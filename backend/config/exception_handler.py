"""Casa Segura standard error envelope (CS-009).

Envelope shape:
    {
        "error_code": "string",
        "message": "string",
        "details": { ... } | null,
        "correlation_id": "string",
        "schema_version": "string"
    }

`X-Request-ID` response header mirrors `correlation_id` (set by
`CorrelationIdMiddleware`)."""

from __future__ import annotations

import structlog
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_default_exception_handler

from django.conf import settings
from django.http import Http404

from shared.domain.exceptions import DomainException
from shared.observability.logging import SCHEMA_VERSION

logger = structlog.get_logger(__name__)


def _correlation_id(context) -> str | None:
    request = context.get("request") if context else None
    if request is None:
        return None
    return getattr(request, "correlation_id", None)


def _build_envelope(*, code: str, message: str, details, correlation_id: str | None) -> dict:
    return {
        "error_code": code,
        "message": message,
        "details": details,
        "correlation_id": correlation_id,
        "schema_version": SCHEMA_VERSION,
    }


def _handle_domain_exception(exc: DomainException, context) -> Response:
    correlation_id = _correlation_id(context)
    logger.warning(
        "domain_exception",
        error_code=exc.code,
        status=exc.status,
        message=exc.message,
        details=exc.details,
    )
    return Response(
        _build_envelope(
            code=exc.code,
            message=exc.message,
            details=exc.details or None,
            correlation_id=correlation_id,
        ),
        status=exc.status,
    )


def _map_drf_exception(exc: exceptions.APIException, drf_response: Response, context) -> Response:
    """Translate a DRF APIException response into the Casa Segura envelope."""
    correlation_id = _correlation_id(context)

    if isinstance(exc, exceptions.ValidationError):
        code = "validation_error"
        message = "Request payload failed validation."
        details = drf_response.data
    elif isinstance(exc, exceptions.NotAuthenticated):
        code = "unauthorized"
        message = "Authentication required."
        details = None
    elif isinstance(exc, exceptions.AuthenticationFailed):
        code = "unauthorized"
        message = "Authentication failed."
        details = None
    elif isinstance(exc, exceptions.PermissionDenied):
        code = "forbidden"
        message = "Caller lacks permission for this resource."
        details = None
    elif isinstance(exc, exceptions.NotFound):
        code = "not_found"
        message = "Resource not found."
        details = None
    elif isinstance(exc, exceptions.MethodNotAllowed):
        code = "method_not_allowed"
        message = "HTTP method not allowed."
        details = None
    elif isinstance(exc, exceptions.Throttled):
        code = "throttled"
        message = "Rate limit exceeded."
        details = {"wait_seconds": exc.wait} if exc.wait else None
    else:
        code = getattr(exc, "default_code", "domain_error") or "domain_error"
        message = str(exc.detail) if hasattr(exc, "detail") else exc.__class__.__name__
        details = drf_response.data if isinstance(drf_response.data, dict) else None

    return Response(
        _build_envelope(
            code=code,
            message=message,
            details=details,
            correlation_id=correlation_id,
        ),
        status=drf_response.status_code,
    )


def custom_exception_handler(exc, context):
    """DRF entrypoint — replaces the default exception handler."""
    if isinstance(exc, DomainException):
        return _handle_domain_exception(exc, context)

    if isinstance(exc, Http404):
        exc = exceptions.NotFound()

    drf_response = drf_default_exception_handler(exc, context)
    if drf_response is not None and isinstance(exc, exceptions.APIException):
        return _map_drf_exception(exc, drf_response, context)

    # Unhandled exception. Log full info; respond with sanitized envelope.
    correlation_id = _correlation_id(context)
    logger.exception(
        "unhandled_exception",
        exc_type=exc.__class__.__name__,
    )
    body = _build_envelope(
        code="internal_error",
        message="An unexpected error occurred.",
        details={"exception": exc.__class__.__name__} if settings.DEBUG else None,
        correlation_id=correlation_id,
    )
    return Response(body, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
