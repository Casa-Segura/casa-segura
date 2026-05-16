"""Rubric-local enums."""

from __future__ import annotations

from django.db import models


class Category(models.TextChoices):
    """Rubric categories A..F. See RUBRICA_CONTRATO and DOMAIN_MODEL §3.7."""

    A = "A", "Legalidad básica"
    B = "B", "Salud económica"
    C = "C", "Estructura del contrato"
    D = "D", "Garantías y saneamiento"
    E = "E", "Cláusulas abusivas y derechos"
    F = "F", "Cumplimiento específico por tipo"
