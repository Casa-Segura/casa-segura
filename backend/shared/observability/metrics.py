"""Cross-cutting Prometheus metric factories with PII-label guards — CS-330.

Centralizes:

* The list of *forbidden* label keys (anything that could carry
  per-user, per-contract, or content-derived data).
* A wrapper around ``prometheus_client.Counter`` / ``Histogram`` that
  rejects forbidden labels at registration time, so a regression that
  adds e.g. ``submission_hash`` or ``project_normalized`` as a label
  fails on import rather than leaking telemetry to the dashboard.

Other apps (``ingestion``, ``delivery``, ``rubric``, ``reports``) define
their own metric files but should obtain Counter/Histogram instances via
``safe_counter`` / ``safe_histogram`` to enforce the contract.
"""

from __future__ import annotations

from collections.abc import Iterable

from prometheus_client import Counter, Histogram
from prometheus_client.metrics import MetricWrapperBase

# CS-330 AC: explicit deny list — must never appear in a metric label
# (or as a dimension value in a coarse enum). Lower-cased compare.
FORBIDDEN_METRIC_LABELS: frozenset[str] = frozenset(
    {
        # Identity / per-user attribution.
        "submission_hash",
        "project_normalized",
        "project_name",
        "project_canonical_name",
        "delivery_target_hash",
        "delivery_target",
        "delivery_target_value",
        "target_value",
        "target_value_encrypted",
        "email",
        "phone",
        "phone_number",
        "msisdn",
        "ip",
        "ip_address",
        "user_agent",
        "request_id",
        # Content-derived.
        "contract_text",
        "ocr_text",
        "extracted_text",
        "evidence_snippet",
        "evidence_clause_snippet",
        "raw_clause",
        "clause",
        "finding_description",
        "justification",
        # Surrogates that could correlate timelines back to a user.
        "session_id",
        "auth_token",
        "jwt",
    }
)


class ForbiddenMetricLabelError(ValueError):
    """Raised when a forbidden label key is requested for a metric."""


def _validate_labelnames(metric_name: str, labelnames: Iterable[str]) -> tuple[str, ...]:
    out = tuple(labelnames)
    bad = {name for name in out if name.lower() in FORBIDDEN_METRIC_LABELS}
    if bad:
        raise ForbiddenMetricLabelError(
            f"metric {metric_name!r} cannot use forbidden label(s) {sorted(bad)} (CS-330 deny list)"
        )
    return out


def safe_counter(
    name: str,
    documentation: str,
    *,
    labelnames: Iterable[str] = (),
) -> Counter:
    """Return a ``Counter`` after rejecting forbidden labels."""

    return Counter(name, documentation, labelnames=_validate_labelnames(name, labelnames))


def safe_histogram(
    name: str,
    documentation: str,
    *,
    labelnames: Iterable[str] = (),
    buckets: tuple[float, ...] | None = None,
) -> Histogram:
    """Return a ``Histogram`` after rejecting forbidden labels."""

    kwargs: dict[str, object] = {"labelnames": _validate_labelnames(name, labelnames)}
    if buckets is not None:
        kwargs["buckets"] = buckets
    return Histogram(name, documentation, **kwargs)  # type: ignore[arg-type]


def assert_safe_labelnames(metric: MetricWrapperBase) -> None:
    """Defensive runtime check usable from tests / startup."""

    bad = {name for name in metric._labelnames if name.lower() in FORBIDDEN_METRIC_LABELS}
    if bad:
        raise ForbiddenMetricLabelError(f"metric {metric._name!r} has forbidden label(s) {sorted(bad)}")


__all__ = [
    "FORBIDDEN_METRIC_LABELS",
    "ForbiddenMetricLabelError",
    "assert_safe_labelnames",
    "safe_counter",
    "safe_histogram",
]
