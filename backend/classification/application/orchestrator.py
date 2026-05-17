"""F2 orchestrator (CS-110 + CS-111 + CS-112 + CS-113 + CS-116 wiring).

Chains the per-step classification services declared by EPIC-04 into a
single transactional pass and persists the envelope to ``ContractAnalysis``.
Mirrors the shape of :func:`ingestion.application.upload_service.ingest_upload`
(frozen dataclasses, linear pipeline, ``@transaction.atomic`` for the
single write, structlog-style structured logging).

Pipeline
--------
``F2Orchestrator.run(submission_hash, extracted_text)`` performs:

1. **Classification** (`ContractClassifier`) — PRD F2 §US-01 confidence
   bands. ``LLM_PARSE_FAILED`` flips the submission's
   ``processing_status`` to ``failed_classification`` and surfaces a
   typed :class:`F2OrchestratorError`; ``NOT_CLASSIFIABLE`` is a
   legitimate outcome and is propagated to the persisted row.
2. **Leasing reclassification** (`LeasingReclassificationDetector`) —
   skipped if classification rejected the contract. When the detector
   recommends ``LEA`` (≥4 of 6 Art. 2 LAF indicators), the effective
   ``contract_type`` is switched and ``reclassification_reason`` is
   populated. The §8.4 warning envelope is persisted on
   ``ContractAnalysis.reclassification_indicators`` regardless of
   severity so EPIC-06 can pick up the 2-3 indicator warnings.
3. **Project linkage** (`ProjectNameExtractor` + `ProjectLinker`) —
   produces the ``Project`` row and the ``project_name_canonical`` raw
   string. Wrapped in the linker's own ``transaction.atomic`` (BR-05 /
   BR-06).
4. **Economic extraction** (`EconomicFieldExtractor`) — runs against the
   effective contract type (post-leasing-override). Short-circuited on
   ``NOT_CLASSIFIABLE`` (no LLM call). Conflicting figures surface via
   the AMBIGUOUS signal added in PR-5.
5. **Aggregation** (`aggregate_extraction`) — turns the extraction into
   the slot/status payload CS-116 owns; this is the ``economic_summary``
   precursor EPIC-05 will refine.
6. **Single write** to ``ContractAnalysis`` via ``update_or_create``
   keyed by ``submission_hash`` — idempotent on retry.

Failure surface
---------------
* ``ClassificationError(LLM_PARSE_FAILED)`` -> submission marked
  ``failed_classification``, ``F2OrchestratorError(FAILED_CLASSIFICATION)``
  raised. The :class:`ContractAnalysis` row is NOT created (per PRD F2
  §6.2 — failed classification never produces a persisted analysis).
* All other ``ClassificationError`` / ``EconomicExtractionError`` / etc.
  propagate as ``F2OrchestratorError`` with the original code; the
  submission status is left alone so the caller can decide on retry.
* ``NOT_CLASSIFIABLE`` is **not** an error: an analysis row IS created
  with ``contract_type=NOT_CLASSIFIABLE`` so the user-facing copy
  (PRD §US-06) can be rendered downstream.

DDD note
--------
Application layer. Imports the four sibling services + the linker
(which itself crosses into ``platform_core`` infrastructure for the
``Project`` ORM model), plus ``ContractSubmission`` /
``ContractAnalysis``. Does not touch HTTP / DRF / Celery directly; the
internal endpoint (`classification.interfaces.api.views`) is the public
surface.
"""

from __future__ import annotations

import logging
import secrets
import string
import uuid
from dataclasses import dataclass
from typing import Any

from django.db import transaction
from django.utils import timezone

from classification.application.classifier import (
    ClassificationError,
    ContractClassifier,
)
from classification.application.economic_extractor import (
    EconomicExtractionError,
    EconomicFieldExtractor,
)
from classification.application.extraction_aggregator import aggregate_extraction
from classification.application.leasing_detector import (
    LeasingReclassificationDetector,
)
from classification.application.project_linker import ProjectLinker
from classification.application.project_name_extractor import (
    ProjectNameExtractionError,
    ProjectNameExtractor,
)
from classification.domain.aggregated_extraction import AggregatedExtraction
from classification.domain.contract_extraction import ContractExtraction
from classification.domain.contract_type import ContractType
from classification.domain.dtos import ClassificationResult
from classification.domain.extracted_fields import ExtractedFields
from classification.domain.reclassification import (
    LeasingReclassificationResult,
    LeasingSeverity,
)
from corpus.infrastructure.django.models import CorpusVersion
from ingestion.domain.enums import ProcessingStatus
from ingestion.infrastructure.django.models import ContractSubmission
from platform_core.infrastructure.django.models import ContractAnalysis
from rubric.infrastructure.django.models import RubricVersion
from shared.llm.openrouter import OpenRouterClient

