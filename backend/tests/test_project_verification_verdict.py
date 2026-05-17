"""Deterministic verdict synthesis regressions (EPIC-12 / CS-354)."""

from __future__ import annotations

from project_verification.domain.permit_format import PermitFormatEvaluation, PermitFormatVerdict
from project_verification.domain.verdict_synthesis import (
    GREEN_MIN,
    UNKNOWN_PERMIT_MAX_SCORE_BEFORE_GREEN_CAP,
    headline_key_for_band,
    synthesize_verdict,
)


def _u(fk: str = "permit.format_unknown.case") -> PermitFormatEvaluation:
    return PermitFormatEvaluation(PermitFormatVerdict.UNKNOWN, fk)


def _o(fk: str = "permit.format_ok.case") -> PermitFormatEvaluation:
    return PermitFormatEvaluation(PermitFormatVerdict.OK, fk)


def _s(fk: str = "permit.format_suspicious.case") -> PermitFormatEvaluation:
    return PermitFormatEvaluation(PermitFormatVerdict.SUSPICIOUS, fk)


def _kw(**patch: object):
    core = dict(
        permit=_u(),
        reputation_negative=False,
        reputation_positive=False,
        reputation_failure=False,
        reputation_disabled=True,
        ocr_low_confidence=False,
        ocr_medium_confidence=False,
        apply_unknown_permit_cap=False,
    )
    core.update(patch)
    return core


def test_green_requires_permit_ok_and_positive_evidence():
    score, band, _ = synthesize_verdict(
        **_kw(permit=_o(), reputation_disabled=False, reputation_positive=True)
    )

    assert score >= GREEN_MIN
    assert band == "green"


def test_negative_evidence_wins_over_positive_when_both_present():
    _, _, keys = synthesize_verdict(
        **_kw(reputation_disabled=False, reputation_positive=True, reputation_negative=True)
    )

    assert "pv.reputation.evidence_negative" in keys
    assert "pv.reputation.evidence_positive" not in keys


def test_negative_reputation_weakens_score_vs_skipped_stub():
    skipped = synthesize_verdict(**_kw())
    degraded = synthesize_verdict(**_kw(reputation_disabled=False, reputation_negative=True))

    assert degraded[0] < skipped[0]


def test_unknown_permit_high_confidence_cap():
    score, _, keys = synthesize_verdict(
        **_kw(
            apply_unknown_permit_cap=True,
            reputation_disabled=False,
            reputation_positive=True,
        )
    )

    assert "pv.policy.cap_green_unknown_permit" in keys
    assert score <= UNKNOWN_PERMIT_MAX_SCORE_BEFORE_GREEN_CAP


def test_suspicious_with_negative_rep_heads_red():
    _, band, _ = synthesize_verdict(
        **_kw(permit=_s(), reputation_disabled=False, reputation_negative=True, reputation_positive=False)
    )

    assert band == "red"
    assert headline_key_for_band(band) == headline_key_for_band("red")
