"""Project name canonicalization (CS-031, F2 US-02 / `ProjectNameNormalizer`).

Pure, side-effect-free. Strips accents, lowercases, drops generic words that don't
identify a project, and returns an empty string when nothing meaningful remains
(callers map empty → `unknown_<short_hash>` placeholder, NOT this function).

Divergence note: CS-031 ticket lists an example yielding `residencial los ebanos`
(keeps the generic word). The F2 plan strips `residencial` from `GENERIC_WORDS`,
yielding `los ebanos`. This implementation follows **F2** (the more concrete
source); the divergence is logged in ADR-0003 for product reconciliation.
"""

from __future__ import annotations

import re
import unicodedata

GENERIC_WORDS: frozenset[str] = frozenset(
    {
        "proyecto",
        "residencial",
        "condominio",
        "urbanizacion",
        "lotificacion",
        "complejo",
        "parque",
    }
)

_ALLOWED_CHARS_RE = re.compile(r"[^a-z0-9 -]")
_WHITESPACE_RE = re.compile(r"\s+")
_MIN_RESULT_LEN = 3
_PLACEHOLDER_RE = re.compile(r"^unknown_[0-9a-f]+$")


def _strip_accents(value: str) -> str:
    """NFKD decompose, drop combining marks, recompose — Spanish accent-safe."""
    return "".join(c for c in unicodedata.normalize("NFKD", value) if not unicodedata.combining(c))


def normalize_project_name(raw: str | None) -> str:
    """Apply the F2 normalization rules to a raw project name.

    Returns an empty string when the input is empty/null or when stripping leaves
    fewer than 3 characters. Callers are responsible for mapping empty to a
    placeholder (e.g. `unknown_<sha1[:8]>`).

    Examples:
        >>> normalize_project_name("Residencial Las Palmeras")
        'las palmeras'
        >>> normalize_project_name("PROYECTO URBANO CUMBRES DEL VOLCÁN")
        'urbano cumbres del volcan'
        >>> normalize_project_name("CONDOMINIO ARRECIFE 2")
        'arrecife 2'
        >>> normalize_project_name("")
        ''
        >>> normalize_project_name(None)
        ''
        >>> normalize_project_name("Residencial")
        ''
    """
    if not raw:
        return ""

    folded = _strip_accents(raw).lower()
    cleaned = _ALLOWED_CHARS_RE.sub(" ", folded)
    cleaned = _WHITESPACE_RE.sub(" ", cleaned).strip()
    if not cleaned:
        return ""

    tokens = cleaned.split(" ")
    while tokens and tokens[0] in GENERIC_WORDS:
        tokens.pop(0)
    while tokens and tokens[-1] in GENERIC_WORDS:
        tokens.pop()

    result = " ".join(tokens)
    if len(result) < _MIN_RESULT_LEN:
        return ""
    return result


def is_placeholder_normalized_name(name: str) -> bool:
    """True when `name` matches the system-generated `unknown_<hex>` placeholder pattern.

    Callers use this to skip deduplication on placeholder rows (each placeholder
    should remain a distinct Project row)."""
    return bool(_PLACEHOLDER_RE.match(name))
