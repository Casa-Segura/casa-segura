"""Zavu webhook HMAC verification (https://docs.zavu.dev/guides/receiving-messages/security.md)."""

from __future__ import annotations

import hashlib
import hmac
import time

_ZAVU_MAX_AGE_SECONDS = 300
_ZAVU_FUTURE_SKEW_SECONDS = 60


def _parse_zavu_signature_header(signature_header: str) -> tuple[int | None, str | None]:
    """Extract ``t`` timestamp and ``v1`` hex digest from ``X-Zavu-Signature``."""
    ts: int | None = None
    v1: str | None = None
    for part in signature_header.split(","):
        segment = part.strip()
        if segment.startswith("t="):
            try:
                ts = int(segment[2:])
            except ValueError:
                return None, None
        elif segment.startswith("v1="):
            v1 = segment[3:]
    return ts, v1


def _zavu_timestamp_valid(ts: int, clock: int) -> bool:
    if clock - ts > _ZAVU_MAX_AGE_SECONDS:
        return False
    return ts <= clock + _ZAVU_FUTURE_SKEW_SECONDS


def verify_zavu_signature(
    *,
    signature_header: str | None,
    raw_body: bytes,
    secret: str,
    now: int | None = None,
) -> bool:
    """Return True if ``X-Zavu-Signature`` matches the raw body and timestamp window."""
    if not signature_header or not secret:
        return False

    ts, v1 = _parse_zavu_signature_header(signature_header)
    if ts is None or not v1:
        return False

    clock = int(time.time()) if now is None else now
    if not _zavu_timestamp_valid(ts, clock):
        return False

    try:
        body_text = raw_body.decode("utf-8")
    except UnicodeDecodeError:
        return False

    signed_payload = f"{ts}.{body_text}"
    expected = hmac.new(
        secret.encode("utf-8"),
        signed_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return len(v1) == len(expected) and hmac.compare_digest(expected, v1)
