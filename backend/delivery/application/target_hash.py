"""Salted SHA-256 for delivery destinations — CS-232 / CS-248 resend gate."""

from __future__ import annotations

import hashlib

from django.conf import settings


def normalize_target_for_hash(raw: str) -> str:
    """Normalize user-supplied destination before hashing (email case-fold)."""

    t = (raw or "").strip()
    if "@" in t:
        return t.lower()
    return t


def hash_delivery_target(raw: str) -> str:
    """``SHA256(salt || normalized)`` hex digest — aligns with resend verifier."""

    salt = (getattr(settings, "DELIVERY_TARGET_HASH_SALT", "") or "dev-insecure-salt").encode()
    normalized = normalize_target_for_hash(raw).encode("utf-8")
    return hashlib.sha256(salt + b"|" + normalized).hexdigest()
