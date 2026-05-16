"""PII detection used to guard `Project.metadata` (CS-023).

Conservative: rejects values that look like email, phone, DUI (8-digit
Salvadoran national ID), NIT, IBAN, or any string ≥ 16 chars matching a
digit-dominant pattern that might hide a card number / passport / ID.

Walks nested dicts/lists. Empty dict and primitive non-string scalars are
always safe. False positives are acceptable here: `Project.metadata` is
meant for project-level facts (locality hints, project type), not user
data — anything that smells like PII should be re-modeled elsewhere."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(?:\+?\d[\s\-]?){8,}")
_DUI_RE = re.compile(r"\b\d{8}[-\s]?\d\b")
_NIT_RE = re.compile(r"\b\d{4}[-\s]?\d{6}[-\s]?\d{3}[-\s]?\d\b")
_IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{4,30}\b")
_LONG_DIGIT_RE = re.compile(r"\b\d{10,}\b")

_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (_EMAIL_RE, "email"),
    (_PHONE_RE, "phone"),
    (_DUI_RE, "dui"),
    (_NIT_RE, "nit"),
    (_IBAN_RE, "iban"),
    (_LONG_DIGIT_RE, "long_digit_sequence"),
]


class PIIDetected(ValueError):
    """Raised when a string value matches one of the PII patterns."""

    def __init__(self, kind: str, path: str, value: str):
        self.kind = kind
        self.path = path
        self.value = value
        super().__init__(f"PII ({kind}) detected at metadata path {path!r}")


def _walk(node: Any, path: str) -> Iterable[tuple[str, str]]:
    """Yield (path, string-value) for every string in nested dicts/lists."""
    if isinstance(node, str):
        yield path, node
    elif isinstance(node, dict):
        for k, v in node.items():
            yield from _walk(v, f"{path}.{k}" if path else str(k))
    elif isinstance(node, (list, tuple)):
        for i, v in enumerate(node):
            yield from _walk(v, f"{path}[{i}]")


def assert_no_pii(metadata: Any) -> None:
    """Raise `PIIDetected` if `metadata` contains any value that looks like PII.

    Safe on empty dict / None / primitives. Walks arbitrarily nested
    `dict`/`list` structures and inspects every string leaf."""
    if not metadata:
        return
    for path, text in _walk(metadata, path=""):
        for pattern, kind in _PATTERNS:
            if pattern.search(text):
                raise PIIDetected(kind, path or "<root>", text)
