"""Per-section ``ViewModel`` builders (CS-201..CS-208).

Each builder consumes the persisted ``ContractAnalysis`` columns + the
``Project`` row and emits a typed ``*VM`` ready for Jinja. Keeping the
builders in one module makes the spelling of every Spanish copy line
auditable in one place.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from datetime import datetime
from decimal import Decimal
from typing import Any

from reports.application.services.formatters import (
    PURCHASE_CONTRACT_TYPES,
    band_hex,
    band_icon,
    band_label_es,
    contract_type_label_es,
    long_date_es,
    money_usd_es,
    months_to_years_es,
    multiplier_es,
    percent_es,
)
from reports.domain.view_models import (
    ActionsVM,
    BenchmarkRowVM,
    CategoryBlockVM,
    CriterionRowVM,
    EconomicVM,
    FindingsVM,
    FindingVM,
    FooterVM,
    HeaderVM,
    LegalReferenceVM,
    LegalRefsVM,
    OverrideEntryVM,
    VerdictVM,
)
from rubric.domain.overrides import OVERRIDE_CATALOG

# Match the PRD F6 §3 US-06 default; configurable via env elsewhere.
DEFAULT_FINDINGS_COLLAPSE_THRESHOLD = 25

_GLOBAL_WEIGHT_PCT = {"A": 20, "B": 30, "C": 20, "D": 15, "E": 10, "F": 5}
_CATEGORY_NAMES_ES = {
    "A": "Validez legal y formal",
    "B": "Salud económica",
    "C": "Garantías para el comprador o arrendatario",
    "D": "Riesgos del inmueble",
    "E": "Cláusulas y prácticas abusivas",
    "F": "Transparencia y claridad",
}
_SEVERITY_LABELS_ES = {
    "critical": "Crítico",
    "red": "Rojo",
    "yellow": "Amarillo",
    "green": "Verde",
    "unverifiable": "No verificable",
}
_SEVERITY_ICONS = {
    "critical": "\U0001f534",
    "red": "\U0001f7e0",
    "yellow": "\U0001f7e1",
    "green": "\U0001f7e2",
    "unverifiable": "⊘",
}
_CRITICAL_DISCLAIMER_ES = (
    "Recuerda: este reporte no es asesoría legal. Antes de actuar sobre los hallazgos "
    "críticos, consulta a un abogado salvadoreño."
)


# ── CS-201 ──────────────────────────────────────────────────────────────


def build_header(analysis, project_name: str | None) -> HeaderVM:
    date_value = getattr(analysis, "created_at", None) or datetime.utcnow()
    return HeaderVM(
        public_short_id=analysis.public_short_id,
        analysis_date_long_es=long_date_es(date_value),
        contract_type_label=contract_type_label_es(analysis.contract_type),
        contract_type_reclassified=bool(analysis.contract_type_reclassified),
        reclassification_reason=(analysis.reclassification_reason or None),
        project_canonical_name=project_name,
    )


# ── CS-202 ──────────────────────────────────────────────────────────────


def build_verdict(analysis) -> VerdictVM:
    band_code = analysis.band or "not_analyzable"
    overrides_raw = list(analysis.override_triggered or [])
    override_entries = [
        OverrideEntryVM(code=code, title_es=_override_title_es(code)) for code in sorted(overrides_raw)
    ]
    score = float(analysis.score_total) if analysis.score_total is not None else 0.0
    return VerdictVM(
        score_total=score,
        band=band_code,
        band_label_es=band_label_es(band_code),
        band_icon=band_icon(band_code),
        band_hex=band_hex(band_code),
        executive_summary=getattr(analysis, "executive_summary", "") or _band_summary_fallback(band_code),
        override_active=bool(override_entries),
        overrides=override_entries,
    )


def _override_title_es(code: str) -> str:
    try:
        spec = OVERRIDE_CATALOG[code]  # type: ignore[index]
        return spec.title_es
    except KeyError:
        return code


def _band_summary_fallback(band: str) -> str:
    return {
        "green": "Este contrato luce favorable en general. Aún así, llévalo a tu abogado antes de firmar.",
        "yellow": "Este contrato tiene puntos a negociar antes de firmar. Revísalos con un abogado.",
        "red": "Este contrato te expone a riesgo serio. No firmes sin asesoría legal y exigir cambios.",
        "not_analyzable": "No fue posible analizar el contrato. Reenvía un documento legible.",
    }.get(band, "")


# ── CS-203 ──────────────────────────────────────────────────────────────


def build_economic(analysis) -> EconomicVM:
    summary = analysis.economic_summary
    contract_type = analysis.contract_type
    show_warning = contract_type in PURCHASE_CONTRACT_TYPES

    if not summary:
        return EconomicVM(present=False, show_art_1686_warning=show_warning)

    fields_extracted = summary.get("fields_extracted") or {}
    fields_derived = summary.get("fields_derived") or {}
    comparisons = summary.get("benchmark_comparisons") or []

    rows: list[BenchmarkRowVM] = []
    rows.append(
        BenchmarkRowVM(
            label_es="Precio contado",
            contract_value_es=money_usd_es(fields_extracted.get("price_cash")) or "—",
        )
    )
    rows.append(
        BenchmarkRowVM(
            label_es="Prima",
            contract_value_es=_compose_down_payment(fields_extracted),
        )
    )
    rows.append(
        BenchmarkRowVM(
            label_es="Monto financiado",
            contract_value_es=money_usd_es(fields_extracted.get("financed_amount")) or "—",
        )
    )
    rows.append(
        BenchmarkRowVM(
            label_es="Plazo",
            contract_value_es=months_to_years_es(fields_extracted.get("term_months")) or "—",
        )
    )
    rate_cmp = next((c for c in comparisons if c.get("metric") == "annual_rate"), None)
    rate_row = BenchmarkRowVM(
        label_es="Tasa efectiva anual",
        contract_value_es=percent_es(fields_extracted.get("annual_rate_pct")) or "—",
    )
    if rate_cmp:
        rate_row = rate_row.model_copy(
            update={
                "benchmark_value_es": percent_es(rate_cmp.get("benchmark_value")),
                "delta_es": _delta_pp_es(rate_cmp.get("delta_pct_points")),
                "assessment": rate_cmp.get("assessment") or "neutral",
            }
        )
    rows.append(rate_row)
    rows.append(
        BenchmarkRowVM(
            label_es="Cuota mensual",
            contract_value_es=money_usd_es(fields_extracted.get("monthly_payment")) or "—",
        )
    )
    rows.append(
        BenchmarkRowVM(
            label_es="Costo total a pagar",
            contract_value_es=money_usd_es(fields_derived.get("total_cost_paid")) or "—",
        )
    )
    rows.append(
        BenchmarkRowVM(
            label_es="Costo total / contado",
            contract_value_es=multiplier_es(fields_derived.get("total_cost_vs_cash_multiplier")) or "—",
        )
    )

    overcost = summary.get("overcost") or {}
    headline = _build_overcost_headline_es(overcost)
    changes = list(overcost.get("what_changes_would_save") or [])

    return EconomicVM(
        present=True,
        rows=rows,
        overcost_headline_es=headline,
        what_changes_would_save_es=[str(item) for item in changes][:5],
        show_art_1686_warning=show_warning,
    )


def _compose_down_payment(fields_extracted: dict[str, Any]) -> str:
    amount = money_usd_es(fields_extracted.get("down_payment"))
    pct = percent_es(fields_extracted.get("down_payment_pct"))
    if amount and pct:
        return f"{amount} ({pct})"
    return amount or pct or "—"


def _delta_pp_es(value: Any) -> str | None:
    if value is None:
        return None
    delta = Decimal(str(value))
    sign = "+" if delta > 0 else ""
    return f"{sign}{delta} puntos vs. mercado"


def _build_overcost_headline_es(overcost: dict[str, Any]) -> str | None:
    usd = overcost.get("overcost_vs_benchmark_usd")
    if usd is None:
        return None
    return f"Pagas {money_usd_es(usd)} más que en un crédito de mercado."


# ── CS-204 ──────────────────────────────────────────────────────────────


def build_categories(analysis) -> list[CategoryBlockVM]:
    blocks: list[CategoryBlockVM] = []
    category_rows = analysis.scores_by_category or []
    evaluations = analysis.criterion_evaluations or []

    by_category: dict[str, list[dict[str, Any]]] = {}
    for ev in evaluations:
        if not ev.get("applicable", True):
            continue
        by_category.setdefault(ev["category"], []).append(ev)

    for cat in category_rows:
        code = cat["category"]
        criterion_rows = [_build_criterion_row(ev) for ev in by_category.get(code, [])]
        blocks.append(
            CategoryBlockVM(
                code=code,
                name_es=cat.get("category_name") or _CATEGORY_NAMES_ES.get(code, code),
                weight_global_pct=_GLOBAL_WEIGHT_PCT.get(code, 0),
                score=float(cat.get("score", 0.0)),
                bar_pct=float(cat.get("score", 0.0)) * 10.0,
                criterion_rows=criterion_rows,
            )
        )
    return blocks


def _build_criterion_row(ev: dict[str, Any]) -> CriterionRowVM:
    score = float(ev.get("score", 0.0))
    unverifiable = bool(ev.get("unverifiable", False))
    if unverifiable:
        icon = "⊘"
        state = "No verificable"
    elif score >= 8.0:
        icon = "✅"  # ✅
        state = "Cumple"
    elif score >= 5.0:
        icon = "⚠️"  # ⚠️
        state = "Atención"
    else:
        icon = "⛔"  # ⛔
        state = "Problema"
    title = ev.get("criterion_id") or "Criterio"
    return CriterionRowVM(
        criterion_id=ev["criterion_id"],
        title_es=f"Criterio {title}",
        score=score,
        icon=icon,
        state_label_es=state,
        unverifiable=unverifiable,
        justification=ev.get("justification") or "",
    )


# ── CS-205 ──────────────────────────────────────────────────────────────


def build_findings(
    analysis,
    *,
    collapse_threshold: int = DEFAULT_FINDINGS_COLLAPSE_THRESHOLD,
) -> FindingsVM:
    findings = analysis.findings or []
    vms = [_finding_to_vm(f) for f in findings]
    has_critical = any(vm.severity == "critical" for vm in vms)

    if len(vms) > collapse_threshold:
        primary = [vm for vm in vms if vm.severity in ("critical", "red")]
        secondary = [vm for vm in vms if vm.severity in ("yellow", "green", "unverifiable")]
    else:
        primary = vms
        secondary = []

    return FindingsVM(
        primary=primary,
        collapsed_secondary=secondary,
        critical_disclaimer_es=_CRITICAL_DISCLAIMER_ES if has_critical else None,
    )


def _finding_to_vm(finding: dict[str, Any]) -> FindingVM:
    severity = finding.get("severity", "yellow")
    tags = finding.get("tags") or []
    grounding_tag_es: str | None = None
    if "market_based" in tags:
        grounding_tag_es = "Hallazgo basado en práctica de mercado, no en violación legal específica."
    elif "unverifiable_legal" in tags:
        grounding_tag_es = "No pudimos confirmar la base legal específica en nuestro corpus para este hallazgo."
    return FindingVM(
        id=finding["id"],
        severity=severity,
        severity_icon=_SEVERITY_ICONS.get(severity, ""),
        severity_label_es=_SEVERITY_LABELS_ES.get(severity, severity),
        title=finding["title"],
        description=finding["description"],
        evidence_clause_snippet=finding.get("evidence_clause_snippet"),
        legal_basis=[_legal_ref_to_vm(ref) for ref in finding.get("legal_basis") or []],
        recommendation=finding["recommendation"],
        related_criterion_id=finding["related_criterion_id"],
        grounding_tag_es=grounding_tag_es,
    )


def _legal_ref_to_vm(ref: dict[str, Any]) -> LegalReferenceVM:
    return LegalReferenceVM(
        law_id=ref["law_id"],
        law_title=ref.get("law_title") or ref["law_id"].replace("-", " ").title(),
        article=ref["article"],
        anchor=ref["anchor"],
        paraphrased_quote=ref["paraphrased_quote"],
    )


# ── CS-206 ──────────────────────────────────────────────────────────────


def build_legal_refs(findings_vm: FindingsVM) -> LegalRefsVM:
    seen: dict[tuple[str, str], LegalReferenceVM] = {}
    for batch in (findings_vm.primary, findings_vm.collapsed_secondary):
        for finding in batch:
            for ref in finding.legal_basis:
                key = (ref.law_id, ref.anchor)
                if key not in seen:
                    seen[key] = ref
    entries = sorted(seen.values(), key=lambda r: (r.law_id, r.anchor))
    return LegalRefsVM(entries=entries)


# ── CS-207 ──────────────────────────────────────────────────────────────


def build_actions(
    analysis,
    findings_vm: FindingsVM,
    *,
    lawyer_items: Iterable[str] | None = None,
    lawyer_fallback_used: bool = False,
) -> ActionsVM:
    """Compose the three action blocks (block 2 may carry LLM-generated items).

    ``lawyer_items`` is injected by the caller — the LLM call is performed
    by ``LawyerBlockComposer`` and translated here. When the LLM is
    unavailable, ``lawyer_fallback_used=True`` is set and we substitute a
    deterministic checklist drawn from the critical/red findings.
    """

    seller_items: list[str] = []
    for finding in findings_vm.primary:
        if finding.severity in ("critical", "red"):
            seller_items.append(finding.recommendation)
        if len(seller_items) >= 5:
            break

    documents_items = _build_documents_items(analysis)
    lawyer_items_list = list(lawyer_items or [])
    if not lawyer_items_list:
        lawyer_items_list = _deterministic_lawyer_items(findings_vm)
        lawyer_fallback_used = True
    lawyer_items_list = lawyer_items_list[:5]

    band = analysis.band or "not_analyzable"
    green_substitute = (
        "El contrato luce favorable en general. Igual revisa con tu abogado antes de firmar."
        if band == "green" and not seller_items
        else None
    )

    return ActionsVM(
        seller_items=seller_items[:5],
        lawyer_items=lawyer_items_list,
        documents_items=documents_items[:5],
        green_band_substitute_es=green_substitute,
        lawyer_block_fallback_used=lawyer_fallback_used,
    )


def _deterministic_lawyer_items(findings_vm: FindingsVM) -> list[str]:
    items: list[str] = []
    for finding in findings_vm.primary[:5]:
        items.append(f"Pregúntale al abogado sobre el hallazgo '{finding.title}' y qué riesgo concreto te genera.")
    if not items:
        items.append(
            "Pídele al abogado que confirme que las cláusulas usuales del contrato no contienen riesgos ocultos."
        )
    return items


def _build_documents_items(analysis) -> list[str]:
    documents = [
        "Escritura pública o, en arrendamiento, contrato firmado por las partes con datos completos.",
        "Constancia de matrícula del inmueble (libro, folio, número de inscripción).",
        "Permiso de construcción vigente y nombre del profesional responsable, si aplica.",
        "Carta del Fondo Social para la Vivienda autorizando la operación, si hay anotación FSV.",
        "Comprobantes de pago previo y recibos del vendedor o arrendador.",
    ]
    return documents


# ── CS-208 ──────────────────────────────────────────────────────────────


def build_footer(
    analysis,
    *,
    rubric_version: str,
    corpus_version: str,
    benchmark_version: str | None,
    rendered_html_for_hash: str = "",
    aggregate_project_note: str | None = None,
) -> FooterVM:
    versions_line = (
        f"Generado con rúbrica {rubric_version}, corpus {corpus_version}, "
        f"benchmarks {benchmark_version or 'no aplica'}"
    )
    integrity = compute_integrity_hash(
        analysis_id=str(analysis.id),
        rubric_version=rubric_version,
        corpus_version=corpus_version,
        benchmark_version=benchmark_version or "",
        rendered_html=rendered_html_for_hash,
    )
    return FooterVM(
        versions_line_es=versions_line,
        integrity_hash_short=integrity[:16],
        aggregate_project_note_es=aggregate_project_note,
    )


def compute_integrity_hash(
    *,
    analysis_id: str,
    rubric_version: str,
    corpus_version: str,
    benchmark_version: str,
    rendered_html: str,
) -> str:
    """Deterministic hash of the analysis identity + render content."""

    digest = hashlib.sha256()
    digest.update(analysis_id.encode("utf-8"))
    digest.update(b"|")
    digest.update(rubric_version.encode("utf-8"))
    digest.update(b"|")
    digest.update(corpus_version.encode("utf-8"))
    digest.update(b"|")
    digest.update(benchmark_version.encode("utf-8"))
    digest.update(b"|")
    digest.update(rendered_html.encode("utf-8"))
    return digest.hexdigest()


__all__ = [
    "DEFAULT_FINDINGS_COLLAPSE_THRESHOLD",
    "build_actions",
    "build_categories",
    "build_economic",
    "build_findings",
    "build_footer",
    "build_header",
    "build_legal_refs",
    "build_verdict",
    "compute_integrity_hash",
]
