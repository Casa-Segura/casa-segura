"""Canonical disclaimer registry — CS-337.

Single source of truth for the BR-07 "Esto no es asesoría legal" copy
shared across HTML reports, PDFs, SMS, email, and any future surface.
The frontend mirrors this at ``frontend/src/legal/disclaimer.ts`` —
both must move in lockstep when the registry version bumps.

The companion lint at ``scripts/lint_disclaimer_registry.py`` greps
``backend/`` for the canonical literals outside the allowlisted files
and fails CI on drift.
"""

from __future__ import annotations

from dataclasses import dataclass

DISCLAIMER_ID = "cs.disclaimer.short"
DISCLAIMER_REGISTRY_VERSION = "1.0.0"

# Substring lint uses as a coarse forbidden-token check (NFKC). Tightened
# by the literal allow-list below for false-positive scoping.
DISCLAIMER_FORBIDDEN_SUBSTRING = "asesoría legal"

# Short headline — BR-07 canonical wording.
DISCLAIMER_SHORT_ES = "Esto no es asesoría legal"

# Report header sentence: the short disclaimer plus a call to action.
DISCLAIMER_REPORT_HEADER_ES = "Este reporte no es asesoría legal. Antes de firmar, consulta a un abogado."

# Extended footer / extended page copy — long form for HTML/PDF reports.
DISCLAIMER_EXTENDED_FOOTER_ES = (
    "Casa Segura es una herramienta de orientación. No reemplaza asesoría legal "
    "profesional. Antes de firmar cualquier contrato inmobiliario, consulta a un "
    "abogado salvadoreño."
)

# Email body line — combines BR-07 with an actionable nudge.
DISCLAIMER_EMAIL_BODY_ES = (
    "Este informe es orientativo y no sustituye asesoría legal. Revísalo con un " "profesional antes de decidir."
)

# SMS-friendly variant (channel cap ~160 chars).
DISCLAIMER_SMS_SHORTHAND_ES = "No es asesoría legal."

# Consent gate label (e.g. checkbox before report download).
DISCLAIMER_BLANK_GATE_LABEL_ES = (
    "Confirmo que entiendo que esto no es asesoría legal y que Casa Segura no " "sustituye la revisión de un abogado."
)


@dataclass(frozen=True)
class DisclaimerCopy:
    """Versioned bundle of every disclaimer surface."""

    id: str
    version: str
    short: str
    report_header: str
    extended_footer: str
    email_body: str
    sms_shorthand: str
    gate_label: str


def canonical_disclaimers() -> DisclaimerCopy:
    """Return the canonical disclaimer bundle.

    Callers should prefer this over importing the individual constants
    when they need more than one surface (e.g. report renderer building
    header + footer + gate label).
    """

    return DisclaimerCopy(
        id=DISCLAIMER_ID,
        version=DISCLAIMER_REGISTRY_VERSION,
        short=DISCLAIMER_SHORT_ES,
        report_header=DISCLAIMER_REPORT_HEADER_ES,
        extended_footer=DISCLAIMER_EXTENDED_FOOTER_ES,
        email_body=DISCLAIMER_EMAIL_BODY_ES,
        sms_shorthand=DISCLAIMER_SMS_SHORTHAND_ES,
        gate_label=DISCLAIMER_BLANK_GATE_LABEL_ES,
    )


# Canonical literals the CS-337 lint guards. Files outside the allow-list
# in ``scripts/lint_disclaimer_registry.py`` may not embed any of these
# strings verbatim — callers must import from this module instead.
CANONICAL_DISCLAIMER_LITERALS: tuple[str, ...] = (
    DISCLAIMER_SHORT_ES,
    DISCLAIMER_REPORT_HEADER_ES,
    DISCLAIMER_EXTENDED_FOOTER_ES,
    DISCLAIMER_EMAIL_BODY_ES,
    DISCLAIMER_SMS_SHORTHAND_ES,
    DISCLAIMER_BLANK_GATE_LABEL_ES,
)


__all__ = [
    "CANONICAL_DISCLAIMER_LITERALS",
    "DISCLAIMER_BLANK_GATE_LABEL_ES",
    "DISCLAIMER_EMAIL_BODY_ES",
    "DISCLAIMER_EXTENDED_FOOTER_ES",
    "DISCLAIMER_FORBIDDEN_SUBSTRING",
    "DISCLAIMER_ID",
    "DISCLAIMER_REGISTRY_VERSION",
    "DISCLAIMER_REPORT_HEADER_ES",
    "DISCLAIMER_SHORT_ES",
    "DISCLAIMER_SMS_SHORTHAND_ES",
    "DisclaimerCopy",
    "canonical_disclaimers",
]
