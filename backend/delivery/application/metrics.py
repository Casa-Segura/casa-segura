"""Delivery Prometheus metrics — CS-237 scaffolding."""

from __future__ import annotations

from prometheus_client import Counter, Histogram

DELIVERY_ATTEMPT_TOTAL = Counter(
    "delivery_attempt_total",
    "Delivery attempts started",
    labelnames=("channel",),
)

DELIVERY_FAILED_TOTAL = Counter(
    "delivery_failed_total",
    "Delivery failures",
    labelnames=("channel", "reason"),
)

DELIVERY_SEND_LATENCY_SECONDS = Histogram(
    "delivery_send_latency_seconds",
    "Provider send latency",
    labelnames=("channel",),
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 15.0, 60.0),
)
