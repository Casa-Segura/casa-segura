"""Verdict synthesis (CS-165) + output validator (CS-166).

The synthesis service produces the 2-3 sentence executive summary for
the report. Production wires it to OpenRouter via a callable; tests
inject a deterministic stub. Either way the validator
(``validate_synthesis_output``) is the *final* gate: ungrounded legal
citations are stripped and replaced with the band-only fallback so
``Art. <n>`` strings cannot escape into a report unless they trace to
a retrieval anchor allow-list.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass

from rubric.domain.band import Band, OverrideCode, Severity
from rubric.domain.entities import Finding, FullAnalysisResult
from rubric.domain.overrides import OVERRIDE_CATALOG

logger = logging.getLogger(__name__)

MAX_SUMMARY_SENTENCES = 3
MAX_SUMMARY_LENGTH = 450
# Citation tokens that must trace to an allow-list anchor.
_CITATION_RX = re.compile(
    r"""
    (?:
        Art\.\s*\d+                # "Art. 12"
      | Art[íi]culo\s*\d+           # "Artículo 12"
      | Decreto\s+\d+               # "Decreto 776"
      | D\.L\.\s*\d+                # "D.L. 776"
    )
    """,
    flags=re.IGNORECASE | re.VERBOSE | re.UNICODE,
)
_FORBIDDEN_GENERIC_TOKENS = ("Código",)


DEFAULT_FALLBACKS: dict[Band, str] = {
    Band.GREEN: (
        "Este contrato luce favorable en general. Las cifras y cláusulas analizadas están "
        "dentro de lo aceptable. Aún así, llévalo a tu abogado antes de firmar."
    ),
    Band.YELLOW: (
        "Este contrato tiene cifras o cláusulas que necesitan negociación antes de firmar. "
        "Lleva los hallazgos a tu abogado y a la otra parte para corregirlos."
    ),
    Band.RED: (
        "Este contrato te expone a riesgo serio. Hay desviaciones importantes contra ti. "
        "No firmes sin asesoría legal y exigir cambios."
    ),
    Band.NOT_ANALYZABLE: (
        "No fue posible analizar el contrato con la información proporcionada. "
        "Revisa la legibilidad del documento y vuelve a enviarlo."
    ),
}


@dataclass(frozen=True)
class SynthesisInputs:
    """The aggregate handed to the LLM (PRD F4 §8.3)."""

    contract_type: str
    band: Band
    score_total: float
    override_codes: tuple[OverrideCode, ...]
    critical_findings_count: int
    red_findings_count: int
    overcost_vs_benchmark_usd: float | None


@dataclass(frozen=True)
class ValidatorReport:
    """Outcome of ``validate_synthesis_output``."""

    summary: str
    is_fallback: bool
    citations_stripped: tuple[str, ...]
    length_truncated: bool


SynthesisCallable = Callable[[SynthesisInputs], str]


def _strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def _count_sentences(text: str) -> int:
    cleaned = text.strip()
    if not cleaned:
        return 0
    return sum(1 for part in re.split(r"(?<=[.!?])\s+", cleaned) if part.strip())


def _has_ungrounded_citation(
    text: str,
    *,
    allowed_anchors: tuple[str, ...],
) -> tuple[bool, list[str]]:
    """Return ``(found, matches)``. Matches that map to an allowed anchor pass."""

    matches = _CITATION_RX.findall(text)
    if not matches:
        return False, []
    allowed_norm = {_strip_accents(a).lower() for a in allowed_anchors}
    bad: list[str] = []
    for raw in matches:
        norm = _strip_accents(raw).lower().replace("artículo", "art.").replace("articulo", "art.")
        # Compact "art.  12" → "art. 12" and convert to anchor-style slug.
        tokens = norm.replace(".", "").split()
        if not tokens:
            continue
        if "art" in tokens and any(t.isdigit() for t in tokens):
            number = next(t for t in tokens if t.isdigit())
            anchor_guess = f"art-{number}"
            if anchor_guess in allowed_norm or any(anchor_guess in a for a in allowed_norm):
                continue
        bad.append(raw)
    return bool(bad), bad


def validate_synthesis_output(
    raw_summary: str,
    *,
    band: Band,
    allowed_anchors: tuple[str, ...] = (),
) -> ValidatorReport:
    """Apply CS-166 deterministic post-processing to ``raw_summary``.

    Rules:

    * length capped at ``MAX_SUMMARY_SENTENCES`` / ``MAX_SUMMARY_LENGTH``
    * any ``Art. <n>`` / ``Artículo <n>`` / decree token not in
      ``allowed_anchors`` triggers a strip-and-replace; if the result
      becomes empty or still violates, fall back to the band template
    * empty input always falls back

    Returns a ``ValidatorReport`` carrying the final string + a
    diagnostics envelope for telemetry.
    """

    summary = (raw_summary or "").strip()
    fallback = DEFAULT_FALLBACKS[band]

    if not summary:
        return ValidatorReport(summary=fallback, is_fallback=True, citations_stripped=(), length_truncated=False)

    citations_found, bad_matches = _has_ungrounded_citation(summary, allowed_anchors=allowed_anchors)
    if citations_found:
        cleaned = _CITATION_RX.sub("la ley salvadoreña", summary)
        if any(token in cleaned for token in _FORBIDDEN_GENERIC_TOKENS):
            cleaned = re.sub(r"\bCódigo\b", "la ley", cleaned)
        summary = cleaned.strip()
        # Re-check after cleaning.
        citations_again, _ = _has_ungrounded_citation(summary, allowed_anchors=allowed_anchors)
        if citations_again or not summary:
            return ValidatorReport(
                summary=fallback,
                is_fallback=True,
                citations_stripped=tuple(bad_matches),
                length_truncated=False,
            )

    sentences = _count_sentences(summary)
    truncated = False
    if sentences > MAX_SUMMARY_SENTENCES:
        parts = re.split(r"(?<=[.!?])\s+", summary)
        summary = " ".join(parts[:MAX_SUMMARY_SENTENCES]).strip()
        truncated = True
    if len(summary) > MAX_SUMMARY_LENGTH:
        summary = summary[: MAX_SUMMARY_LENGTH - 1].rstrip() + "…"
        truncated = True

    return ValidatorReport(
        summary=summary,
        is_fallback=False,
        citations_stripped=tuple(bad_matches) if citations_found else (),
        length_truncated=truncated,
    )


def synthesize(
    inputs: SynthesisInputs,
    *,
    llm_callable: SynthesisCallable | None = None,
    allowed_anchors: tuple[str, ...] = (),
) -> ValidatorReport:
    """Run the synthesis pipeline: LLM call + validator.

    ``llm_callable`` may be ``None`` to use the deterministic band-band
    fallback directly (this is also what the validator returns when the
    LLM output is unsalvageable).
    """

    if llm_callable is None:
        return ValidatorReport(
            summary=_build_fallback(inputs),
            is_fallback=True,
            citations_stripped=(),
            length_truncated=False,
        )
    try:
        raw = llm_callable(inputs) or ""
    except Exception as exc:
        logger.warning("rubric.synthesis.llm_failed", extra={"err": str(exc)})
        return ValidatorReport(
            summary=_build_fallback(inputs),
            is_fallback=True,
            citations_stripped=(),
            length_truncated=False,
        )
    return validate_synthesis_output(raw, band=inputs.band, allowed_anchors=allowed_anchors)


def _build_fallback(inputs: SynthesisInputs) -> str:
    """Deterministic copy when the LLM is unavailable.

    The override path leads the message with the named criticality so
    the user is not misled by the band-only fallback.
    """

    if inputs.override_codes:
        primary = inputs.override_codes[0]
        title = OVERRIDE_CATALOG[primary].title_es
        return (
            "Este contrato contiene una cláusula que la ley salvadoreña considera nula "
            f"({title}). No firmes hasta corregirla con asesoría legal."
        )
    return DEFAULT_FALLBACKS[inputs.band]


def synthesis_inputs_from_result(
    result: FullAnalysisResult,
    *,
    overcost_vs_benchmark_usd: float | None = None,
) -> SynthesisInputs:
    """Pack the synthesis inputs from a ``FullAnalysisResult`` snapshot."""

    red = _count_severity(result.findings, Severity.RED)
    return SynthesisInputs(
        contract_type=result.scores_by_category[0].category if result.scores_by_category else "",
        band=result.band,
        score_total=result.score_total,
        override_codes=tuple(result.override_triggered),
        critical_findings_count=result.critical_findings_count,
        red_findings_count=red,
        overcost_vs_benchmark_usd=overcost_vs_benchmark_usd,
    )


def _count_severity(findings: list[Finding], severity: Severity) -> int:
    return sum(1 for f in findings if f.severity == severity)


def collect_allowed_anchors(findings: list[Finding]) -> tuple[str, ...]:
    """Return the anchors present in the persisted ``legal_basis``.

    Used by ``validate_synthesis_output`` as the allow-list — citations
    in the summary must trace back to one of these anchors.
    """

    anchors: set[str] = set()
    for f in findings:
        for ref in f.legal_basis:
            anchors.add(ref.anchor)
    return tuple(sorted(anchors))


__all__ = [
    "DEFAULT_FALLBACKS",
    "MAX_SUMMARY_LENGTH",
    "MAX_SUMMARY_SENTENCES",
    "SynthesisCallable",
    "SynthesisInputs",
    "ValidatorReport",
    "collect_allowed_anchors",
    "synthesis_inputs_from_result",
    "synthesize",
    "validate_synthesis_output",
]
