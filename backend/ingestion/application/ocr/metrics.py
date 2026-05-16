"""Prometheus instrumentation for the ingestion pipeline (CS-060).

`django_prometheus` is already installed; we just register custom
histograms here so each ingest stage publishes its own latency series.
Labels stay coarse to keep cardinality bounded.
"""

from __future__ import annotations

from prometheus_client import Counter, Histogram

# Stage = upload | route | extract | language | persist
INGEST_STAGE_DURATION = Histogram(
    "casa_segura_ingest_stage_duration_seconds",
    "Duration of each ingestion pipeline stage.",
    labelnames=("stage", "strategy"),
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 90),
)

INGEST_OUTCOMES = Counter(
    "casa_segura_ingest_outcomes_total",
    "Final outcome of a submission (success, rejected, failed).",
    labelnames=("outcome", "error_code"),
)

OPENROUTER_CALLS = Counter(
    "casa_segura_openrouter_calls_total",
    "Outbound OpenRouter calls by model and outcome.",
    labelnames=("model", "outcome"),
)
