"""Log scrubbing pipeline — CS-331.

A structlog processor + a recursive-dict scrubber that:

* Drops or masks any key whose name is in ``DENY_LOG_KEYS`` (deep scan).
* Truncates string values longer than ``MAX_STRING_LEN`` to avoid
  accidentally pasting bodies / OCR text into a log line.
* Redacts substrings matching email / phone heuristics so an arbitrary
  ``message`` field can't leak contact data.

The scrubber is the *first* processor in the structlog chain (see
``shared/observability/logging.py``) so every downstream processor —
including the JSON renderer and the Sentry breadcrumb hook in CS-332 —
sees only sanitized data.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, MutableMapping
from typing import Any

# Explicit deny list (CS-331 AC: "policy lists explicit deny keys").
# Lower-cased compare; nested dicts are scrubbed recursively.
DENY_LOG_KEYS: frozenset[str] = frozenset(
    {
        # Contract / OCR content.
        "contract_text",
        "ocr_text",
        "extracted_text",
        "extracted_text_excerpt",
        "evidence_snippet",
        "evidence_clause_snippet",
        "raw_clause",
        "clause",
        "developer_name_from_user",
        "pdf_bytes",
        "image_bytes",
        # LLM payloads.
        "prompt",
        "system_prompt",
        "user_prompt",
        "messages",
        "openrouter_prompt",
        "llm_payload",
        "completion",
        # Webhook / SMS / email raw bodies.
        "raw_body",
        "raw_payload",
        "webhook_payload",
        "sms_provider_payload",
        "email_html_body",
        "email_text_body",
        # PII / delivery targets.
        "email",
        "phone",
        "phone_number",
        "msisdn",
        "delivery_target",
        "delivery_target_value",
        "target_value",
        "target_value_encrypted",
        "authorization",
        "auth_token",
        "jwt",
        "password",
        "secret",
        "api_key",
    }
)

REDACTED_PLACEHOLDER = "[REDACTED]"
MAX_STRING_LEN = 1024

_EMAIL_RX = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# Phone: 8+ digits with optional +/spaces/dashes; coarse but matches SV
# numbers (e.g. +503 7000-0000 or 70000000).
_PHONE_RX = re.compile(r"\+?\d[\d\s().-]{7,}\d")


def _redact_inline(text: str) -> str:
    text = _EMAIL_RX.sub(REDACTED_PLACEHOLDER, text)
    text = _PHONE_RX.sub(REDACTED_PLACEHOLDER, text)
    if len(text) > MAX_STRING_LEN:
        text = text[: MAX_STRING_LEN - 1] + "…"
    return text


def _scrub_value(value: Any) -> Any:
    if isinstance(value, str):
        return _redact_inline(value)
    if isinstance(value, dict):
        return _scrub_mapping(value)
    if isinstance(value, (list, tuple)):
        return type(value)(_scrub_value(item) for item in value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        return f"[bytes:{len(bytes(value))}]"
    return value


def _scrub_mapping(payload: MutableMapping[str, Any] | dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in payload.items():
        key_lower = key.lower() if isinstance(key, str) else key
        if isinstance(key_lower, str) and key_lower in DENY_LOG_KEYS:
            out[key] = REDACTED_PLACEHOLDER
            continue
        out[key] = _scrub_value(value)
    return out


def scrub_event_dict(_: Any, __: str, event_dict: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    """structlog processor — strips deny-list keys, redacts inline PII.

    The processor mutates and returns the same dict (structlog
    contract) so downstream processors see the sanitized view.
    """

    scrubbed = _scrub_mapping(dict(event_dict))
    event_dict.clear()
    event_dict.update(scrubbed)
    return event_dict


def scrub_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Public helper for ad-hoc scrubbing (e.g. Sentry ``before_send``)."""

    return _scrub_mapping(payload)


def deny_log_keys() -> Iterable[str]:
    """Return the deny-list (read-only view) for documentation/test use."""

    return tuple(sorted(DENY_LOG_KEYS))


__all__ = [
    "DENY_LOG_KEYS",
    "MAX_STRING_LEN",
    "REDACTED_PLACEHOLDER",
    "deny_log_keys",
    "scrub_event_dict",
    "scrub_payload",
]
