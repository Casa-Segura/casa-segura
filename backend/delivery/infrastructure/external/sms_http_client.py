"""HTTP SMS adapter — CS-238 (+ error mapping CS-243)."""

from __future__ import annotations

from typing import Any

import httpx

from django.conf import settings

from delivery.application.provider_errors import ClassifiedDeliveryError, classify_sms_provider_response
from delivery.domain.enums import ErrorClassification


def _classified_error_for_http_response(resp: httpx.Response) -> ClassifiedDeliveryError | None:
    if resp.status_code == 429:
        return ClassifiedDeliveryError(
            classification=ErrorClassification.TRANSIENT.value,
            reason_code="RATE_LIMITED",
            message="sms rate limited",
        )
    if resp.status_code in (401, 403):
        return ClassifiedDeliveryError(
            classification=ErrorClassification.PERMANENT.value,
            reason_code="PROVIDER_AUTH",
            message="sms auth failure",
        )
    if 400 <= resp.status_code < 500:
        return classify_sms_provider_response(status_code=resp.status_code, body_text=resp.text)
    if resp.status_code >= 500:
        return ClassifiedDeliveryError(
            classification=ErrorClassification.TRANSIENT.value,
            reason_code="PROVIDER_UNAVAILABLE",
            message=f"sms server {resp.status_code}",
        )
    return None


def _message_id_from_json_body(data: object, *, fallback: str) -> str:
    if not isinstance(data, dict):
        return fallback
    raw = data.get("id") or data.get("message_id") or data.get("sid")
    if raw:
        return str(raw)
    return fallback


def send_sms_e164(*, to_e164: str, body: str, idempotency_key: str) -> str:
    """POST JSON to SMS provider; raises ``ClassifiedDeliveryError`` on failure."""

    provider = (getattr(settings, "SMS_PROVIDER", "stub") or "stub").lower()
    budget = int(getattr(settings, "SMS_SEGMENT_CHAR_BUDGET", 480))
    if len(body) > budget:
        raise ClassifiedDeliveryError(
            classification=ErrorClassification.PERMANENT.value,
            reason_code="sms_payload_too_large",
            message="sms body exceeds segment budget",
        )

    if provider == "stub":
        _ = to_e164
        return f"stub_{idempotency_key}"

    base = getattr(settings, "SMS_API_BASE_URL", "") or ""
    key = getattr(settings, "SMS_API_KEY", "") or ""
    sender = getattr(settings, "SMS_FROM", "") or ""
    timeout = float(getattr(settings, "SMS_TIMEOUT_SECONDS", 15))
    if not base.strip() or not key.strip():
        raise ClassifiedDeliveryError(
            classification=ErrorClassification.PERMANENT.value,
            reason_code="sms_not_configured",
            message="SMS_API_BASE_URL or SMS_API_KEY missing",
        )

    url = base.rstrip("/") + "/messages"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload: dict[str, Any] = {"to": to_e164, "from": sender, "body": body}
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, json=payload, headers=headers)
    except httpx.TimeoutException as exc:
        raise ClassifiedDeliveryError(
            classification=ErrorClassification.TRANSIENT.value,
            reason_code="PROVIDER_UNAVAILABLE",
            message="sms timeout",
        ) from exc
    except httpx.RequestError as exc:
        raise ClassifiedDeliveryError(
            classification=ErrorClassification.TRANSIENT.value,
            reason_code="PROVIDER_UNAVAILABLE",
            message=str(exc),
        ) from exc

    err = _classified_error_for_http_response(resp)
    if err is not None:
        raise err

    try:
        data = resp.json()
    except ValueError:
        data = {}
    return _message_id_from_json_body(data, fallback=idempotency_key)