logger = logging.getLogger(__name__)


# Contract types that have an economic prompt registered in
# `economic_prompts.py`. NOT_CLASSIFIABLE is excluded; the orchestrator
# short-circuits before invoking the extractor for it.
_ECONOMIC_CONTRACT_TYPES: frozenset[ContractType] = frozenset(
    {
        ContractType.CVC,
        ContractType.CVP,
        ContractType.ARV,
        ContractType.ARC,
        ContractType.APV,
        ContractType.LEA,
        ContractType.IVU,
        ContractType.FSV,
    },
)

_PUBLIC_SHORT_ID_ALPHABET: str = string.ascii_uppercase + string.digits


def _generate_public_short_id() -> str:
    """Produce a `CS-YYYY-XXXXXX` short id matching DOMAIN §3.2.

    Mirrors ``tests.factories.make_public_short_id``. Lives here so the
    orchestrator does not depend on the test module. If we ever need
    this in a second place, promote to `platform_core.domain.short_id`.
    """
    year = timezone.now().year
    suffix = "".join(secrets.choice(_PUBLIC_SHORT_ID_ALPHABET) for _ in range(6))
    return f"CS-{year}-{suffix}"


def _active_rubric_version() -> RubricVersion:
    version = RubricVersion.objects.filter(is_active=True).first()
    if version is None:
        raise F2OrchestratorError(
            "no active RubricVersion (run seed_rubric_version --activate)",
            code="NO_ACTIVE_RUBRIC",
        )
    return version


def _active_corpus_version() -> CorpusVersion:
    version = CorpusVersion.objects.filter(is_active=True).first()
    if version is None:
        raise F2OrchestratorError(
            "no active CorpusVersion (run seed_corpus_version --activate)",
            code="NO_ACTIVE_CORPUS",
        )
    return version


@dataclass(frozen=True)
class F2OrchestratorResult:
    """Envelope returned by `F2Orchestrator.run` (and serialized by the
    internal endpoint)."""

    contract_analysis_id: uuid.UUID
    public_short_id: str
    classification: ClassificationResult
    leasing: LeasingReclassificationResult
    extraction: ContractExtraction
    aggregated: AggregatedExtraction
    was_created: bool
    effective_contract_type: ContractType


class F2OrchestratorError(RuntimeError):
    """Raised when the F2 pipeline cannot produce a persisted analysis.

    The ``code`` attribute mirrors the canonical PRD F2 error codes
    (``LLM_PARSE_FAILED``, ``LLM_TRANSIENT_FAILURE``,
    ``FAILED_CLASSIFICATION``, ``NO_ACTIVE_RUBRIC``,
    ``NO_ACTIVE_CORPUS``, ``EMPTY_INPUT``, ``SUBMISSION_NOT_FOUND``).
    """

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code


