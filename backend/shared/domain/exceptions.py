"""DomainException base + canonical public error code registry (CS-009).

Every feature module raises `DomainException` (or a subclass) for expected
business errors. The DRF custom `exception_handler` catches these and emits the
standard envelope. Unknown exceptions fall through to `internal_error` HTTP 500.

Error codes are stable, snake_case, and namespaced by domain (e.g.
`ingestion.disclaimer_required`, `delivery.target_invalid`). Each module may
extend the registry, but only via this single module to keep the public surface
greppable."""

from __future__ import annotations

from typing import Any


class DomainException(Exception):
    """Base class for all business/domain errors.

    Args:
        message: human-readable description (kept short; bulk goes in `details`)
        code: stable error code (snake_case, namespaced)
        status: HTTP status to return when this error reaches the view layer
        details: optional structured context (field errors, validation traces, etc.)
    """

    default_message: str = "An unexpected domain error occurred."
    default_code: str = "domain_error"
    default_status: int = 400

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        status: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.code = code or self.default_code
        self.status = status or self.default_status
        self.details = details or {}
        super().__init__(self.message)


class ValidationDomainException(DomainException):
    default_code = "validation_error"
    default_status = 400


class NotFoundDomainException(DomainException):
    default_code = "not_found"
    default_status = 404


class ConflictDomainException(DomainException):
    default_code = "conflict"
    default_status = 409


class UnauthorizedDomainException(DomainException):
    default_code = "unauthorized"
    default_status = 401


class ForbiddenDomainException(DomainException):
    default_code = "forbidden"
    default_status = 403


class UpstreamDomainException(DomainException):
    """For OpenRouter / SMS / SMTP / KMS failures that should bubble as 502."""

    default_code = "upstream_error"
    default_status = 502


# Canonical public error codes registry. Feature modules may extend this dict;
# do NOT shadow existing keys — pick a new namespace.
PUBLIC_ERROR_CODES: dict[str, str] = {
    "domain_error": "Generic domain error.",
    "DISCLAIMER_REQUIRED": "Disclaimer must be explicitly accepted before ingestion.",
    "validation_error": "Request payload failed validation.",
    "not_found": "Resource not found.",
    "conflict": "Resource state conflict.",
    "unauthorized": "Caller is not authenticated.",
    "forbidden": "Caller lacks permission for this resource.",
    "internal_error": "Unhandled server error.",
    "upstream_error": "Upstream provider failed.",
    "throttled": "Rate limit exceeded.",
    "project_verification_disabled": "Optional project verification stubs are disabled for this deployment.",
}
