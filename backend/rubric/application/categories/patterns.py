"""Pattern catalog for deterministic clause detection (CS-159..CS-163).

The lists are intentionally small and verbatim — every entry traces to
a rubric cue or to the explicit override trigger in RUBRICA_CONTRATO
§2.2. They are *not* an attempt at a full legal-NLP system; they are
the deterministic short-circuit the rubric engine uses when a clause
is clearly present. The LLM-based evaluator is the long path for the
ambiguous cases — but those are out of scope for Phase 4 acceptance
which pins behavior on the patterns below.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class PatternHit:
    pattern: str
    snippet: str
    start: int


_RX_FLAGS = re.IGNORECASE | re.DOTALL | re.UNICODE


def _norm(text: str) -> str:
    return text.replace(" ", " ").strip()


def find_first(text: str, patterns: tuple[str, ...]) -> PatternHit | None:
    """Return the earliest match across ``patterns`` (case-insensitive)."""

    if not text:
        return None
    best: PatternHit | None = None
    for pat in patterns:
        match = re.search(pat, text, _RX_FLAGS)
        if not match:
            continue
        snippet = _norm(text[max(0, match.start() - 40) : min(len(text), match.end() + 120)])
        candidate = PatternHit(pattern=pat, snippet=snippet, start=match.start())
        if best is None or candidate.start < best.start:
            best = candidate
    return best


def any_match(text: str, patterns: tuple[str, ...]) -> bool:
    return find_first(text, patterns) is not None


# ── Category A patterns ─────────────────────────────────────────────────

A1_PUBLIC_DEED = (
    r"escritura\s+p[uú]blica",
    r"otorgad[oa]\s+ante\s+notario",
)
A1_SIMPLE_PRIVATE = (
    r"documento\s+privado\s+sin\s+escritura",
    r"sin\s+escritura\s+p[uú]blica",
)
A3_DISCRETIONARY_PRICE = (
    r"precio\s+(?:que|al)\s+(?:arbitrio|sola\s+discreci[oó]n|libre\s+decisi[oó]n)\s+de",
    r"a\s+criterio\s+del?\s+(?:vendedor|arrendador|empresa|compañ[ií]a)",
    r"seg[uú]n\s+pol[ií]tica\s+(?:de\s+la\s+)?(?:compañ[ií]a|empresa)",
)
A6_PROMISE_WITHOUT_TERM = (
    r"se\s+promete\s+vender\s+(?:el\s+inmueble\s+)?sin\s+plazo",
    r"promesa\s+de\s+venta\s+sin\s+plazo",
    r"sin\s+fecha\s+(?:determinada|definida)\s+(?:para|de)\s+ejecuci[oó]n",
)


# ── Category B patterns ─────────────────────────────────────────────────

B7_LATE_INTEREST_TOTAL_BALANCE = (
    r"inter[eé]s\s+moratorio.*?(?:sobre|calculad[oa]\s+sobre)\s+(?:el\s+)?saldo\s+total",
    r"mora.*sobre\s+(?:el\s+)?saldo\s+total\s+adeudado",
)
B9_UNILATERAL_MODIFICATION = (
    r"(?:el\s+vendedor|el\s+arrendador|la\s+compa[ñn][ií]a).*?podr[aá]\s+modificar\s+(?:el\s+precio|las\s+condiciones)\s+(?:unilateralmente|sin\s+consentimiento)",
    r"modificaci[oó]n\s+unilateral\s+de\s+(?:precio|condiciones)",
)


# ── Category C patterns ─────────────────────────────────────────────────

C5_WARRANTY_WAIVER = (
    r"renuncia\s+(?:expresamente\s+)?al\s+saneamiento\s+por\s+evicci[oó]n",
    r"se\s+exime\s+(?:al\s+vendedor|al\s+arrendador)\s+de\s+la\s+obligaci[oó]n\s+de\s+saneamiento",
)


# ── Category D patterns ─────────────────────────────────────────────────

D2_BIEN_DE_FAMILIA = (
    r"bien\s+de\s+familia",
    r"r[eé]gimen\s+de\s+bien\s+de\s+familia",
    r"\bIVU\b.*adjudicaci[oó]n",
)
D2_TRANSFER_ATTEMPT = (r"transferir|vender|enajenar|ceder|traspasar",)
D3_FSV_DECLARED = (
    r"anotaci[oó]n\s+preventiva\s+(?:del\s+)?FSV",
    r"fondo\s+social\s+para\s+la\s+vivienda.*?anotaci[oó]n",
)
D3_FSV_NO_CONSENT = (r"sin\s+(?:la\s+)?(?:autorizaci[oó]n|consentimiento)\s+(?:del?\s+)?(?:fondo|FSV)",)


# ── Category E patterns ─────────────────────────────────────────────────

E1_RIGHT_WAIVER = (
    r"el\s+(?:comprador|consumidor|arrendatario)\s+renuncia\s+(?:expresamente\s+)?a\s+",
    r"se\s+renuncia\s+(?:expresamente\s+)?a\s+los\s+derechos",
)
E2_WARRANTY_EXEMPTION = (
    r"se\s+exime\s+(?:al\s+vendedor|al\s+arrendador)\s+(?:de\s+toda\s+responsabilidad|de\s+todo\s+saneamiento)",
)
E3_BURDEN_REVERSAL = (
    r"la\s+carga\s+(?:de\s+la\s+)?prueba\s+(?:recae|recaer[aá])\s+sobre\s+el\s+consumidor",
    r"el\s+consumidor\s+deber[aá]\s+probar\s+(?:la|cualquier)\s+(?:falla|incumplimiento)",
)
E4_AUTO_RENEWAL = (
    r"renovaci[oó]n\s+autom[aá]tica\s+(?:sin|salvo\s+aviso)",
    r"se\s+entender[aá]\s+(?:autom[aá]ticamente\s+)?prorrogado",
)
E5_NOTARY_IMPOSED = (
    r"el\s+(?:vendedor|arrendador)\s+designar[aá]\s+(?:al\s+)?notario",
    r"se\s+impone\s+(?:al\s+comprador\s+)?la\s+designaci[oó]n\s+del\s+notario",
)
E6_BLANK_SIGNATURE = (
    r"firma\s+(?:de\s+)?(?:pagar[eé]s?|letras?|documentos?)\s+en\s+blanco",
    r"suscribir\s+(?:pagar[eé]s?|letras?)\s+en\s+blanco",
)
E7_ARBITRATION = (
    r"someter[aá]n?\s+(?:las\s+controversias|toda\s+disputa)\s+a\s+arbitraje",
    r"cl[aá]usula\s+arbitral.*?obligatoria",
)
E8_LIABILITY_LIMITATION = (
    r"se\s+exonera\s+(?:al\s+vendedor|al\s+arrendador)\s+de\s+(?:cualquier|toda)\s+responsabilidad\s+por\s+da[ñn]os",
    r"el\s+(?:vendedor|arrendador)\s+no\s+ser[aá]\s+responsable\s+por\s+da[ñn]os",
)
E9_DISPROPORTIONATE_PENALTY = (
    r"perder[aá]\s+todo\s+lo\s+pagado\s+(?:por|si)\s+(?:incumplir|cualquier\s+incumplimiento)",
    r"penalidad\s+(?:equivalente\s+al\s+)?100\s*%\s+de\s+lo\s+pagado",
)


# ── Category F patterns ─────────────────────────────────────────────────

F1_FOREIGN_LANGUAGE = (
    r"\bin\s+english\b",
    r"this\s+agreement\s+is\s+governed",
)
F3_WITHDRAWAL_RIGHT = (
    r"derecho\s+de\s+retracto.*?ocho?\s+d[ií]as",
    r"derecho\s+a\s+retractarse.*?8\s+d[ií]as",
)
F4_TOTAL_COST_STATED = (
    r"costo\s+total\s+(?:de\s+)?(?:cr[eé]dito|financiamiento)",
    r"precio\s+total\s+a\s+plazos",
)
F5_EAR_STATED = (
    r"tasa\s+(?:anual\s+)?efectiva\s+anual",
    r"\bTAE\b",
    r"\bTEA\b",
)


__all__ = [
    "A1_PUBLIC_DEED",
    "A1_SIMPLE_PRIVATE",
    "A3_DISCRETIONARY_PRICE",
    "A6_PROMISE_WITHOUT_TERM",
    "B7_LATE_INTEREST_TOTAL_BALANCE",
    "B9_UNILATERAL_MODIFICATION",
    "C5_WARRANTY_WAIVER",
    "D2_BIEN_DE_FAMILIA",
    "D2_TRANSFER_ATTEMPT",
    "D3_FSV_DECLARED",
    "D3_FSV_NO_CONSENT",
    "E1_RIGHT_WAIVER",
    "E2_WARRANTY_EXEMPTION",
    "E3_BURDEN_REVERSAL",
    "E4_AUTO_RENEWAL",
    "E5_NOTARY_IMPOSED",
    "E6_BLANK_SIGNATURE",
    "E7_ARBITRATION",
    "E8_LIABILITY_LIMITATION",
    "E9_DISPROPORTIONATE_PENALTY",
    "F1_FOREIGN_LANGUAGE",
    "F3_WITHDRAWAL_RIGHT",
    "F4_TOTAL_COST_STATED",
    "F5_EAR_STATED",
    "PatternHit",
    "any_match",
    "find_first",
]
