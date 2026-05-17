"""PRD F8 US-07/US-08 anonymization helpers (CS-273).

Bucket edge conventions match CS-273 BVA tables (formal PRD US-08 wins over rubric text):

* ``price_cash`` (USD): ``[0,30k) -> "<30k"``, ``[30k,60k) -> "30k-60k"``, … up to ``>=250k -> ">250k"``.
* ``down_payment_pct``: inclusive lower band ``[0,5] -> "0-5"``, then ``(5,10] -> "5-10"``, …
* ``annual_rate_pct``: ``[0,7) -> "<7"``, ``[7,9) -> "7-9"``, ``[9,12) -> "9-12"``, ``[12,15) -> "12-15"``,
  ``[15,20) -> "15-20"``, ``>=20 -> ">20"``.
* ``term_months``: ``<120 -> "<120"``, ``[120,180) -> "120-180"``, ``[180,240) -> "180-240"``,
  ``[240,300) -> "240-300"``, ``>=300 -> ">300"``.

``overcost`` USD magnitude maps to qualitative labels (PRD US-08 names only — thresholds are
engineering defaults until product pins cutoffs): ``|v|==0 -> none``, ``(0,5k) small``,
``[5k,25k) medium``, ``>=25k large``.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)


def reduce_scores_by_category(scores_by_category: list[Any]) -> list[dict[str, Any]]:
    """Keep category letter + numeric score only (PRD US-07)."""

    out: list[dict[str, Any]] = []
    for row in scores_by_category or []:
        if not isinstance(row, dict):
            continue
        cat = row.get("category")
        score = row.get("score")
        if cat is None or score is None:
            continue
        out.append({"category": cat, "score": score})
    return out


def _to_decimal(val: Any) -> Decimal | None:
    if val is None:
        return None
    if isinstance(val, Decimal):
        return val
    try:
        return Decimal(str(val))
    except Exception:
        logger.warning("anonymization_decimal_parse_failed", extra={"value_type": type(val).__name__})
        return None


def _to_int(val: Any) -> int | None:
    if val is None:
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _bucket_price_cash_usd(amount: Decimal) -> str:
    # Boundaries inclusive on lower edge per CS-273 BVA (30000 lands in 30k-60k).
    if amount < Decimal("30000"):
        return "<30k"
    if amount < Decimal("60000"):
        return "30k-60k"
    if amount < Decimal("100000"):
        return "60k-100k"
    if amount < Decimal("150000"):
        return "100k-150k"
    if amount < Decimal("250000"):
        return "150k-250k"
    return ">250k"


def _bucket_down_payment_pct(pct: Decimal) -> str:
    # 5.0 stays in 0-5 (inclusive upper of first band).
    if pct <= Decimal("5"):
        return "0-5"
    if pct <= Decimal("10"):
        return "5-10"
    if pct <= Decimal("15"):
        return "10-15"
    if pct <= Decimal("25"):
        return "15-25"
    if pct <= Decimal("40"):
        return "25-40"
    return ">40"


def _bucket_annual_rate_pct(rate: Decimal) -> str:
    if rate < Decimal("7"):
        return "<7"
    if rate < Decimal("9"):
        return "7-9"
    if rate < Decimal("12"):
        return "9-12"
    if rate < Decimal("15"):
        return "12-15"
    if rate < Decimal("20"):
        return "15-20"
    return ">20"


def _bucket_term_months(months: int) -> str:
    # 119 -> "<120", 120 -> "120-180" per CS-273 BVA.
    if months < 120:
        return "<120"
    if months < 180:
        return "120-180"
    if months < 240:
        return "180-240"
    if months < 300:
        return "240-300"
    return ">300"


def _bucket_overcost_label(vs_benchmark_usd: Decimal) -> str:
    abs_v = abs(vs_benchmark_usd)
    if abs_v == 0:
        return "none"
    if abs_v < Decimal("5000"):
        return "small"
    if abs_v < Decimal("25000"):
        return "medium"
    return "large"


def _scrub_benchmark_rows(rows: Any) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    if not isinstance(rows, (list, tuple)):
        return out
    for row in rows:
        if not isinstance(row, dict):
            continue
        metric = row.get("metric")
        assessment = row.get("assessment")
        if metric is None or assessment is None:
            continue
        out.append({"metric": str(metric), "assessment": str(assessment)})
    return out


def anonymize_economic_summary(raw: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return bucket-only economic payload + ``anonymized: True``, or ``None`` if input absent."""

    if raw is None:
        return None

    fields_extracted = raw.get("fields_extracted") if isinstance(raw.get("fields_extracted"), dict) else {}

    price_cash = _to_decimal(fields_extracted.get("price_cash"))
    down_payment_pct = _to_decimal(fields_extracted.get("down_payment_pct"))
    annual_rate_pct = _to_decimal(fields_extracted.get("annual_rate_pct"))
    term_months = _to_int(fields_extracted.get("term_months"))

    bucketed: dict[str, Any] = {
        "anonymized": True,
        "benchmark_comparisons": _scrub_benchmark_rows(raw.get("benchmark_comparisons")),
    }

    derivation_status = raw.get("derivation_status")
    if derivation_status is not None:
        bucketed["derivation_status"] = str(derivation_status)

    if price_cash is not None:
        bucketed["price_cash_bucket"] = _bucket_price_cash_usd(price_cash)
    if down_payment_pct is not None:
        bucketed["down_payment_pct_bucket"] = _bucket_down_payment_pct(down_payment_pct)
    if annual_rate_pct is not None:
        bucketed["annual_rate_pct_bucket"] = _bucket_annual_rate_pct(annual_rate_pct)
    if term_months is not None:
        bucketed["term_months_bucket"] = _bucket_term_months(term_months)

    overcost = raw.get("overcost") if isinstance(raw.get("overcost"), dict) else None
    if overcost is not None:
        vs = _to_decimal(overcost.get("vs_benchmark_usd"))
        if vs is not None:
            bucketed["overcost_label"] = _bucket_overcost_label(vs)

    return bucketed
