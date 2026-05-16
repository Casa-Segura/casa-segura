"""Economics-local enums."""

from __future__ import annotations

from django.db import models


class BenchmarkUnit(models.TextChoices):
    """Unit of an EconomicBenchmark value. PRD DDL set is canonical (per CS-028 notes):
    DOMAIN_MODEL §3.8 lists `pct|usd|months|multiplier`, PRD adds `ratio`."""

    PCT = "pct", "Porcentaje"
    USD = "usd", "USD"
    MONTHS = "months", "Meses"
    MULTIPLIER = "multiplier", "Multiplicador"
    RATIO = "ratio", "Ratio"


class BenchmarkAssessment(models.TextChoices):
    """Outcome of a comparison between contract value and benchmark. See DOMAIN_MODEL §5.6."""

    WITHIN_MARKET = "within_market", "Dentro del mercado"
    ABOVE_MARKET = "above_market", "Encima del mercado"
    WELL_ABOVE_MARKET = "well_above_market", "Muy por encima del mercado"
    BELOW_MARKET_FAVORABLE = "below_market_favorable", "Por debajo del mercado (favorable)"
