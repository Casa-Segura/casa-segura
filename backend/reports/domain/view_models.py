"""Pydantic view models the Jinja templates consume.

Templates never touch ORM objects or the rubric domain types directly —
the renderer maps ``ContractAnalysis`` + ``Project`` into these
typed view models first. Two benefits:

* Templates stay declarative; they iterate plain dicts/objects.
* The mapping is the single place where Spanish copy, formatting, and
  defaults live (no scattered ``{% if %}`` ladders for missing fields).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

BandLiteral = Literal["green", "yellow", "red", "not_analyzable"]
SeverityLiteral = Literal["critical", "red", "yellow", "green", "unverifiable"]


class HeaderVM(BaseModel):
    """CS-201 — Report header block."""

    model_config = ConfigDict(extra="forbid")

    public_short_id: str
    analysis_date_long_es: str  # "10 de mayo de 2026"
    contract_type_label: str
    contract_type_reclassified: bool = False
    reclassification_reason: str | None = None
    project_canonical_name: str | None = None
    project_name_disclaimer: str = (
        "El nombre del proyecto se extrajo del contrato; no se verificó contra fuente externa."
    )
    invariant_disclaimer: str = "Este reporte no es asesoría legal. Antes de firmar, consulta a un abogado."


class OverrideEntryVM(BaseModel):
    """CS-202 — One row inside the override panel."""

    model_config = ConfigDict(extra="forbid")

    code: str
    title_es: str


class VerdictVM(BaseModel):
    """CS-202 — Verdict block."""

    model_config = ConfigDict(extra="forbid")

    score_total: float
    band: BandLiteral
    band_label_es: str  # "Favorable" / "Negocia antes de firmar" / "Procede con cuidado"
    band_icon: str  # emoji marker
    band_hex: str  # accessible color token
    executive_summary: str
    override_active: bool
    overrides: list[OverrideEntryVM] = Field(default_factory=list)
    override_warning_es: str = (
        "Este contrato contiene cláusulas que la ley salvadoreña declara nulas o "
        "establece como infracciones muy graves. Independientemente del resto del "
        "análisis, no firmes hasta resolver estos puntos."
    )


class BenchmarkRowVM(BaseModel):
    """CS-203 — One numeric row in the economic table."""

    model_config = ConfigDict(extra="forbid")

    label_es: str
    contract_value_es: str  # already-formatted Spanish string ("18,0% anual", "$80,000.00", "20 años")
    benchmark_value_es: str | None = None
    delta_es: str | None = None
    assessment: Literal["within_market", "above_market", "well_above_market", "below_market_favorable", "neutral"] = (
        "neutral"
    )


class EconomicVM(BaseModel):
    """CS-203 — Economic section view model."""

    model_config = ConfigDict(extra="forbid")

    present: bool
    rows: list[BenchmarkRowVM] = Field(default_factory=list)
    overcost_headline_es: str | None = None
    what_changes_would_save_es: list[str] = Field(default_factory=list)
    show_art_1686_warning: bool = False
    art_1686_warning_es: str = (
        "En El Salvador no existe la rescisión por lesión enorme (Art. 1686 CC). Si firmas "
        "este precio, no podrás impugnarlo después por motivo de precio excesivo. Por eso es "
        "importante revisar las cifras antes de firmar."
    )


class CriterionRowVM(BaseModel):
    """CS-204 — One criterion line inside a category block."""

    model_config = ConfigDict(extra="forbid")

    criterion_id: str
    title_es: str
    score: float
    icon: str  # green/yellow/red/gray
    state_label_es: str  # "Cumple" / "Atención" / "Problema" / "No verificable"
    unverifiable: bool
    justification: str


class CategoryBlockVM(BaseModel):
    """CS-204 — One category block."""

    model_config = ConfigDict(extra="forbid")

    code: Literal["A", "B", "C", "D", "E", "F"]
    name_es: str
    weight_global_pct: int  # 20, 30, 20, 15, 10, 5
    score: float
    bar_pct: float  # 0..100 for the progress bar
    criterion_rows: list[CriterionRowVM] = Field(default_factory=list)


class LegalReferenceVM(BaseModel):
    """CS-205 / CS-206 — Legal reference card."""

    model_config = ConfigDict(extra="forbid")

    law_id: str
    law_title: str
    article: str
    anchor: str
    paraphrased_quote: str
    expand_label_es: str = "Ver texto completo del artículo"


class FindingVM(BaseModel):
    """CS-205 — One finding card."""

    model_config = ConfigDict(extra="forbid")

    id: str
    severity: SeverityLiteral
    severity_icon: str
    severity_label_es: str
    title: str
    description: str
    evidence_clause_snippet: str | None = None
    legal_basis: list[LegalReferenceVM] = Field(default_factory=list)
    recommendation: str
    related_criterion_id: str
    grounding_tag_es: str | None = None  # e.g. "Hallazgo basado en práctica de mercado…"


class FindingsVM(BaseModel):
    """CS-205 — Findings section bundle."""

    model_config = ConfigDict(extra="forbid")

    primary: list[FindingVM] = Field(default_factory=list)
    collapsed_secondary: list[FindingVM] = Field(default_factory=list)
    critical_disclaimer_es: str | None = None
    secondary_label_es: str = "Otros puntos de observación"


class LegalRefsVM(BaseModel):
    """CS-206 — Bibliography list."""

    model_config = ConfigDict(extra="forbid")

    entries: list[LegalReferenceVM] = Field(default_factory=list)
    empty_state_es: str = (
        "No hay artículos legales consolidados para este análisis. Consulta a un abogado "
        "para revisar puntos específicos."
    )
    stewardship_note_es: str = (
        "Estas referencias provienen de un corpus curado de leyes salvadoreñas. "
        "Si encuentras un error, repórtalo a errores@casasegura.sv."
    )


class ActionsVM(BaseModel):
    """CS-207 — Suggested actions section."""

    model_config = ConfigDict(extra="forbid")

    seller_items: list[str] = Field(default_factory=list)
    lawyer_items: list[str] = Field(default_factory=list)
    documents_items: list[str] = Field(default_factory=list)
    green_band_substitute_es: str | None = None
    lawyer_block_fallback_used: bool = False


class FooterVM(BaseModel):
    """CS-208 — Footer block."""

    model_config = ConfigDict(extra="forbid")

    versions_line_es: str  # "Generado con rúbrica 1.0.0, corpus 2026-05-10, benchmarks 2026-Q2"
    integrity_hash_short: str  # first 16 chars of SHA-256
    aggregate_project_note_es: str | None = None
    error_report_es: str = "Reporta errores a errores@casasegura.sv mencionando el identificador del análisis."
    extended_disclaimer_es: str = (
        "Casa Segura es una herramienta de orientación. No reemplaza asesoría legal "
        "profesional. Antes de firmar cualquier contrato inmobiliario, consulta a un "
        "abogado salvadoreño."
    )


class ReportContextVM(BaseModel):
    """Top-level context handed to the Jinja shell template."""

    model_config = ConfigDict(extra="forbid")

    analysis_id: str
    public_short_id: str
    generated_at: datetime
    header: HeaderVM
    verdict: VerdictVM
    economic: EconomicVM
    categories: list[CategoryBlockVM]
    findings: FindingsVM
    legal_refs: LegalRefsVM
    actions: ActionsVM
    footer: FooterVM
    anonymized: bool = False
    anonymized_at: date | None = None


__all__ = [
    "ActionsVM",
    "BandLiteral",
    "BenchmarkRowVM",
    "CategoryBlockVM",
    "CriterionRowVM",
    "EconomicVM",
    "FindingVM",
    "FindingsVM",
    "FooterVM",
    "HeaderVM",
    "LegalReferenceVM",
    "LegalRefsVM",
    "OverrideEntryVM",
    "ReportContextVM",
    "SeverityLiteral",
    "VerdictVM",
]
