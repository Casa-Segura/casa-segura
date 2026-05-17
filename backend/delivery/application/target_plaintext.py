"""Resolve ciphertext destinations — dev stub until KMS wiring (CS-232)."""

from __future__ import annotations

PREFIX = "enc::"


def plaintext_destination(target_value_encrypted: str | None) -> str:
    """Strip Casa dev placeholder prefix `enc::`; production KMS decrypt plugs in here."""
    raw = (target_value_encrypted or "").strip()
    if raw.startswith(PREFIX):
        raw = raw[len(PREFIX) :]
    if not raw:
        raise ValueError("missing_delivery_destination")
    return raw


def plaintext_email(target_value_encrypted: str | None) -> str:
    """Email destinations — basic shape check after stripping ``enc::``."""

    e = plaintext_destination(target_value_encrypted).strip()
    if "@" not in e or e.startswith("@") or e.endswith("@"):
        raise ValueError("delivery_destination_not_email")
    return e


def plaintext_phone(target_value_encrypted: str | None) -> str:
    """SMS destinations — expect E.164 after stripping ``enc::``."""

    p = plaintext_destination(target_value_encrypted).strip()
    if len(p) < 8 or not p.startswith("+"):
        raise ValueError("delivery_destination_not_e164")
    return p
