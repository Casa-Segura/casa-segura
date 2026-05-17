"""Classify provider/Zavu failures — CS-243."""

from __future__ import annotations

from dataclasses import dataclass

from delivery.domain.enums import ErrorClassification

try:
    import zavudev
except ImportError:  # pragma: no cover - optional until SDK installed in minimal envs
    zavudev = None  # type: ignore[assignment]


@dataclass(frozen=True, slots=True)
class ClassifiedDeliveryError(Exception):
    """Wraps underlying provider failure with retry classification."""

    classification: str
    reason_code: str
    message: str

    def __str__(self) -> str:  # pragma: no cover - diagnostic only
        return self.message


def classify_zavu_exception(exc: BaseException) -> ClassifiedDeliveryError:
    """Map Zavu SDK / HTTP errors to transient vs permanent."""

    msg = str(exc)
    perm = ErrorClassification.PERMANENT.value
    transient = ErrorClassification.TRANSIENT.value

    if zavudev is None:
        return ClassifiedDeliveryError(
            classification=transient,
            reason_code="provider_import_error",
            message=msg,
        )

    z = zavudev
    rules: tuple[tuple[tuple[type[BaseException], ...], str, str], ...] = (
        ((z.AuthenticationError,), perm, "provider_auth"),
        ((z.BadRequestError, z.UnprocessableEntityError), perm, "provider_bad_request"),
        ((z.NotFoundError, z.PermissionDeniedError), perm, "provider_client_error"),
        (
            (
                z.RateLimitError,
                z.APITimeoutError,
                z.APIConnectionError,
                z.InternalServerError,
                z.ConflictError,
            ),
            transient,
            "provider_transient",
        ),
    )
    for types, classification, reason_code in rules:
        if isinstance(exc, types):
            return ClassifiedDeliveryError(
                classification=classification,
                reason_code=reason_code,
                message=msg,
            )

    if isinstance(exc, z.APIStatusError):
        code = getattr(exc, "status_code", None) or 0
        retryable = code in (408, 409, 429) or code >= 500
        return ClassifiedDeliveryError(
            classification=transient if retryable else perm,
            reason_code="provider_http_retryable" if retryable else "provider_http_terminal",
            message=msg,
        )

    return ClassifiedDeliveryError(classification=transient, reason_code="provider_unknown", message=msg)


def classify_generic(exc: BaseException) -> ClassifiedDeliveryError:
    """Fallback when transport is not Zavu."""

    return ClassifiedDeliveryError(
        classification=ErrorClassification.TRANSIENT.value,
        reason_code="generic",
        message=str(exc),
    )
