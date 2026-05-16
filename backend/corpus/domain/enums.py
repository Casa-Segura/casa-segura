"""Corpus-local enums."""

from __future__ import annotations

from django.db import models


class LegalDocumentStatus(models.TextChoices):
    """Status of a LegalDocument in the corpus. See DOMAIN_MODEL §3.5."""

    IN_FORCE = "in_force", "Vigente"
    REPEALED = "repealed", "Derogada"
    IN_FORCE_WITH_AMENDMENTS = "in_force_with_amendments", "Vigente con reformas"


class SeverityHint(models.TextChoices):
    """Suggested severity if a contract violates a chunk. Used by F4 as a default."""

    CRITICAL = "critical", "Crítica"
    RED = "red", "Roja"
    YELLOW = "yellow", "Amarilla"
