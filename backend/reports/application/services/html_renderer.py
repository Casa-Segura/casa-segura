"""Public facade ``generate_report_html(analysis_id, options)`` (CS-200).

Validates the analysis state, builds every section view model, picks
``full.html.j2`` or ``anonymized.html.j2``, and returns the rendered
HTML string. The function never persists anything (PRD F6 BR-01).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime

from reports.application.metrics import (
    REPORT_BYTES_HISTOGRAM,
    REPORT_HTML_DURATION,
    REPORT_RENDER_OUTCOMES,
)
from reports.application.services.section_builders import (
    DEFAULT_FINDINGS_COLLAPSE_THRESHOLD,
    build_actions,
    build_categories,
    build_economic,
    build_findings,
    build_footer,
    build_header,
    build_legal_refs,
    build_verdict,
    compute_integrity_hash,
)
from reports.domain.errors import (
    AnalysisFailedError,
    AnalysisNotFoundError,
    AnalysisNotReadyError,
    TemplateNotFoundError,
    VersionMissingError,
)
from reports.domain.view_models import FooterVM, ReportContextVM
from reports.infrastructure.jinja.env import make_env


@dataclass(frozen=True)
class GenerateReportOptions:
    """Options accepted by the facades — kept narrow."""

    template_version: str = "v1"
    findings_collapse_threshold: int = DEFAULT_FINDINGS_COLLAPSE_THRESHOLD
    art_1686_warning_mode: str = "always"  # always | when_red | never
    project_name: str | None = None
    project_aggregate_note: str | None = None
    lawyer_items: tuple[str, ...] | None = None
    lawyer_fallback_used: bool = False


def generate_report_html(analysis, options: GenerateReportOptions | None = None) -> str:
    """Render the full HTML report for a ``ContractAnalysis``-shaped row.

    Accepts a duck-typed object (works with both the Django model and a
    test stub) carrying every column the rubric writes plus
    ``public_short_id``, ``contract_type``, ``economic_summary``,
    ``scores_by_category``, ``criterion_evaluations``, ``findings``,
    ``executive_summary`` (optional), ``rubric_version_id``,
    ``corpus_version_id``, ``benchmark_version_id``, and ``created_at``.
    """

    if analysis is None:
        raise AnalysisNotFoundError("analysis is None")

    options = options or GenerateReportOptions()
    started = time.perf_counter()
    try:
        _guard_analysis_state(analysis)

        rubric_version = _resolve_version_field(analysis, ("rubric_version_id", "rubric_version"))
        corpus_version = _resolve_version_field(analysis, ("corpus_version_id", "corpus_version"))
        benchmark_version = _resolve_version_field(
            analysis,
            ("benchmark_version_id", "benchmark_version"),
            allow_missing=True,
        )

        if rubric_version is None or corpus_version is None:
            raise VersionMissingError("rubric_version / corpus_version absent on ContractAnalysis")

        context = _build_context(
            analysis,
            rubric_version=rubric_version,
            corpus_version=corpus_version,
            benchmark_version=benchmark_version,
            options=options,
        )

        template_name = "anonymized.html.j2" if context.anonymized else "full.html.j2"
        try:
            env = make_env(options.template_version)
            template = env.get_template(template_name)
        except FileNotFoundError as exc:
            raise TemplateNotFoundError(str(exc)) from exc

        html = template.render(ctx=context)

        integrity = compute_integrity_hash(
            analysis_id=str(analysis.id),
            rubric_version=rubric_version,
            corpus_version=corpus_version,
            benchmark_version=benchmark_version or "",
            rendered_html=html,
        )
        updated_footer = FooterVM(
            versions_line_es=context.footer.versions_line_es,
            integrity_hash_short=integrity[:16],
            aggregate_project_note_es=context.footer.aggregate_project_note_es,
            error_report_es=context.footer.error_report_es,
            extended_disclaimer_es=context.footer.extended_disclaimer_es,
        )
        if updated_footer.integrity_hash_short != context.footer.integrity_hash_short:
            new_context = context.model_copy(update={"footer": updated_footer})
            html = template.render(ctx=new_context)
    except Exception:
        REPORT_HTML_DURATION.labels(template_version=options.template_version, outcome="error").observe(
            time.perf_counter() - started
        )
        REPORT_RENDER_OUTCOMES.labels(format="html", outcome="error").inc()
        raise

    REPORT_HTML_DURATION.labels(template_version=options.template_version, outcome="ok").observe(
        time.perf_counter() - started
    )
    REPORT_RENDER_OUTCOMES.labels(format="html", outcome="ok").inc()
    REPORT_BYTES_HISTOGRAM.labels(format="html").observe(len(html))
    return html


def _build_context(
    analysis,
    *,
    rubric_version: str,
    corpus_version: str,
    benchmark_version: str | None,
    options: GenerateReportOptions,
) -> ReportContextVM:
    project_name = options.project_name or _resolve_project_name(analysis)
    header = build_header(analysis, project_name)
    verdict = build_verdict(analysis)
    economic = build_economic(analysis)
    economic = _apply_art_1686_policy(economic, verdict, options.art_1686_warning_mode)
    categories = build_categories(analysis)
    findings = build_findings(analysis, collapse_threshold=options.findings_collapse_threshold)
    legal_refs = build_legal_refs(findings)
    actions = build_actions(
        analysis,
        findings,
        lawyer_items=options.lawyer_items,
        lawyer_fallback_used=options.lawyer_fallback_used,
    )
    footer = build_footer(
        analysis,
        rubric_version=rubric_version,
        corpus_version=corpus_version,
        benchmark_version=benchmark_version,
        aggregate_project_note=options.project_aggregate_note,
    )

    return ReportContextVM(
        analysis_id=str(analysis.id),
        public_short_id=analysis.public_short_id,
        generated_at=datetime.now(UTC),
        header=header,
        verdict=verdict,
        economic=economic,
        categories=categories,
        findings=findings,
        legal_refs=legal_refs,
        actions=actions,
        footer=footer,
        anonymized=bool(getattr(analysis, "anonymized_at", None)),
        anonymized_at=(analysis.anonymized_at.date() if getattr(analysis, "anonymized_at", None) else None),
    )


def _apply_art_1686_policy(economic, verdict, mode: str):
    if not economic.show_art_1686_warning:
        return economic
    if mode == "never":
        return economic.model_copy(update={"show_art_1686_warning": False})
    if mode == "when_red" and verdict.band != "red":
        return economic.model_copy(update={"show_art_1686_warning": False})
    return economic


def _resolve_version_field(analysis, names, *, allow_missing: bool = False):
    for name in names:
        if hasattr(analysis, name):
            value = getattr(analysis, name)
            if value:
                return str(value)
    if allow_missing:
        return None
    return None


def _resolve_project_name(analysis) -> str | None:
    project = getattr(analysis, "project", None)
    if project is None:
        return None
    return getattr(project, "canonical_name", None)


def _guard_analysis_state(analysis) -> None:
    if getattr(analysis, "score_total", None) is None:
        if getattr(analysis, "delivery_status", "") == "failed":
            raise AnalysisFailedError("ContractAnalysis is in failed state")
        raise AnalysisNotReadyError(
            "ContractAnalysis is not finalized (score_total is NULL); rubric pipeline still running"
        )


__all__ = ["GenerateReportOptions", "generate_report_html"]
