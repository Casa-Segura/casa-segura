"""CS-110+CS-111+CS-112+CS-113+CS-116 — `F2Orchestrator` end-to-end tests.

Exercises the persisted envelope EPIC-06 will consume:

    - Happy CVP: classifier high-confidence -> no leasing reclassification ->
      project upsert -> economic extraction -> single ContractAnalysis write.
    - CVP -> LEA reclassification: 4-of-6 indicators flip the effective
      contract_type; reclassification_indicators JSONB persisted.
    - NOT_CLASSIFIABLE: low primary confidence + no validator agreement ->
      ContractAnalysis row is still created (PRD §US-06) but contract_type
      is NOT_CLASSIFIABLE and no economic fields.
    - failed_classification: LLM_PARSE_FAILED -> ContractSubmission marked
      failed_classification, NO ContractAnalysis row.
    - Idempotency: two runs with the same submission_hash -> 1 row,
      `public_short_id` stable.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from django.conf import settings

from classification.application.orchestrator import (
    F2Orchestrator,
    F2OrchestratorError,
)
from classification.domain.contract_type import ContractType
from classification.domain.reclassification import LeasingSeverity
from conftest import OPENROUTER_BASE_URL, openrouter_response
from economics.application.benchmark_loader import load_yaml, upsert_benchmarks
from economics.domain.economic_summary import EconomicSummary
from ingestion.domain.enums import ProcessingStatus
from platform_core.infrastructure.django.models import ContractAnalysis
from shared.llm.openrouter import OpenRouterClient
from tests.factories import (
    ContractSubmissionFactory,
    CorpusVersionFactory,
    RubricVersionFactory,
)

CHAT_URL = f"{OPENROUTER_BASE_URL}/chat/completions"

SUBMISSION_HASH = "a" * 64
TEXT = "texto sintético del contrato"


def _client() -> OpenRouterClient:
    return OpenRouterClient(
        api_key="sk-or-v1-test",
        base_url=OPENROUTER_BASE_URL,
        timeout_seconds=5,
        max_retries=1,
        http_referer="https://test.local",
        x_title="Test",
    )


def _stage_calls(router, *payloads: dict):
    """Queue sequential OpenRouter responses for each pipeline stage."""
    return router.post(CHAT_URL).mock(
        side_effect=[openrouter_response(p) for p in payloads],
    )


BENCHMARK_FIXTURE = Path(settings.BASE_DIR) / "fixtures" / "economic_benchmarks_2026q2.yaml"


@pytest.fixture
def active_benchmark(db):
    """Seed + activate the canonical benchmark catalog from the prod YAML fixture.

    Using the real fixture (rather than synthetic factory rows) keeps the test
    aligned with the catalog the orchestrator hydrates in production.
    """
    payload = load_yaml(BENCHMARK_FIXTURE)
    version_obj, _, _ = upsert_benchmarks(payload, activate=True)
    return version_obj


@pytest.fixture
def active_catalog(db, active_benchmark):
    """Ensure an active RubricVersion + CorpusVersion + BenchmarkVersion exist."""
    rubric = RubricVersionFactory(version="1.0.0", is_active=True)
    corpus = CorpusVersionFactory(version="1.0.0", is_active=True)
    return rubric, corpus, active_benchmark


def _classification_payload(
    contract_type: str = "CVP",
    confidence: float = 0.92,
    reasoning: str = "precio + cuotas",
) -> dict:
    return {
        "contract_type": contract_type,
        "confidence": confidence,
        "reasoning": reasoning,
        "indicators_found": ["precio explícito", "saldo a plazos"],
        "elements_detected": {"public_deed": True, "arbitration_clause": False},
    }


def _leasing_skip_payload() -> dict:
    """Payload that yields zero indicators (no reclassification)."""
    return {
        "mandatory_term": False,
        "predefined_purchase_option": False,
        "ownership_retained": False,
        "taxes_to_buyer": False,
        "risks_to_buyer": False,
        "payments_as_rent": False,
        "confidence": 0.7,
        "reasoning": "no indicators",
    }


def _leasing_reclassify_payload() -> dict:
    """4-of-6 indicators -> LEA reclassification."""
    return {
        "mandatory_term": True,
        "predefined_purchase_option": True,
        "ownership_retained": True,
        "taxes_to_buyer": True,
        "risks_to_buyer": False,
        "payments_as_rent": False,
        "confidence": 0.92,
        "reasoning": "Art. 2 LAF indicators 1-4 detected",
    }


def _project_name_payload(name: str = "Residencial Las Palmeras") -> dict:
    return {"project_name_raw": name, "confidence": 0.95}


def _economic_payload_full() -> dict:
    return {
        "purchase_price_usd": {"value": 80000.0, "confidence": 0.92, "rationale": "precio"},
        "down_payment_usd": {"value": 8000.0, "confidence": 0.9, "rationale": "prima"},
        "down_payment_pct": {"value": 0.10, "confidence": 0.9, "rationale": "10%"},
        "financed_amount_usd": {"value": 72000.0, "confidence": 0.9, "rationale": "saldo"},
        "term_months": {"value": 72, "confidence": 0.95, "rationale": "72 meses"},
        "monthly_payment_usd": {"value": 1167.0, "confidence": 0.85, "rationale": "cuota"},
        "interest_rate_pct": {"value": 0.12, "confidence": 0.85, "rationale": "12% anual"},
        "interest_calculation_base": {
            "value": "outstanding_principal",
            "confidence": 0.9,
            "rationale": "saldo insoluto",
        },
        "payment_periodicity": {"value": "monthly", "confidence": 0.95, "rationale": "mensual"},
    }


# ---------------------------------------------------------------------------
# Happy path — CVP, high confidence, no reclassification
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_happy_cvp_persists_contract_analysis(mock_openrouter, active_catalog):
    _stage_calls(
        mock_openrouter,
        _classification_payload(),
        _leasing_skip_payload(),
        _project_name_payload(),
        _economic_payload_full(),
    )

    with F2Orchestrator(client=_client()) as orchestrator:
        result = orchestrator.run(
            submission_hash=SUBMISSION_HASH,
            extracted_text=TEXT,
        )

    assert result.effective_contract_type is ContractType.CVP
    assert result.was_created is True
    assert result.leasing.should_reclassify is False
    assert result.aggregated.warning_precursors == []

    analysis = ContractAnalysis.objects.get(id=result.contract_analysis_id)
    assert analysis.contract_type == "CVP"
    assert analysis.contract_type_declared == "CVP"
    assert analysis.contract_type_reclassified is False
    assert float(analysis.classification_confidence) == pytest.approx(0.92, abs=0.001)
    assert analysis.classification_attempts == 1
    assert analysis.elements_detected["public_deed"] is True
    assert analysis.elements_detected["warranty_exemption_clause"] is False
    assert analysis.project_name_canonical == "Residencial Las Palmeras"
    assert analysis.economic_fields_raw is not None
    assert analysis.economic_fields_raw["fields"]["purchase_price_usd"] == 80000.0
    # Transient identifiers MUST be filtered out (BR-04).
    assert "seller_name" not in analysis.economic_fields_raw["fields"]
    # CS-138: F5 envelope is persisted (not the slot precursor) and the FK
    # echoes the active benchmark version byte-equal with the JSON stamp.
    assert analysis.economic_summary is not None
    envelope = EconomicSummary.model_validate(analysis.economic_summary)
    assert envelope.benchmark_version == active_catalog[2].version
    assert analysis.benchmark_version_id == active_catalog[2].version
    # CS-139: CVP routes through the developer-direct rate band per PRD_F5
    # BR-10 (the §8.1 prompt definition of CVP excludes bank financing).
    rate_comparisons = [
        c for c in envelope.benchmark_comparisons if c.metric == "annual_rate"
    ]
    assert rate_comparisons, "CVP happy path must produce a rate-band comparison"
    assert rate_comparisons[0].metric_label == "Tasa efectiva anual vs financiamiento directo"


# ---------------------------------------------------------------------------
# CVP -> LEA reclassification
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_cvp_reclassifies_to_lea_when_four_indicators(mock_openrouter, active_catalog):
    _stage_calls(
        mock_openrouter,
        _classification_payload(),
        _leasing_reclassify_payload(),
        _project_name_payload(),
        _economic_payload_full(),
    )

    with F2Orchestrator(client=_client()) as orchestrator:
        result = orchestrator.run(
            submission_hash=SUBMISSION_HASH,
            extracted_text=TEXT,
        )

    assert result.effective_contract_type is ContractType.LEA
    assert result.leasing.should_reclassify is True
    assert result.leasing.severity is LeasingSeverity.HIGH

    analysis = ContractAnalysis.objects.get(id=result.contract_analysis_id)
    assert analysis.contract_type == "LEA"
    assert analysis.contract_type_declared == "CVP"
    assert analysis.contract_type_reclassified is True
    assert analysis.reclassification_indicators["count"] == 4
    assert analysis.reclassification_indicators["severity"] == "high"
    assert analysis.reclassification_indicators["indicators"]["mandatory_term"] is True


# ---------------------------------------------------------------------------
# NOT_CLASSIFIABLE path (low primary confidence + no validator agreement)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_low_confidence_returns_not_classifiable_envelope(mock_openrouter, active_catalog):
    # Primary low confidence (< 0.65) short-circuits straight to
    # NOT_CLASSIFIABLE in CS-110 — no validator, no leasing, no economic.
    _stage_calls(
        mock_openrouter,
        _classification_payload(contract_type="CVP", confidence=0.40, reasoning="weak"),
        _leasing_skip_payload(),
        _project_name_payload(name="Proyecto Difuso"),
    )

    with F2Orchestrator(client=_client()) as orchestrator:
        result = orchestrator.run(
            submission_hash=SUBMISSION_HASH,
            extracted_text=TEXT,
        )

    assert result.effective_contract_type is ContractType.NOT_CLASSIFIABLE
    assert result.extraction.contract_type is ContractType.NOT_CLASSIFIABLE
    assert result.extraction.extracted_fields.purchase_price_usd is None

    analysis = ContractAnalysis.objects.get(id=result.contract_analysis_id)
    assert analysis.contract_type == "NOT_CLASSIFIABLE"
    assert analysis.economic_fields_raw is None
    assert analysis.economic_summary is None
    # CS-138: NOT_CLASSIFIABLE skips F5 entirely — the FK is left null even
    # though an active BenchmarkVersion exists.
    assert analysis.benchmark_version_id is None


# ---------------------------------------------------------------------------
# failed_classification — parse error path
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_parse_failure_marks_submission_failed_and_creates_no_row(
    mock_openrouter,
    active_catalog,
):
    """LLM_PARSE_FAILED -> ContractSubmission.processing_status flipped, no row."""
    submission = ContractSubmissionFactory(
        submission_hash=SUBMISSION_HASH,
        processing_status=ProcessingStatus.EXTRACTED.value,
    )
    import httpx

    mock_openrouter.post(CHAT_URL).mock(
        return_value=httpx.Response(
            200,
            json={"choices": [{"message": {"content": "this is not json"}}]},
        ),
    )

    with F2Orchestrator(client=_client()) as orchestrator:
        with pytest.raises(F2OrchestratorError) as exc:
            orchestrator.run(submission_hash=SUBMISSION_HASH, extracted_text=TEXT)

    assert exc.value.code == "FAILED_CLASSIFICATION"
    submission.refresh_from_db()
    assert submission.processing_status == ProcessingStatus.FAILED_CLASSIFICATION.value
    assert ContractAnalysis.objects.filter(submission_hash=SUBMISSION_HASH).count() == 0


# ---------------------------------------------------------------------------
# Idempotency — two runs over the same submission_hash
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_idempotent_when_same_submission_hash(mock_openrouter, active_catalog):
    # Queue two rounds of (classify, leasing, project, economic) responses.
    _stage_calls(
        mock_openrouter,
        _classification_payload(),
        _leasing_skip_payload(),
        _project_name_payload(),
        _economic_payload_full(),
        _classification_payload(),
        _leasing_skip_payload(),
        _project_name_payload(),
        _economic_payload_full(),
    )

    with F2Orchestrator(client=_client()) as orchestrator:
        first = orchestrator.run(submission_hash=SUBMISSION_HASH, extracted_text=TEXT)
        second = orchestrator.run(submission_hash=SUBMISSION_HASH, extracted_text=TEXT)

    assert first.contract_analysis_id == second.contract_analysis_id
    assert first.was_created is True
    assert second.was_created is False
    assert first.public_short_id == second.public_short_id
    assert ContractAnalysis.objects.filter(submission_hash=SUBMISSION_HASH).count() == 1


# ---------------------------------------------------------------------------
# Configuration errors
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_missing_active_rubric_raises_typed_error(mock_openrouter, active_benchmark):
    # No active catalog rows. Stage the LLM responses anyway; the failure
    # surfaces at the persist step.
    CorpusVersionFactory(version="1.0.0", is_active=True)
    _stage_calls(
        mock_openrouter,
        _classification_payload(),
        _leasing_skip_payload(),
        _project_name_payload(),
        _economic_payload_full(),
    )

    with F2Orchestrator(client=_client()) as orchestrator:
        with pytest.raises(F2OrchestratorError) as exc:
            orchestrator.run(submission_hash=SUBMISSION_HASH, extracted_text=TEXT)

    assert exc.value.code == "NO_ACTIVE_RUBRIC"
    assert ContractAnalysis.objects.filter(submission_hash=SUBMISSION_HASH).count() == 0


@pytest.mark.django_db
def test_missing_active_benchmark_raises_typed_error(mock_openrouter):
    """CS-138: persistence requires an active BenchmarkVersion."""
    RubricVersionFactory(version="1.0.0", is_active=True)
    CorpusVersionFactory(version="1.0.0", is_active=True)
    _stage_calls(
        mock_openrouter,
        _classification_payload(),
        _leasing_skip_payload(),
        _project_name_payload(),
        _economic_payload_full(),
    )

    with F2Orchestrator(client=_client()) as orchestrator:
        with pytest.raises(F2OrchestratorError) as exc:
            orchestrator.run(submission_hash=SUBMISSION_HASH, extracted_text=TEXT)

    assert exc.value.code == "NO_ACTIVE_BENCHMARK"
    assert ContractAnalysis.objects.filter(submission_hash=SUBMISSION_HASH).count() == 0


@pytest.mark.django_db
def test_empty_input_raises_typed_error(mock_openrouter, active_catalog):
    with F2Orchestrator(client=_client()) as orchestrator:
        with pytest.raises(F2OrchestratorError) as exc:
            orchestrator.run(submission_hash="", extracted_text=TEXT)
    assert exc.value.code == "EMPTY_INPUT"
