"""Deterministic heuristic → verdict synthesis (EPIC-12 / CS-354)."""

from __future__ import annotations

from typing import Literal

from project_verification.domain.permit_format import PermitFormatEvaluation, PermitFormatVerdict

VerdictBand = Literal["green", "yellow", "red"]


GREEN_MIN = 8.0
YELLOW_MIN = 5.0


# Policy: permit format unknown cannot land in green absent stronger corroboration (ticket BVA table).
UNKNOWN_PERMIT_MAX_SCORE_BEFORE_GREEN_CAP = 7.99


def _band_from_score(score: float) -> VerdictBand:
    if score >= GREEN_MIN:
        return "green"
    if score >= YELLOW_MIN:
        return "yellow"
    return "red"


def synthesize_verdict(  # noqa: PLR0912
    *,
    permit: PermitFormatEvaluation,
    reputation_negative: bool,
    reputation_positive: bool,
    reputation_failure: bool,
    reputation_disabled: bool,
    ocr_low_confidence: bool,
    ocr_medium_confidence: bool,
    apply_unknown_permit_cap: bool,
) -> tuple[float, VerdictBand, list[str]]:
    """Return heuristic score ∈ [0,10], verdict band, and stable rationale_keys."""

    keys: list[str] = []
    score = 7.0

    if permit.verdict == PermitFormatVerdict.OK:
        score += 0.9
        keys.append(permit.finding_key)
    elif permit.verdict == PermitFormatVerdict.SUSPICIOUS:
        score -= 3.2
        keys.append(permit.finding_key)
    else:
        score -= 0.1
        keys.append(permit.finding_key)

    if reputation_disabled:
        keys.append("pv.reputation.skipped_disabled")
    elif reputation_failure:
        score -= 0.35
        keys.append("pv.reputation.degraded")
    elif reputation_negative:
        score -= 2.0
        keys.append("pv.reputation.evidence_negative")
    elif reputation_positive:
        score += 1.2
        keys.append("pv.reputation.evidence_positive")

    if ocr_low_confidence:
        score -= 2.8
        keys.append("pv.ocr.low_confidence_penalty")
    elif ocr_medium_confidence:
        score -= 1.1
        keys.append("pv.ocr.medium_confidence_penalty")

    score = max(0.0, min(10.0, score))

    if permit.verdict == PermitFormatVerdict.SUSPICIOUS and reputation_negative:
        score = min(score, 4.8)
        keys.append("pv.override.suspicious_permit_negative_rep")

    if apply_unknown_permit_cap and permit.verdict == PermitFormatVerdict.UNKNOWN:
        if score >= GREEN_MIN:
            score = min(score, UNKNOWN_PERMIT_MAX_SCORE_BEFORE_GREEN_CAP)
            keys.append("pv.policy.cap_green_unknown_permit")

    band = _band_from_score(score)

    ordered_keys: list[str] = []
    for k in keys:
        if k not in ordered_keys:
            ordered_keys.append(k)

    return score, band, ordered_keys


def headline_key_for_band(band: VerdictBand) -> str:
    return {
        "green": "pv.headline.green",
        "yellow": "pv.headline.yellow",
        "red": "pv.headline.red",
    }[band]


async def narration_only_llm_maybe(
    *,
    enabled: bool,
    heuristic_band: VerdictBand,
    rationale_keys: list[str],
) -> str | None:
    """Placeholder for optional narration (never mutates bands). Declared async for symmetry."""

    del enabled, heuristic_band, rationale_keys
    # CS-354: wired when PRODUCT enables after review; deterministic path default.
    return None


__all__ = [
    "GREEN_MIN",
    "UNKNOWN_PERMIT_MAX_SCORE_BEFORE_GREEN_CAP",
    "YELLOW_MIN",
    "VerdictBand",
    "headline_key_for_band",
    "narration_only_llm_maybe",
    "synthesize_verdict",
]
