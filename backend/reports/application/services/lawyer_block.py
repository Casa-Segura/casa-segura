"""LLM-backed builder for the "Lleva esto a tu abogado" block (CS-207).

Production wires this to OpenRouter; tests inject a stub callable. The
output is parsed into a ``{items: [...]}`` JSON envelope per PRD F6 §8.1
and clamped to 5 items. On any failure the orchestrator falls back to
the deterministic checklist in ``section_builders.build_actions``.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from reports.domain.view_models import FindingsVM

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_ES = (
    "Eres asesor que ayuda a una persona común a preparar una conversación con un abogado "
    "sobre un contrato inmobiliario salvadoreño. Tu tarea es generar 3-5 puntos clave que el "
    "usuario debe llevar a la conversación, con base en los hallazgos del análisis.\n\n"
    "Reglas:\n"
    '1. Lenguaje "tú", claro, sin jerga legal innecesaria.\n'
    "2. Cada punto es una oración o dos máximo.\n"
    "3. Cada punto debe ser una pregunta o un tema, no un consejo legal.\n"
    "4. Si hay findings críticos, prioriza ellos.\n"
    "5. No inventes detalles del contrato. Usa solo lo que se te da.\n\n"
    'Devuelve un JSON con la lista: {"items": ["...", "...", "..."]}'
)


@dataclass(frozen=True)
class LawyerBlockInputs:
    """Snapshot the LLM consumes — no clause content beyond titles/summaries."""

    contract_type: str
    score_total: float
    band: str
    findings_critical_and_red: tuple[str, ...]


LawyerBlockLLM = Callable[[LawyerBlockInputs], str]


def compose_lawyer_block(
    *,
    contract_type: str,
    band: str,
    score_total: float,
    findings_vm: FindingsVM,
    llm: LawyerBlockLLM | None = None,
) -> tuple[list[str], bool]:
    """Return ``(items, fallback_used)``.

    ``llm`` may be None — in that case ``fallback_used=True`` is set and the
    caller substitutes the deterministic checklist.
    """

    if llm is None:
        return [], True

    inputs = LawyerBlockInputs(
        contract_type=contract_type,
        score_total=score_total,
        band=band,
        findings_critical_and_red=tuple(
            f"{f.title} — {f.description[:200]}" for f in findings_vm.primary if f.severity in ("critical", "red")
        ),
    )

    try:
        raw = llm(inputs)
    except Exception as exc:
        logger.warning("reports.lawyer_block.llm_failed", extra={"err": str(exc)})
        return [], True

    items = _parse_items(raw)
    if not items:
        return [], True
    # Sanitize items: strip, drop empties, dedupe preserving order, clamp to 5.
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        clean = item.strip()
        if not clean or clean in seen:
            continue
        seen.add(clean)
        out.append(clean)
        if len(out) >= 5:
            break
    if not out:
        return [], True
    return out, False


def _parse_items(raw: str) -> list[str]:
    if not raw:
        return []
    try:
        payload: Any = json.loads(raw)
    except json.JSONDecodeError:
        return []
    items = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return []
    return [str(item) for item in items if isinstance(item, (str, int, float))]


__all__ = ["SYSTEM_PROMPT_ES", "LawyerBlockInputs", "LawyerBlockLLM", "compose_lawyer_block"]
