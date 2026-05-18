"""Log scrubbing pipeline — CS-331.

A structlog processor + a recursive-dict scrubber that:

* Drops or masks any key whose name is in ``DENY_LOG_KEYS`` (deep scan).
* Truncates string values longer than ``MAX_STRING_LEN`` to avoid
  accidentally pasting bodies / OCR text into a log line.
* Redacts substrings matching email / phone heuristics so an arbitrary
  ``message`` field can't leak contact data.
* Skips entire values for structural / safe keys (timestamps, levels,
  schema metadata, correlation ids, version stamps, http path/method)
  so the redactor does not mangle deterministic fields.

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

# Structural / non-PII keys the scrubber leaves untouched. Inline PII
# regexes are skipped for these because their values are deterministic
# IDs, ISO timestamps, version strings, or routing metadata. Including
# the timestamp here fixes the ``[REDACTED]T01:02:[REDACTED]Z`` bug —
# the phone regex was matching ``2026-05-18`` and ``17.123456Z``.
SAFE_LOG_KEYS: frozenset[str] = frozenset(
    {
        "timestamp",
        "time",
        "@timestamp",
        "level",
        "log_level",
        "logger",
        "logger_name",
        "service",
        "schema_version",
        "correlation_id",
        "request_id",
        "trace_id",
        "span_id",
        "http_path",
        "http_method",
        "http_status",
        "status_code",
        "latency_ms",
        "elapsed_ms",
        "rubric_version",
        "corpus_version",
        "benchmark_version",
        "event",
        "exception",
        "exc_info",
        "stack_info",
        # Identifier keys — UUIDs and short IDs are structural, not PII.
        "analysis_id",
        "submission_id",
        "public_short_id",
        "project_id",
        "report_id",
        "ocr_job_id",
        "delivery_request_id",
        "celery_task_id",
        "id",
    }
)

REDACTED_PLACEHOLDER = "[REDACTED]"
MAX_STRING_LEN = 1024

_EMAIL_RX = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# Phone heuristic: 8+ digits in a `+`-prefixed or grouped run that uses
# only digit-or-(space|dash|paren) separators — periods and colons are
# **excluded** so ISO timestamps and version strings don't match.
# Hex-letter lookahead/lookbehind keeps the regex from clipping UUID
# fragments (UUIDs interleave hex letters with digit groups, e.g.
# ``41231716-5b1f-42a3-...``). A digit-count post-check on the match
# enforces the 8-digit minimum so 4-digit years etc. don't trip it.
_PHONE_CANDIDATE_RX = re.compile(r"(?<![a-fA-F0-9\-])\+?\d[\d\s()\-]{6,}\d(?![a-fA-F0-9\-])")
_PHONE_MIN_DIGITS = 8
_ISO_TIMESTAMP_RX = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}")


def _redact_phone(match: re.Match[str]) -> str:
    snippet = match.group(0)
    digit_count = sum(1 for c in snippet if c.isdigit())
    if digit_count < _PHONE_MIN_DIGITS:
        return snippet
    return REDACTED_PLACEHOLDER


def _redact_inline(text: str) -> str:
    text = _EMAIL_RX.sub(REDACTED_PLACEHOLDER, text)
    text = _PHONE_CANDIDATE_RX.sub(_redact_phone, text)
    if len(text) > MAX_STRING_LEN:
        text = text[: MAX_STRING_LEN - 1] + "…"
    return text


def _looks_like_timestamp(value: str) -> bool:
    return bool(_ISO_TIMESTAMP_RX.match(value))


def _scrub_value(value: Any, *, key: str | None = None) -> Any:  # noqa: PLR0911 — single-pass type dispatch is clearer flat
    if isinstance(value, str):
        if key and key.lower() in SAFE_LOG_KEYS:
            # Truncate runaway values but leave structural keys alone.
            return value if len(value) <= MAX_STRING_LEN else value[: MAX_STRING_LEN - 1] + "…"
        if _looks_like_timestamp(value):
            return value
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
        out[key] = _scrub_value(value, key=key if isinstance(key, str) else None)
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


def safe_log_keys() -> Iterable[str]:
    """Return the safe-key allow-list (read-only view)."""

    return tuple(sorted(SAFE_LOG_KEYS))


__all__ = [
    "DENY_LOG_KEYS",
    "MAX_STRING_LEN",
    "REDACTED_PLACEHOLDER",
    "SAFE_LOG_KEYS",
    "deny_log_keys",
    "safe_log_keys",
    "scrub_event_dict",
    "scrub_payload",
]
