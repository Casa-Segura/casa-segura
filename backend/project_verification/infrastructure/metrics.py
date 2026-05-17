"""Prometheus metrics for EPIC-12 optional project verification (CS-330 hygiene)."""

from __future__ import annotations

from prometheus_client import Counter, Histogram

# Low-cardinality labels only — no free-text identifiers (PII-sensitive).
PROJECT_VERIFICATION_VISION_SECONDS = Histogram(
    "casa_segura_project_verification_billboard_vision_seconds",
    "Billboard OCR / vision latency for optional flow.",
    labelnames=("flow", "stage"),
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 90),
)

PROJECT_VERIFICATION_OCR_OUTCOMES = Counter(
    "casa_segura_project_verification_ocr_outcomes_total",
    "Structured outcomes for billboard vision extraction.",
    labelnames=("outcome",),
)

PROJECT_VERIFICATION_REPUTATION_OUTCOMES = Counter(
    "casa_segura_project_verification_reputation_queries_total",
    "Reputation lookups for optional verification (additive signal).",
    labelnames=("outcome",),
)
