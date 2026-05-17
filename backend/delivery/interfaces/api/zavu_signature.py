"""Zavu webhook HMAC verification (https://docs.zavu.dev/guides/receiving-messages/security.md)."""

from __future__ import annotations

import hashlib
import hmac
import time

_ZAVU_MAX_AGE_SECONDS = 300
_ZAVU_FUTURE_SKEW_SECONDS = 60


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

    ts: int | None = None
    v1: str | None = None
    for part in signature_header.split(","):
        segment = part.strip()
        if segment.startswith("t="):
            try:
                ts = int(segment[2:])
            except ValueError:
                return False
        elif segment.startswith("v1="):
            v1 = segment[3:]

    if ts is None or not v1:
        return False

    clock = int(time.time()) if now is None else now
    if clock - ts > _ZAVU_MAX_AGE_SECONDS:
        return False
    if ts - clock > _ZAVU_FUTURE_SKEW_SECONDS:
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

    if len(v1) != len(expected):
        return False
    return hmac.compare_digest(expected, v1)
