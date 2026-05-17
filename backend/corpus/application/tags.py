"""Tag/relevance normalization (CS-082).

The corpus YAML uses Spanish prose with accents and inconsistent case for
tags and finding categories. We normalise them to a stable lowercase
diacritic-free slug so:

  * Postgres GIN indexes on `tags[]` / `relevance_for_findings[]` aren't
    fragmented by `ñ` vs `n`, capital letters or spacing.
  * Retrieval (CS-085/086) can pre-filter chunks by tag without a
    fuzzy match.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def normalize_tag(value: str) -> str:
    """Return a slug-safe representation of `value`.

    Steps: lowercase → strip → unicode NFKD → drop combining marks →
    replace any run of non-alphanumerics with `_` → strip leading/trailing
    underscores.
    """

    if value is None:
        return ""
    text = str(value).strip().lower()
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    slug = _NON_ALNUM_RE.sub("_", stripped).strip("_")
    return slug


def normalize_tags(values: Iterable) -> list[str]:
    """Normalise + dedupe (preserving first-seen order)."""

    seen: dict[str, None] = {}
    for raw in values or []:
        slug = normalize_tag(raw)
        if slug:
            seen.setdefault(slug, None)
    return list(seen.keys())
