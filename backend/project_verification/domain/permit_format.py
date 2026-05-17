"""Salvadoran permit format sanity checks (EPIC-12 / CS-352).

Format-only signals — no registry or legal validity claims. Regex catalog is
versioned in-code; extend with domain steward agreement.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum


class PermitFormatVerdict(StrEnum):
    """Machine outcome for synthesis (CS-354)."""

    OK = "format_ok"
    SUSPICIOUS = "format_suspicious"
    UNKNOWN = "format_unknown"


@dataclass(frozen=True, slots=True)
class PermitFormatEvaluation:
    verdict: PermitFormatVerdict
    finding_key: str


# v1 — authority template hints (illustrative placeholders; adjust with legal context owners).
_PATTERNS_OK: tuple[tuple[re.Pattern[str], str], ...] = (
    # Ministerial / central registry style (hypothetical DGMP token)
    (re.compile(r"^DGMP[-\s]?\d{3,6}[-/]?\d{2,4}$", re.IGNORECASE), "permit.format_ok.dgmp"),
    # Year + serial common in billboards
    (re.compile(r"^P[-\s]?\d{4}[-/]?\d{3,6}$", re.IGNORECASE), "permit.format_ok.year_serial"),
    # Municipal prefix + short code (SS = department placeholder)
    (re.compile(r"^MUN[-\s]?[A-Z]{2,4}[-\s]?\d{3,8}$", re.IGNORECASE), "permit.format_ok.municipal"),
    # Expediente / file reference
    (re.compile(r"^EXP[-\s]?\d{4,10}$", re.IGNORECASE), "permit.format_ok.expediente"),
    # Resolution style RES-12345-2024
    (re.compile(r"^RES[-\s]?\d{3,8}[-/]?\d{4}$", re.IGNORECASE), "permit.format_ok.resolution"),
)

# Looks “almost” structured but fails strict templates — advisory unease.
_PATTERN_SUSPICIOUS = re.compile(r"^[A-Z]{1,6}[-\s]?\d{2,8}.*\d+", re.IGNORECASE)


_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _normalize_permit_token(raw: str) -> str:
    t = unicodedata.normalize("NFC", raw or "")
    t = _CONTROL_RE.sub("", t)
    return " ".join(t.split()).strip()


def evaluate_permit_format(
    permit: str,
    municipality_hint: str | None = None,
) -> PermitFormatEvaluation:
    """Return coarse format classification for billboard / manual permit text."""

    token = _normalize_permit_token(permit)
    _ = municipality_hint  # reserved — future locality-specific templates (CS-352 extension)

    if not token:
        return PermitFormatEvaluation(PermitFormatVerdict.UNKNOWN, "permit.format_unknown.empty")

    if len(token) < 4:
        return PermitFormatEvaluation(PermitFormatVerdict.UNKNOWN, "permit.format_unknown.too_short")

    for rx, finding in _PATTERNS_OK:
        if rx.fullmatch(token):
            return PermitFormatEvaluation(PermitFormatVerdict.OK, finding)

    if _PATTERN_SUSPICIOUS.fullmatch(token) and not any(
        rx.fullmatch(token) for rx, _ in _PATTERNS_OK
    ):
        return PermitFormatEvaluation(PermitFormatVerdict.SUSPICIOUS, "permit.format_suspicious.generic")

    return PermitFormatEvaluation(PermitFormatVerdict.UNKNOWN, "permit.format_unknown.free_text")


__all__ = [
    "PermitFormatEvaluation",
    "PermitFormatVerdict",
    "evaluate_permit_format",
]
