"""Override catalog (CS-151).

The 11 critical overrides defined by RUBRICA_CONTRATO §2.2 and
PRD_F4_MOTOR_RUBRICA §3 US-02.

Each entry carries:

* ``code`` — the canonical ``OverrideCode`` enum member.
* ``title_es`` — short Spanish label used in report headers (EPIC-07).
* ``legal_anchors`` — anchor slugs the rubric prefers when calling F3's
  ``retrieve_legal_basis(prefer_anchors=...)``.
* ``associated_criterion_ids`` — the criterion codes whose evaluator
  may trigger this override (RUBRICA_CONTRATO §16 appendix).
* ``metric_label`` — stable snake_case label for the Prometheus
  ``f4_override_total`` counter.

The catalog is **frozen**: tests in
``tests/test_rubric_overrides.py`` assert the eleven members match the
spec byte-for-byte. Adding a twelfth override requires editing this
module *and* RUBRICA_CONTRATO §2.2 in lockstep.
"""

from __future__ import annotations

from dataclasses import dataclass

from rubric.domain.band import OverrideCode


@dataclass(frozen=True)
class OverrideSpec:
    """Static metadata for one critical override (CS-151)."""

    code: OverrideCode
    title_es: str
    legal_anchors: tuple[str, ...]
    associated_criterion_ids: tuple[str, ...]
    metric_label: str

    def __post_init__(self) -> None:
        # CS-151 AC: empty display title or empty criterion mapping is forbidden.
        if not self.title_es.strip():
            raise ValueError(f"OverrideSpec[{self.code}] requires a non-empty title_es")
        if not self.associated_criterion_ids:
            raise ValueError(f"OverrideSpec[{self.code}] must map to at least one criterion id")
        if len(self.metric_label) > 64:
            raise ValueError(f"OverrideSpec[{self.code}] metric_label exceeds 64 chars")


OVERRIDE_CATALOG: dict[OverrideCode, OverrideSpec] = {
    OverrideCode.ART_1605_CC: OverrideSpec(
        code=OverrideCode.ART_1605_CC,
        title_es="Venta de inmueble sin escritura pública (Art. 1605 CC)",
        legal_anchors=("art-1605-cc",),
        associated_criterion_ids=("A1",),
        metric_label="art_1605_cc",
    ),
    OverrideCode.ART_1613_CC: OverrideSpec(
        code=OverrideCode.ART_1613_CC,
        title_es="Precio al arbitrio de una de las partes (Art. 1613 CC)",
        legal_anchors=("art-1613-cc",),
        associated_criterion_ids=("A3",),
        metric_label="art_1613_cc",
    ),
    OverrideCode.ART_1644_CC: OverrideSpec(
        code=OverrideCode.ART_1644_CC,
        title_es="Renuncia de mala fe al saneamiento por evicción (Art. 1644 CC)",
        legal_anchors=("art-1644-cc",),
        associated_criterion_ids=("C5",),
        metric_label="art_1644_cc",
    ),
    OverrideCode.ART_1425_CC: OverrideSpec(
        code=OverrideCode.ART_1425_CC,
        title_es="Promesa de venta sin plazo o condición que fije la época (Art. 1425 CC)",
        legal_anchors=("art-1425-cc",),
        associated_criterion_ids=("A6",),
        metric_label="art_1425_cc",
    ),
    OverrideCode.ART_3_IVU_FAMILY_HOMESTEAD: OverrideSpec(
        code=OverrideCode.ART_3_IVU_FAMILY_HOMESTEAD,
        title_es="Intento de transferir inmueble bajo Bien de Familia (Art. 3 Ley IVU)",
        legal_anchors=("art-3-ley-ivu",),
        associated_criterion_ids=("D2",),
        metric_label="art_3_ivu_family_homestead",
    ),
    OverrideCode.ART_5_LPC_NON_WAIVABLE: OverrideSpec(
        code=OverrideCode.ART_5_LPC_NON_WAIVABLE,
        title_es="Renuncia a derechos irrenunciables del consumidor (Art. 5 LPC)",
        legal_anchors=("art-5-lpc", "art-2-ley-inquilinato"),
        associated_criterion_ids=("E1",),
        metric_label="art_5_lpc_non_waivable",
    ),
    OverrideCode.ART_12_LPC: OverrideSpec(
        code=OverrideCode.ART_12_LPC,
        title_es="Interés moratorio sobre saldo total y no sobre capital pendiente (Art. 12 LPC)",
        legal_anchors=("art-12-lpc",),
        associated_criterion_ids=("B7",),
        metric_label="art_12_lpc",
    ),
    OverrideCode.ART_13_LPC: OverrideSpec(
        code=OverrideCode.ART_13_LPC,
        title_es="Modificación unilateral de precio o condiciones (Art. 13 LPC)",
        legal_anchors=("art-13-lpc", "art-17-b-lpc"),
        associated_criterion_ids=("B9",),
        metric_label="art_13_lpc",
    ),
    OverrideCode.ART_18_LPC_BLANK_SIGNATURE: OverrideSpec(
        code=OverrideCode.ART_18_LPC_BLANK_SIGNATURE,
        title_es="Imposición de firma en blanco en pagarés o letras (Art. 18 lit. b LPC)",
        legal_anchors=("art-18-b-lpc",),
        associated_criterion_ids=("E6",),
        metric_label="art_18_lpc_blank_signature",
    ),
    OverrideCode.ART_17H_LPC_ARBITRATION: OverrideSpec(
        code=OverrideCode.ART_17H_LPC_ARBITRATION,
        title_es="Arbitraje impuesto en contrato de adhesión (Art. 17 lit. h LPC)",
        legal_anchors=("art-17-h-lpc", "art-44-g-lpc"),
        associated_criterion_ids=("E7",),
        metric_label="art_17h_lpc_arbitration",
    ),
    OverrideCode.ART_58_FSV: OverrideSpec(
        code=OverrideCode.ART_58_FSV,
        title_es="Anotación preventiva FSV no divulgada al intentar vender (Art. 58 Ley FSV)",
        legal_anchors=("art-58-ley-fsv",),
        associated_criterion_ids=("D3",),
        metric_label="art_58_fsv",
    ),
}

# Sanity invariants — fail at import if the catalog drifts from the enum.
assert set(OVERRIDE_CATALOG.keys()) == set(OverrideCode), (
    "OVERRIDE_CATALOG must list exactly the eleven OverrideCode members; "
    f"missing={set(OverrideCode) - set(OVERRIDE_CATALOG.keys())} "
    f"extra={set(OVERRIDE_CATALOG.keys()) - set(OverrideCode)}"
)
assert len(OVERRIDE_CATALOG) == 11, "RUBRICA_CONTRATO §2.2 defines exactly 11 overrides"


def get_override_spec(code: OverrideCode | str) -> OverrideSpec:
    """Look up the metadata for an override code.

    Accepts the enum or its string value. Raises ``KeyError`` for unknown
    codes — overrides are *hard gates* on the band, not best-effort
    tags, so silent fall-through would mask telemetry.
    """

    if isinstance(code, str):
        code = OverrideCode(code)
    return OVERRIDE_CATALOG[code]


def overrides_for_criterion(criterion_id: str) -> tuple[OverrideCode, ...]:
    """Return the overrides whose ``associated_criterion_ids`` mentions this criterion."""

    return tuple(spec.code for spec in OVERRIDE_CATALOG.values() if criterion_id in spec.associated_criterion_ids)


__all__ = [
    "OVERRIDE_CATALOG",
    "OverrideSpec",
    "get_override_spec",
    "overrides_for_criterion",
]
