"""Thin SMS adapter stub — CS-238 placeholder until provider is chosen."""

from __future__ import annotations


class SmsProviderNotConfiguredError(RuntimeError):
    """Raised when SMS send is invoked without a configured provider."""


def send_sms_stub(*, to_e164: str, body: str) -> str:
    """Reserved for CS-238 — returns fake message id in tests only."""

    raise SmsProviderNotConfiguredError(f"sms stub ({to_e164}): {body[:32]}")
