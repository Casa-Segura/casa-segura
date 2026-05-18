"""Prometheus histograms for F2 pipeline steps and OpenRouter latency.

Cardinality / privacy (CS-330): ``step`` is a fixed enum of orchestrator stages;
``model`` and ``outcome`` are coarse strings. Do **not** add submission_id,
submission_hash, phones, emails, or text-derived dimensions as metric labels.
"""

from __future__ import annotations

from prometheus_client import Histogram

# Align buckets with ingestion OCR histograms (PRD §9 SLA roll-up).
_PIPELINE_HISTOGRAM_BUCKETS = (0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 90)

F2_STAGE_DURATION = Histogram(
    "casa_segura_f2_stage_duration_seconds",
    "Successful F2 orchestrator step duration (wall-clock per step).",
    labelnames=("step",),
    buckets=_PIPELINE_HISTOGRAM_BUCKETS,
)

OPENROUTER_REQUEST_DURATION = Histogram(
    "casa_segura_openrouter_request_duration_seconds",
    "OpenRouter /chat/completions attempt duration by model and outcome.",
    labelnames=("model", "outcome"),
    buckets=_PIPELINE_HISTOGRAM_BUCKETS,
)

__all__ = ["F2_STAGE_DURATION", "OPENROUTER_REQUEST_DURATION"]
