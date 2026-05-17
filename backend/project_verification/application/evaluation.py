"""Evaluate structured project-verification payloads (manual + billboard follow-up)."""

from __future__ import annotations

import uuid
from typing import Literal


from project_verification.domain.permit_format import evaluate_permit_format
from project_verification.domain.verdict_synthesis import (
    VerdictBand,
    headline_key_for_band,
    synthesize_verdict,
)
from project_verification.reputation import lookup_reputation_signals

SubmissionSource = Literal["manual", "billboard_ocr"]
OcrQualityHint = Literal["high", "medium", "low", "unknown"] | None


def build_verdict_envelope(
    *,
    developer: str,
    project: str,
    permit: str,
    address: str,
    submission_source: SubmissionSource,
    ocr_quality: OcrQualityHint,
) -> dict[str, object]:
    permit_eval = evaluate_permit_format(permit)

    rep = lookup_reputation_signals(developer=developer, project=project)

    reputation_disabled = rep.outcome == "skipped_disabled"

    reputation_positive = bool(rep.positive and rep.outcome == "success")

    reputation_negative = bool(rep.negative and rep.outcome == "success")

    reputation_failure = rep.outcome in {"failure", "timeout"} or rep.degraded

    raw_q = str(ocr_quality or "").strip().lower() if submission_source == "billboard_ocr" else ""
    if submission_source == "billboard_ocr" and raw_q == "":
        raw_q = "low"

    ocr_high = submission_source == "billboard_ocr" and raw_q == "high"
    ocr_medium = submission_source == "billboard_ocr" and raw_q == "medium"
    lowish = {"low", "unknown"}

    ocr_low = submission_source == "billboard_ocr" and raw_q in lowish

    score: float

    verdict: VerdictBand

    keys: list[str]

    score, verdict, keys = synthesize_verdict(
        permit=permit_eval,
        reputation_negative=reputation_negative,
        reputation_positive=reputation_positive,
        reputation_failure=reputation_failure,
        reputation_disabled=reputation_disabled,
        ocr_low_confidence=ocr_low,
        ocr_medium_confidence=ocr_medium,
        apply_unknown_permit_cap=submission_source == "billboard_ocr" and ocr_high,

    )

    hk = headline_key_for_band(verdict)

    rationale_keys_final = [*keys]


    freshness_key = rep.freshness_note_key

    fetched_iso = rep.fetched_at.isoformat().replace("+00:00", "Z") if rep.fetched_at else None

    return {


        "reference_id": str(uuid.uuid4()),
        "verdict": verdict,
        "heuristic_score": score,
        "rationale_keys": rationale_keys_final,

        "headline_key": hk,
        "permit_finding_key": permit_eval.finding_key,

        "reputation_outcome": rep.outcome,
        "reputation_fetched_at": fetched_iso,
        "data_freshness_note_key": freshness_key,
        "echo": {
            "developer": developer,
            "project": project,
            "permit": permit,
            "address": address,
        },

        "narration": None,
        "stub": False,
    }
