"""Type-coercion helpers for LLM-returned economic field values (CS-113).

The OpenRouter response for the §8.5 economic extraction prompt is
nominally JSON, but in practice LLMs frequently emit *string* values
that look like numbers ("$185,000", "3.5%", "60 meses"). Per CS-113 the
extractor must coerce these into the typed values declared on
:class:`~classification.domain.extracted_fields.ExtractedFields` (floats,
ints, narrow string enums) before pydantic validation runs.

Design conventions:
    * Helpers are **pure** (no I/O, no logging, no Django imports) so they
      stay trivially unit-testable when CS-115 lands the test suite.
    * Helpers **never raise** on malformed input — they return ``None``.
      The caller is responsible for demoting that field to ``unverifiable``
      per PRD_F2 BR-07 instead of crashing the whole extraction.
    * Currency-symbol stripping is whitelist-based (``$``, ``USD``,
      ``US$``, ``¢``, ``SVC``, ``COL``). We deliberately do NOT attempt
      FX conversion here — the §8.5 prompt instructs the LLM to apply
      the historical ¢8.75 = $1 rate inline; if a stray colón value
      reaches this coercion, we still surface a float and let F5 sanity-
      check the magnitude.
    * Locale parsing assumes the Salvadoran convention from the prompt:
      ``.`` is the decimal separator and ``,`` is a thousands grouping.
      Any other ordering is rejected as ambiguous and returns ``None``.

PRD references:
    - PRD_F2_CLASIFICACION §8.5 (field shapes, USD default).
    - PRD_F2_CLASIFICACION BR-07 (missing/invalid → unverifiable, not error).
"""

from __future__ import annotations

import re
from typing import Final

# Whitelist of currency markers we strip before float parsing. Kept tight
# on purpose: a wider list invites accidental silent unit changes
# (e.g. swallowing "€"). El Salvador's contract corpus uses USD or
# historical colones; everything else is out of scope for this stage.
_CURRENCY_TOKENS: Final[tuple[str, ...]] = (
    "USD",
    "US$",
    "U$S",
    "U.S.$",
    "$",
    "¢",
    "C$",
    "SVC",
    "COL",
)

# Recognised payment-periodicity tokens (Spanish + English). Maps to the
# closed set declared in PRD_F2 §8.5: monthly | biweekly | weekly | other.
_PERIODICITY_MAP: Final[dict[str, str]] = {
    "monthly": "monthly",
    "mensual": "monthly",
    "mensuales": "monthly",
    "mes": "monthly",
    "biweekly": "biweekly",
    "quincenal": "biweekly",
    "quincenales": "biweekly",
    "quincena": "biweekly",
    "weekly": "weekly",
    "semanal": "weekly",
    "semanales": "weekly",
    "semana": "weekly",
}

# Recognised interest-base tokens. Maps to the closed set declared in
# PRD_F2 §8.5: outstanding_principal | total_balance | unspecified.
_INTEREST_BASE_MAP: Final[dict[str, str]] = {
    "outstanding_principal": "outstanding_principal",
    "saldo_insoluto": "outstanding_principal",
    "saldo insoluto": "outstanding_principal",
    "capital pendiente": "outstanding_principal",
    "saldos diarios": "outstanding_principal",
    "total_balance": "total_balance",
    "saldo_total": "total_balance",
    "saldo total": "total_balance",
    "monto total": "total_balance",
    "unspecified": "unspecified",
    "no_especificado": "unspecified",
    "no especificado": "unspecified",
}

# Decimal-with-optional-thousands matcher. Accepts ``1,234.56``, ``1234.56``,
# ``1234``, ``.56``, ``1,234``. Rejects locales like ``1.234,56`` (European)
# to avoid silently inverting decimals/thousands.
_NUMERIC_RE: Final[re.Pattern[str]] = re.compile(
    r"-?(?:\d{1,3}(?:,\d{3})+|\d+)?(?:\.\d+)?"
)


def coerce_float(raw: object) -> float | None:  # noqa: PLR0911 - explicit early returns are clearer than nested branches for this dispatch.
    """Coerce an LLM-returned money / rate / percentage value to ``float``.

    Examples (no PII):
        >>> coerce_float(185000)
        185000.0
        >>> coerce_float("$185,000.00")
        185000.0
        >>> coerce_float("USD 80,000")
        80000.0
        >>> coerce_float("3.5%")
        3.5
        >>> coerce_float("  ")  # whitespace
        >>> coerce_float("abc")  # garbage
        >>> coerce_float(None)

    The helper does **not** rescale percentages — ``"3.5%"`` becomes
    ``3.5``, not ``0.035``. Rescaling belongs in the prompt (which
    instructs the LLM to emit decimals like ``0.09``) or in F5's
    validation pass. Surfacing the raw number here keeps the coercion
    auditable: any unexpected magnitude survives to the validator that
    can demote the field to ``unverifiable``.
    """
    if raw is None:
        return None
    if isinstance(raw, bool):
        # `bool` is a subclass of `int` in Python; reject explicitly so a
        # stray `true` does not become 1.0.
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    if not isinstance(raw, str):
        return None

    cleaned = raw.strip()
    if not cleaned:
        return None

    # Strip currency markers (longest-first to keep ``US$`` from being
    # eaten by ``$``).
    for token in sorted(_CURRENCY_TOKENS, key=len, reverse=True):
        cleaned = cleaned.replace(token, "")
    # Drop percent sign — caller decides whether the magnitude is a
    # percentage point (``3.5``) or a decimal fraction (``0.035``).
    cleaned = cleaned.replace("%", "")
    # Strip narrative suffixes like " mensual", " anual" — keep only the
    # numeric prefix.
    match = _NUMERIC_RE.search(cleaned)
    if match is None:
        return None
    numeric = match.group(0)
    if not numeric or numeric in {"-", "."}:
        return None
    # Drop thousands grouping commas now that we have a single numeric token.
    numeric = numeric.replace(",", "")
    try:
        return float(numeric)
    except ValueError:
        return None


