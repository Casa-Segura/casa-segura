"""Prometheus instrumentation for the ingestion pipeline (CS-060).

`django_prometheus` is already installed; we just register custom
histograms here so each ingest stage publishes its own latency series.
Labels stay coarse to keep cardinality bounded.

Cardinality budget (PRD §9 / EPIC-02 DoD): well under the <20-combinations
invariant.

  * INGEST_STAGE_DURATION:        2 stages × 3 strategies = 6 series
  * INGEST_EXTRACT_PAGES_DURATION 3 strategies × 3 page buckets = 9 series
  * INGEST_OUTCOMES_TOTAL:        2 outcomes × ~10 error codes ≤ 20 series
  * INGEST_TIMEOUTS_TOTAL:        2 stages × 3 strategies = 6 series
  * OPENROUTER_CALLS:             ~3 models × 2 outcomes = 6 series

Page buckets follow the SLA roll-up taxonomy from
[[PRD_F1_INGESTA_Y_OCR]] §9: `1`, `2-10`, `11+`. Mapping lives in
``page_bucket`` below so callers don't drift apart.
"""

from __future__ import annotations

from prometheus_client import Counter, Histogram

# Stage = route | extract — granular per-extractor latency lives on
# INGEST_EXTRACT_PAGES_DURATION below. `strategy` distinguishes pypdf /
# vision_llm / tesseract.
INGEST_STAGE_DURATION = Histogram(
    "casa_segura_ingest_stage_duration_seconds",
    "Duration of each ingestion pipeline stage.",
    labelnames=("stage", "strategy"),
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 90),
)

# Successful-extraction latency broken down by ``page_bucket`` so the SLA
# roll-up (§9 — 90s P95 submission→report) can isolate per-bucket regressions.
INGEST_EXTRACT_PAGES_DURATION = Histogram(
    "casa_segura_ingest_extract_pages_duration_seconds",
    "Successful extraction latency by strategy and page bucket.",
    labelnames=("strategy", "page_bucket"),
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 90),
)

INGEST_OUTCOMES = Counter(
    "casa_segura_ingest_outcomes_total",
    "Final outcome of a submission (success, rejected, failed).",
    labelnames=("outcome", "error_code"),
)

# Counter incremented when an extractor raises NotAnalyzableReason.TIMEOUT.
# Wired so PRD §US-06 BR-07 / §7.4 (TIMEOUT_EXCEEDED) is observable without
# parsing the generic outcomes counter.
INGEST_TIMEOUTS = Counter(
    "casa_segura_ingest_timeouts_total",
    "Submissions that ended with a TIMEOUT_EXCEEDED extractor failure.",
    labelnames=("stage", "strategy"),
)

OPENROUTER_CALLS = Counter(
    "casa_segura_openrouter_calls_total",
    "Outbound OpenRouter calls by model and outcome.",
    labelnames=("model", "outcome"),
)


def page_bucket(page_count: int | None) -> str:
    """Map a page count to its coarse Prometheus label.

    PRD §9 SLA roll-up: 1-page docs are the bulk of submissions; 2–10
    covers most multi-page rentals; 11+ catches the outliers within the
    50-page per-file cap from [[CS-059]].
    """

    if page_count is None or page_count <= 0:
        return "unknown"
    if page_count == 1:
        return "1"
    if page_count <= 10:
        return "2-10"
    return "11+"
