"""Convert ``CriterionEvaluation`` rows into severity-ranked ``Finding`` rows.

CS-164 wires the F3 (corpus) ``retrieve_legal_basis`` call to enrich each
finding's ``legal_basis`` with up to 3 ``LegalReference`` objects, or to
tag the finding ``unverifiable_legal`` / ``market_based`` when the
retrieval comes back empty (PRD_F4 US-03, BR-05).

The factory accepts an injected ``LegalCitationFetcher`` so tests run
without DB / embedding model. The default fetcher in production wraps
``corpus.application.retrieval.LegalCitationService`` (CS-085).
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Protocol

from rubric.domain.band import Severity
from rubric.domain.entities import (
    CriterionEvaluation,
    Finding,
    LegalReference,
)
from rubric.domain.overrides import OVERRIDE_CATALOG

logger = logging.getLogger(__name__)


SEVERITY_RANK = {
    Severity.CRITICAL: 0,
    Severity.RED: 1,
    Severity.YELLOW: 2,
    Severity.GREEN: 3,
    Severity.UNVERIFIABLE: 4,
}


class LegalCitationFetcher(Protocol):
    """Adapter over F3's ``LegalCitationService`` — kept narrow for tests."""

    def retrieve(
        self,
        *,
        finding_text: str,
        prefer_anchors: tuple[str, ...] = (),
        top_k: int = 3,
    ) -> list[LegalReference]: ...  # pragma: no cover — protocol


def severity_for_evaluation(evaluation: CriterionEvaluation) -> Severity:
    """Map a ``CriterionEvaluation`` to a ``Severity`` per PRD_F4 US-06."""

    if evaluation.override_triggered is not None:
        return Severity.CRITICAL
    if evaluation.unverifiable:
        return Severity.UNVERIFIABLE
    if evaluation.score <= 3.0:
        return Severity.RED
    if evaluation.score <= 6.0:
        return Severity.YELLOW
    if evaluation.score < 10.0:
        return Severity.GREEN
    return Severity.GREEN


def build_findings(
    evaluations: list[CriterionEvaluation],
    *,
    legal_anchor_lookup: dict[str, tuple[str, ...]] | None = None,
    fetcher: LegalCitationFetcher | None = None,
) -> list[Finding]:
    """Build ``Finding`` rows ordered by severity then weight.

    Skips perfect-score (10) rows when no override and not unverifiable.

    ``legal_anchor_lookup`` maps ``criterion_id`` to the criterion's
    legal_anchor slugs (used as ``prefer_anchors``). ``fetcher`` may be
    None for the offline path — findings then carry the appropriate
    tag (``market_based`` when the criterion has no anchors,
    ``unverifiable_legal`` otherwise).
    """

    anchors = legal_anchor_lookup or {}
    findings: list[tuple[int, float, Finding]] = []
    counter = 1
    for ev in evaluations:
        if not ev.applicable:
            continue
        severity = severity_for_evaluation(ev)
        if severity == Severity.GREEN and ev.score >= 10.0 and ev.override_triggered is None:
            continue

        title, description, recommendation = _draft_text(ev)
        prefer_anchors = anchors.get(ev.criterion_id, ())
        legal_basis, tags = _resolve_legal_basis(
            ev,
            prefer_anchors=prefer_anchors,
            fetcher=fetcher,
        )

        finding = Finding(
            id=f"F-{counter:03d}",
            severity=severity,
            title=title,
            description=description,
            evidence_clause_snippet=ev.evidence_snippet,
            legal_basis=legal_basis,
            recommendation=recommendation,
            related_criterion_id=ev.criterion_id,
            anchors_to_override=ev.override_triggered,
            tags=tags,
        )
        findings.append((SEVERITY_RANK[severity], -ev.weight_in_category, finding))
        counter += 1

    findings.sort(key=lambda row: (row[0], row[1]))
    return [row[2] for row in findings]


def _resolve_legal_basis(
    ev: CriterionEvaluation,
    *,
    prefer_anchors: tuple[str, ...],
    fetcher: LegalCitationFetcher | None,
) -> tuple[list[LegalReference], list[str]]:
    """Call F3 (when present) and apply the tag policy."""

    if fetcher is None:
        return [], _empty_legal_basis_tags(prefer_anchors)

    try:
        citations = fetcher.retrieve(
            finding_text=ev.justification,
            prefer_anchors=prefer_anchors,
            top_k=3,
        )
    except Exception as exc:
        logger.warning("rubric.finding.f3_failed", extra={"criterion_id": ev.criterion_id, "err": str(exc)})
        return [], _empty_legal_basis_tags(prefer_anchors)

    citations = list(citations)[:3]
    if not citations:
        return [], _empty_legal_basis_tags(prefer_anchors)
    return citations, []


def _empty_legal_basis_tags(prefer_anchors: tuple[str, ...]) -> list[str]:
    if prefer_anchors:
        return ["unverifiable_legal"]
    return ["market_based"]


def _draft_text(ev: CriterionEvaluation) -> tuple[str, str, str]:
    """Synthesize title / description / recommendation from the evaluation.

    The LLM-driven path (out of scope for Phase 4 acceptance) replaces
    these strings with prompt-generated copy. The deterministic strings
    here are good enough to satisfy the schema invariants and to give
    the report a meaningful placeholder.
    """

    if ev.override_triggered is not None:
        spec = OVERRIDE_CATALOG[ev.override_triggered]
        title = spec.title_es
    else:
        title = f"Criterio {ev.criterion_id}: hallazgo de la rúbrica"
    description = ev.justification
    if ev.unverifiable:
        recommendation = (
            "Solicitar al vendedor o arrendador la información faltante o un anexo aclaratorio "
            f"para el criterio {ev.criterion_id} antes de firmar."
        )
    elif ev.override_triggered is not None:
        recommendation = (
            "No firmar sin asesoría legal. Exigir la eliminación o corrección de la cláusula "
            "señalada como nula por la ley salvadoreña."
        )
    elif ev.score <= 3.0:
        recommendation = "Negociar la cláusula antes de firmar; consultar a un abogado para los términos."
    elif ev.score <= 6.0:
        recommendation = "Aclarar la redacción con el vendedor o arrendador y solicitar mejoras antes de firmar."
    else:
        recommendation = "Revisar el detalle con asesoría legal aunque el criterio luzca aceptable."
    return title, description, recommendation


def count_critical(findings: Iterable[Finding]) -> int:
    return sum(1 for f in findings if f.severity == Severity.CRITICAL)


__all__ = [
    "SEVERITY_RANK",
    "LegalCitationFetcher",
    "build_findings",
    "count_critical",
    "severity_for_evaluation",
]
