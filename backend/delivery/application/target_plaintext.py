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
    addr = plaintext_destination(target_value_encrypted)
    if "@" not in addr:
        raise ValueError("delivery_destination_not_an_email")
    return addr
