"""Request-scoped correlation ID middleware (CS-007).

Pulls `X-Request-ID` from the incoming request (or generates a UUID4 fallback),
stuffs it into structlog's contextvars so every log line within the request
includes it, and mirrors it back as `X-Request-ID` on the response."""

from __future__ import annotations

import uuid
from collections.abc import Callable

import structlog

from django.http import HttpRequest, HttpResponse

CORRELATION_HEADER = "X-Request-ID"
_MAX_HEADER_LEN = 128


def _coerce_correlation_id(raw: str | None) -> str:
    """Trim, reject empty/oversize, fall back to UUID4."""
    if not raw:
        return uuid.uuid4().hex
    trimmed = raw.strip()
    if not trimmed or len(trimmed) > _MAX_HEADER_LEN:
        return uuid.uuid4().hex
    return trimmed


class CorrelationIdMiddleware:
    """Bind correlation_id into structlog contextvars for the duration of one request."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        raw = request.META.get(f"HTTP_{CORRELATION_HEADER.upper().replace('-', '_')}")
        correlation_id = _coerce_correlation_id(raw)

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id,
            http_method=request.method,
            http_path=request.path,
        )
        # Stash on the request for downstream code (settings.SECURE_PROXY_SSL_HEADER
        # exposure, error handlers); typing-wise this is an ad-hoc attribute on
        # Django's HttpRequest, hence the ignore.
        request.correlation_id = correlation_id  # type: ignore[attr-defined]

        try:
            response = self.get_response(request)
        finally:
            structlog.contextvars.clear_contextvars()

        response[CORRELATION_HEADER] = correlation_id
        return response