class F2Orchestrator:
    """Chains the four §F2 services into one transactional pipeline.

    The shared :class:`OpenRouterClient` is injected so tests can plug a
    respx-mocked instance in and so production workers can share a
    single HTTPX connection pool across all four sub-services.
    """

    def __init__(self, *, client: OpenRouterClient | None = None) -> None:
        self._client = client or OpenRouterClient()
        self._owns_client = client is None

    def __enter__(self) -> F2Orchestrator:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run(self, *, submission_hash: str, extracted_text: str) -> F2OrchestratorResult:
        """Run the full F2 pipeline and persist a :class:`ContractAnalysis`.

        Raises :class:`F2OrchestratorError` on classification parse failure
        (after marking the submission ``failed_classification``) or
        configuration errors (missing active rubric / corpus).
        """
        if not submission_hash or not submission_hash.strip():
            raise F2OrchestratorError("submission_hash is empty", code="EMPTY_INPUT")
        if not extracted_text or not extracted_text.strip():
            raise F2OrchestratorError("extracted_text is empty", code="EMPTY_INPUT")

        # Step 1: classify (PRD F2 §US-01).
        classification = self._classify(submission_hash, extracted_text)

        # Step 2: leasing detection (skipped for non-applicable types).
        leasing = self._detect_leasing(extracted_text, classification.contract_type)
        effective_type = (
            leasing.recommended_type if leasing.should_reclassify else classification.contract_type
        )

        # Step 3: project name extraction + linkage.
        link_result, name_canonical = self._link_project(extracted_text, submission_hash)

        # Step 4: economic extraction (skipped on NOT_CLASSIFIABLE).
        extraction = self._extract_economics(extracted_text, effective_type)

        # Step 5: aggregate into the per-slot status payload.
        aggregated = aggregate_extraction(extraction)

        # Step 6: single transactional write to ContractAnalysis.
        analysis, was_created = self._persist(
            submission_hash=submission_hash,
            classification=classification,
            leasing=leasing,
            effective_type=effective_type,
            link_result_project_id=link_result,
            project_name_canonical=name_canonical,
            extraction=extraction,
            aggregated=aggregated,
        )

        logger.info(
            "f2_orchestrator.completed",
            extra={
                "submission_hash": submission_hash[:12],
                "effective_contract_type": effective_type.value,
                "was_created": was_created,
                "classification_attempts": classification.classification_attempts,
                "leasing_severity": leasing.severity.value,
                "unverifiable_count": len(aggregated.unverifiable_fields),
                "ambiguous_count": aggregated.ambiguous_count,
            },
        )

        return F2OrchestratorResult(
            contract_analysis_id=analysis.id,
            public_short_id=analysis.public_short_id,
            classification=classification,
            leasing=leasing,
            extraction=extraction,
            aggregated=aggregated,
            was_created=was_created,
            effective_contract_type=effective_type,
        )

    # ------------------------------------------------------------------
    # Pipeline steps
    # ------------------------------------------------------------------
    def _classify(self, submission_hash: str, text: str) -> ClassificationResult:
        try:
            with ContractClassifier(client=self._client) as svc:
                return svc.classify(text)
        except ClassificationError as exc:
            code = exc.code or "LLM_TRANSIENT_FAILURE"
            if code == "LLM_PARSE_FAILED":
                self._mark_submission_failed(submission_hash)
                raise F2OrchestratorError(
                    f"classification parse failed: {exc}",
                    code="FAILED_CLASSIFICATION",
                ) from exc
            raise F2OrchestratorError(
                f"classification failed: {exc}",
                code=code,
            ) from exc

    def _detect_leasing(
        self,
        text: str,
        initial_type: ContractType,
    ) -> LeasingReclassificationResult:
        try:
            with LeasingReclassificationDetector(client=self._client) as svc:
                return svc.detect(text, initial_type=initial_type)
        except ClassificationError as exc:
            raise F2OrchestratorError(
                f"leasing detection failed: {exc}",
                code=exc.code or "LLM_TRANSIENT_FAILURE",
            ) from exc

    def _link_project(
        self,
        text: str,
        submission_hash: str,
    ) -> tuple[uuid.UUID, str | None]:
        try:
            with ProjectNameExtractor(client=self._client) as svc:
                extraction = svc.extract(text, placeholder_seed=submission_hash)
        except ProjectNameExtractionError as exc:
            raise F2OrchestratorError(
                f"project name extraction failed: {exc}",
                code=exc.code or "LLM_TRANSIENT_FAILURE",
            ) from exc

        link_result = ProjectLinker().link_or_create_project(extraction)
        return link_result.project_id, extraction.raw

    def _extract_economics(
        self,
        text: str,
        contract_type: ContractType,
    ) -> ContractExtraction:
        if contract_type is ContractType.NOT_CLASSIFIABLE or contract_type not in _ECONOMIC_CONTRACT_TYPES:
            # Short-circuit: no LLM call, empty extraction. Aggregator
            # will produce all-NOT_PRESENT slots.
            return ContractExtraction(
                contract_type=contract_type,
                extracted_fields=ExtractedFields(),
                field_confidences={},
                unverifiable_fields=[],
                ambiguous_fields=[],
            )

        try:
            with EconomicFieldExtractor(client=self._client) as svc:
                return svc.extract(text, contract_type)
        except EconomicExtractionError as exc:
            raise F2OrchestratorError(
                f"economic extraction failed: {exc}",
                code=exc.code or "LLM_TRANSIENT_FAILURE",
            ) from exc

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def _mark_submission_failed(self, submission_hash: str) -> None:
        """Flip the submission to ``failed_classification`` (PRD F2 §6.2)."""
        updated = ContractSubmission.objects.filter(submission_hash=submission_hash).update(
            processing_status=ProcessingStatus.FAILED_CLASSIFICATION.value,
        )
        if updated == 0:
            # The submission may legitimately not exist when the
            # orchestrator is called from the QA endpoint with raw text.
            # Log at info, do not raise — the parse failure is the real
            # error the caller cares about.
            logger.info(
                "f2_orchestrator.submission_not_found_on_mark_failed",
                extra={"submission_hash": submission_hash[:12]},
            )

    def _persist(
        self,
        *,
        submission_hash: str,
        classification: ClassificationResult,
        leasing: LeasingReclassificationResult,
        effective_type: ContractType,
        link_result_project_id: uuid.UUID,
        project_name_canonical: str | None,
        extraction: ContractExtraction,
        aggregated: AggregatedExtraction,
    ) -> tuple[ContractAnalysis, bool]:
        """Single transactional write to ``ContractAnalysis`` keyed by ``submission_hash``.

        Idempotent: ``update_or_create`` ensures a retry with the same
        hash returns the existing row rather than spawning a duplicate.
        """
        rubric = _active_rubric_version()
        corpus = _active_corpus_version()

        reclassification_envelope: dict[str, Any] | None = None
        if leasing.severity is not LeasingSeverity.NONE:
            reclassification_envelope = {
                "indicators": leasing.indicators.model_dump(),
                "count": leasing.indicators.total_indicators_found,
                "severity": leasing.severity.value,
            }

        reclassification_reason = ""
        if leasing.should_reclassify:
            reclassification_reason = leasing.reasoning or ""

        elements_detected = classification.elements_detected.model_dump()

        economic_fields_raw = self._build_economic_fields_raw(extraction)
        economic_summary = self._build_economic_summary_precursor(aggregated)

        defaults: dict[str, Any] = {
            "public_short_id": _generate_public_short_id(),
            "project_id": link_result_project_id,
            "contract_type": effective_type.value,
            "contract_type_declared": classification.contract_type.value,
            "contract_type_reclassified": leasing.should_reclassify,
            "reclassification_reason": reclassification_reason,
            "classification_confidence": classification.confidence,
            "classification_attempts": classification.classification_attempts,
            "elements_detected": elements_detected,
            "reclassification_indicators": reclassification_envelope,
            "project_name_canonical": project_name_canonical,
            "economic_fields_raw": economic_fields_raw,
            "economic_summary": economic_summary,
            "unverifiable_count": len(aggregated.unverifiable_fields),
            "rubric_version": rubric,
            "corpus_version": corpus,
        }

        with transaction.atomic():
            existing = ContractAnalysis.objects.filter(submission_hash=submission_hash).first()
            if existing is None:
                analysis = ContractAnalysis.objects.create(
                    submission_hash=submission_hash,
                    **defaults,
                )
                return analysis, True

            # Idempotent update: keep `public_short_id` stable across retries.
            defaults.pop("public_short_id", None)
            for field, value in defaults.items():
                setattr(existing, field, value)
            existing.save(update_fields=list(defaults.keys()))
            return existing, False

    @staticmethod
    def _build_economic_fields_raw(extraction: ContractExtraction) -> dict[str, Any] | None:
        """Persistence-safe dump of the §8.5 extraction.

        Returns ``None`` for NOT_CLASSIFIABLE so the JSONB column stays
        empty. Otherwise dumps the extracted fields + per-field confidence
        scores + unverifiable/ambiguous lists. PRD F2 BR-04 / BR-07: this
        payload is auditable; the transient identifiers (`seller_name`,
        `buyer_name`, `property_address`) are filtered out here.
        """
        if extraction.contract_type is ContractType.NOT_CLASSIFIABLE:
            return None

        fields_dump = extraction.extracted_fields.model_dump()
        # Strip transient identifiers (BR-04: NEVER persist).
        for transient_field in ("seller_name", "buyer_name", "property_address"):
            fields_dump.pop(transient_field, None)

        confidences = {name: band.score for name, band in extraction.field_confidences.items()}

        return {
            "fields": fields_dump,
            "confidences": confidences,
            "unverifiable_fields": list(extraction.unverifiable_fields),
            "ambiguous_fields": list(extraction.ambiguous_fields),
        }

    @staticmethod
    def _build_economic_summary_precursor(aggregated: AggregatedExtraction) -> dict[str, Any] | None:
        """Per-slot status payload that EPIC-05 will refine into the final summary.

        Returns ``None`` for NOT_CLASSIFIABLE so the JSONB column stays
        empty. Otherwise produces ``{slots, unverifiable_fields, ambiguous_count, warning_precursors}``.
        """
        if aggregated.contract_type is ContractType.NOT_CLASSIFIABLE:
            return None
        return {
            "slots": {
                name: {
                    "status": slot.status.value,
                    "value": slot.value,
                    "confidence": slot.confidence,
                }
                for name, slot in aggregated.slots.items()
            },
            "unverifiable_fields": list(aggregated.unverifiable_fields),
            "ambiguous_count": aggregated.ambiguous_count,
            "warning_precursors": list(aggregated.warning_precursors),
        }


__all__ = [
    "F2Orchestrator",
    "F2OrchestratorError",
    "F2OrchestratorResult",
]