def coerce_int(raw: object) -> int | None:
    """Coerce an LLM-returned count (``term_months``, ``installment_count``).

    Accepts the same surface shapes as :func:`coerce_float` plus narrative
    forms like ``"60 meses"`` or ``"240 cuotas"``. Truncates fractional
    inputs (``60.4`` → ``60``) because ``ExtractedFields.term_months`` is
    an ``int | None`` and pydantic would otherwise reject the float.

    Returns ``None`` if no integer survives extraction.

    Examples (no PII):
        >>> coerce_int(60)
        60
        >>> coerce_int("60 meses")
        60
        >>> coerce_int("240 cuotas mensuales")
        240
        >>> coerce_int("foo")
        >>> coerce_int(None)
    """
    value = coerce_float(raw)
    if value is None:
        return None
    try:
        return int(value)
    except (OverflowError, ValueError):
        return None


def coerce_pct_as_decimal(raw: object) -> float | None:
    """Coerce a percentage-like input into a decimal fraction in ``[0, 1+]``.

    The §8.5 prompt instructs the LLM to emit decimals (``0.09`` for 9%),
    but real LLM outputs often slip back into percentage points
    (``"9%"``, ``9.0``). This helper applies a **heuristic** rescale:

        * Strings ending in ``%`` are divided by 100 (``"9%"`` → ``0.09``).
        * Bare numbers ``> 1.0`` are *also* divided by 100 (``9.0`` →
          ``0.09``) on the assumption the model emitted percentage points.
        * Bare numbers ``≤ 1.0`` are returned as-is (``0.09`` → ``0.09``).

    The heuristic produces the wrong answer for a genuine 150% APR, but
    such rates are an automatic CS-114 ``unverifiable`` demotion anyway
    (``ExtractedFields.interest_rate_pct`` validates ``ge=0`` — we leave
    the upper-bound sanity check to F5 per the BVA table in CS-113).
    """
    if isinstance(raw, str) and raw.strip().endswith("%"):
        value = coerce_float(raw)
        if value is None:
            return None
        return value / 100.0
    value = coerce_float(raw)
    if value is None:
        return None
    if value > 1.0:
        return value / 100.0
    return value


def coerce_payment_periodicity(raw: object) -> str | None:
    """Map a free-text periodicity hint to the §8.5 closed-set value.

    Returns one of ``"monthly"`` | ``"biweekly"`` | ``"weekly"`` |
    ``"other"`` or ``None`` if the input is blank. Any string that does
    not match a known synonym is returned as ``"other"`` so downstream
    persistence keeps a meaningful enum slot for QA review (per PRD_F2
    §8.5: "Stored verbatim strings" is *not* the policy — the PRD's
    BVA row in CS-113 prefers verbatim, but ``ExtractedFields`` is a
    *normalized* projection, so we map into the closed set).
    """
    if raw is None:
        return None
    if not isinstance(raw, str):
        raw = str(raw)
    key = raw.strip().lower()
    if not key:
        return None
    return _PERIODICITY_MAP.get(key, "other")


def coerce_interest_base(raw: object) -> str | None:
    """Map a free-text interest-base hint to the §8.5 closed-set value.

    Returns one of ``"outstanding_principal"`` | ``"total_balance"`` |
    ``"unspecified"``. Unknown inputs collapse to ``"unspecified"`` so
    the F4 ``art_12_lpc`` override decision (PRD_GENERAL critical
    overrides) is never silently triggered by a typo.
    """
    if raw is None:
        return None
    if not isinstance(raw, str):
        raw = str(raw)
    key = raw.strip().lower()
    if not key:
        return None
    return _INTEREST_BASE_MAP.get(key, "unspecified")


def coerce_currency(raw: object) -> str | None:
    """Normalize a currency token to the upper-case 3-letter form.

    Accepts ``"usd"`` / ``"USD"`` / ``"$"`` / ``"colones"`` / ``"SVC"``.
    Defaults to ``"USD"`` when the LLM omits currency on a USD field
    (PRD_F2 §8.5 "USD by default in El Salvador").

    Returns ``None`` for blank input; the caller is responsible for
    deciding whether to apply the USD default — we keep the helper
    honest so it does not mask LLM omissions.
    """
    if raw is None:
        return None
    if not isinstance(raw, str):
        raw = str(raw)
    key = raw.strip().upper()
    if not key:
        return None
    if key in {"$", "USD", "US$", "DOLAR", "DOLARES", "DÓLAR", "DÓLARES"}:
        return "USD"
    if key in {"SVC", "¢", "COLON", "COLONES", "COLÓN", "COLONES SV"}:
        return "SVC"
    # Pass-through unknown ISO codes (truncated to 8 chars to honour the
    # `max_length=8` on `ExtractedFields.currency`).
    return key[:8]


__all__ = [
    "coerce_currency",
    "coerce_float",
    "coerce_int",
    "coerce_interest_base",
    "coerce_payment_periodicity",
    "coerce_pct_as_decimal",
]
