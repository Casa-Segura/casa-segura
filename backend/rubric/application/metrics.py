"""Prometheus instrumentation for the rubric engine — CS-330.

* ``RUBRIC_EVAL_DURATION``        — per-analysis wall time.
* ``RUBRIC_CRITERION_DURATION``   — per-criterion latency (criterion_id label only — bounded ≤42).
* ``RUBRIC_CRITERION_OUTCOMES``   — counter per criterion x outcome enum.
* ``RUBRIC_OVERRIDE_TOTAL``       — counter per override_code.
* ``RUBRIC_BAND_TOTAL``           — counter per band (4 dimensions).
* ``RUBRIC_CONTRACT_TYPE_TOTAL``  — counter per contract_type (9 dimensions).
* ``RUBRIC_SCORE_DISTRIBUTION``   — histogram of ``score_total`` over rubric bands.
* ``RUBRIC_UNVERIFIABLE_RATE``    — counter per criterion x unverifiable enum.
* ``RUBRIC_FINDINGS_PER_ANALYSIS``— histogram of total findings emitted.

Cardinality budget (CS-330 BVA): ≤ 42 criteria + ≤ 11 overrides + ≤ 4
bands + ≤ 9 contract types = well under 100 series.
"""

from __future__ import annotations

from shared.observability.metrics import safe_counter, safe_histogram

RUBRIC_EVAL_DURATION = safe_histogram(
    "casa_segura_rubric_eval_duration_seconds",
    "End-to-end rubric evaluation latency per analysis.",
    buckets=(0.5, 1, 2.5, 5, 10, 20, 30, 45, 60, 90, 120),
)

RUBRIC_CRITERION_DURATION = safe_histogram(
    "casa_segura_rubric_criterion_duration_seconds",
    "Per-criterion evaluator latency.",
    labelnames=("criterion_id",),
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 15, 30),
)

RUBRIC_CRITERION_OUTCOMES = safe_counter(
    "casa_segura_rubric_criterion_outcomes_total",
    "Per-criterion evaluator outcomes (evaluated / unverifiable / failed).",
    labelnames=("criterion_id", "outcome"),
)

RUBRIC_OVERRIDE_TOTAL = safe_counter(
    "casa_segura_rubric_override_total",
    "Triggered overrides counter.",
    labelnames=("override_code",),
)

RUBRIC_BAND_TOTAL = safe_counter(
    "casa_segura_rubric_band_total",
    "Final band distribution.",
    labelnames=("band",),
)

RUBRIC_CONTRACT_TYPE_TOTAL = safe_counter(
    "casa_segura_rubric_contract_type_total",
    "Distribution of finalized contract types.",
    labelnames=("contract_type",),
)

RUBRIC_SCORE_DISTRIBUTION = safe_histogram(
    "casa_segura_rubric_score_total",
    "Histogram of rubric score totals (0-10), aligned with band edges.",
    buckets=(0.0, 1.0, 2.0, 3.0, 4.0, 4.9, 5.0, 6.0, 7.0, 7.9, 8.0, 9.0, 10.0),
)

RUBRIC_UNVERIFIABLE_RATE = safe_counter(
    "casa_segura_rubric_unverifiable_total",
    "Per-criterion unverifiable counter.",
    labelnames=("criterion_id",),
)

RUBRIC_FINDINGS_PER_ANALYSIS = safe_histogram(
    "casa_segura_rubric_findings_per_analysis",
    "Histogram of finding count emitted per analysis.",
    buckets=(0, 1, 3, 5, 8, 12, 18, 25, 35, 50),
)


__all__ = [
    "RUBRIC_BAND_TOTAL",
    "RUBRIC_CONTRACT_TYPE_TOTAL",
    "RUBRIC_CRITERION_DURATION",
    "RUBRIC_CRITERION_OUTCOMES",
    "RUBRIC_EVAL_DURATION",
    "RUBRIC_FINDINGS_PER_ANALYSIS",
    "RUBRIC_OVERRIDE_TOTAL",
    "RUBRIC_SCORE_DISTRIBUTION",
    "RUBRIC_UNVERIFIABLE_RATE",
]
