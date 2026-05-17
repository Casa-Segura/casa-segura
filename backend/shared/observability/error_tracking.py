"""Error tracking SDK with hard scrub hooks — CS-332.

Wraps the Sentry SDK so the integration:

* Stays **inactive** unless ``ERROR_TRACKING_ENABLED=true`` and a DSN is
  provided (CS-332 AC: zero outbound calls when DSN unset).
* Strips request bodies, breadcrumbs, and ``extra`` payloads via
  ``shared.observability.scrubbing`` before each event leaves the
  process. The scrubber is the same one structlog uses (CS-331), so
  Sentry never sees a string structlog would have redacted.
* Stamps every event with the release SHA + environment derived from
  ``DEPLOY_RELEASE`` / ``DEPLOY_STAGE`` env vars.
* Rate-limits per-fingerprint event capture so a runaway loop can't
  flood the aggregator (default 1 event per fingerprint per minute).

If the ``sentry_sdk`` package is not installed the module is still
importable; ``configure_error_tracking`` becomes a no-op and emits a
warning. This keeps test environments slim.
"""

from __future__ import annotations

import logging
import os
import time
from collections import deque
from collections.abc import Iterable
from threading import Lock
from typing import Any

from shared.observability.scrubbing import scrub_payload

logger = logging.getLogger(__name__)

ENV_VARS = (
    "ERROR_TRACKING_ENABLED",
    "ERROR_TRACKING_DSN",
    "DEPLOY_RELEASE",
    "DEPLOY_STAGE",
    "ERROR_TRACKING_SAMPLE_RATE",
    "ERROR_TRACKING_EVENTS_PER_FINGERPRINT_PER_MINUTE",
)

DEFAULT_SAMPLE_RATE = 1.0
DEFAULT_EVENTS_PER_FINGERPRINT_PER_MINUTE = 1


class _FingerprintRateLimiter:
    """Tracks recent capture timestamps per fingerprint."""

    def __init__(self, cap_per_minute: int) -> None:
        self.cap = max(1, int(cap_per_minute))
        self._window: dict[str, deque[float]] = {}
        self._lock = Lock()

    def allow(self, fingerprint: str) -> bool:
        now = time.monotonic()
        cutoff = now - 60.0
        with self._lock:
            bucket = self._window.setdefault(fingerprint, deque())
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= self.cap:
                return False
            bucket.append(now)
            return True


_LIMITER: _FingerprintRateLimiter | None = None


def _build_before_send(limiter: _FingerprintRateLimiter):
    def before_send(event: dict[str, Any], hint: dict[str, Any] | None) -> dict[str, Any] | None:
        # 1. Drop the request body wholesale; keep the URL/method only.
        request = event.get("request")
        if isinstance(request, dict):
            request.pop("data", None)
            request.pop("body", None)
            cookies = request.get("cookies")
            if cookies:
                request["cookies"] = "[REDACTED]"
            headers = request.get("headers")
            if isinstance(headers, dict):
                for sensitive in ("authorization", "cookie", "x-api-key"):
                    if sensitive in headers:
                        headers[sensitive] = "[REDACTED]"

        # 2. Scrub `extra` and `contexts` recursively using the same
        #    deny list the structured logger uses.
        if "extra" in event and isinstance(event["extra"], dict):
            event["extra"] = scrub_payload(event["extra"])
        if "contexts" in event and isinstance(event["contexts"], dict):
            event["contexts"] = scrub_payload(event["contexts"])

        # 3. Drop breadcrumbs that mention OCR / LLM / webhook payloads.
        breadcrumbs = event.get("breadcrumbs", {})
        if isinstance(breadcrumbs, dict):
            values = breadcrumbs.get("values")
            if isinstance(values, list):
                breadcrumbs["values"] = [_scrub_breadcrumb(bc) for bc in values]

        # 4. Rate limit per fingerprint so feedback loops don't flood.
        fingerprint = "|".join(
            event.get("fingerprint", []) or [event.get("type", "error"), event.get("transaction", "")]
        )
        if not limiter.allow(fingerprint):
            return None
        return event

    return before_send


def _scrub_breadcrumb(bc: Any) -> Any:
    if not isinstance(bc, dict):
        return bc
    data = bc.get("data")
    if isinstance(data, dict):
        bc["data"] = scrub_payload(data)
    return bc


def configure_error_tracking(
    *,
    enabled: bool | None = None,
    dsn: str | None = None,
    release: str | None = None,
    stage: str | None = None,
    sample_rate: float | None = None,
    events_per_fingerprint_per_minute: int | None = None,
) -> bool:
    """Initialize the SDK if all preconditions are met.

    Returns ``True`` when the SDK was activated, ``False`` otherwise.
    Reads from env vars when arguments are omitted so the function can
    be called from settings without passing a long argument list.
    """

    enabled = enabled if enabled is not None else _env_bool("ERROR_TRACKING_ENABLED", False)
    dsn = dsn if dsn is not None else os.environ.get("ERROR_TRACKING_DSN", "")
    release = release if release is not None else os.environ.get("DEPLOY_RELEASE", "")
    stage = stage if stage is not None else os.environ.get("DEPLOY_STAGE", "development")
    sample_rate = (
        sample_rate if sample_rate is not None else _env_float("ERROR_TRACKING_SAMPLE_RATE", DEFAULT_SAMPLE_RATE)
    )
    cap = (
        events_per_fingerprint_per_minute
        if events_per_fingerprint_per_minute is not None
        else _env_int(
            "ERROR_TRACKING_EVENTS_PER_FINGERPRINT_PER_MINUTE",
            DEFAULT_EVENTS_PER_FINGERPRINT_PER_MINUTE,
        )
    )

    if not enabled:
        return False
    if not dsn:
        logger.warning("error_tracking.disabled.missing_dsn")
        return False

    try:
        import sentry_sdk  # noqa: PLC0415 — optional dep
        from sentry_sdk.integrations.celery import CeleryIntegration  # noqa: PLC0415
        from sentry_sdk.integrations.django import DjangoIntegration  # noqa: PLC0415
    except ImportError:
        logger.warning("error_tracking.disabled.sentry_sdk_missing")
        return False

    global _LIMITER  # noqa: PLW0603 — singleton state matching the SDK lifecycle
    _LIMITER = _FingerprintRateLimiter(cap)
    sentry_sdk.init(
        dsn=dsn,
        environment=stage,
        release=release or None,
        sample_rate=sample_rate,
        send_default_pii=False,
        attach_stacktrace=True,
        max_breadcrumbs=50,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        before_send=_build_before_send(_LIMITER),
    )
    logger.info("error_tracking.enabled", extra={"stage": stage, "sample_rate": sample_rate})
    return True


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name, "")
    if not raw:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name, "")
    try:
        return float(raw) if raw else default
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "")
    try:
        return int(raw) if raw else default
    except ValueError:
        return default


def declared_env_vars() -> Iterable[str]:
    """Return the env vars the integration reads — used by the runbook."""

    return ENV_VARS


__all__ = [
    "DEFAULT_EVENTS_PER_FINGERPRINT_PER_MINUTE",
    "DEFAULT_SAMPLE_RATE",
    "ENV_VARS",
    "configure_error_tracking",
    "declared_env_vars",
]
