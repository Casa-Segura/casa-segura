"""Spanish templates — CS-236."""

from __future__ import annotations

from dataclasses import dataclass

from shared.legal import DISCLAIMER_EMAIL_BODY_ES as _BR_DISCLAIMER_ES


READABLE_CONTRACT_TYPE_ES: dict[str, str] = {
    "CVP": "compraventa con financiamiento",
    "CVC": "compraventa al contado",
    "APV": "promesa de compraventa",
    "LEA": "arrendamiento",
    "ARV": "arrendamiento con promesa",
    "ARC": "arrendamiento comercial",
    "IVU": "IVU",
    "FSV": "FSV",
}


@dataclass(frozen=True, slots=True)
class EmailComposeResult:
    subject: str
    text_body: str
    html_body: str
    attachment_filename: str


def compose_delivery_email(
    *,
    public_short_id: str,
    band_label: str | None = None,
    contract_type_code: str | None = None,
) -> EmailComposeResult:
    """Build transactional email fields + attachment name — PDF bytes supplied separately."""
    band = (band_label or "informe").strip()
    type_es = READABLE_CONTRACT_TYPE_ES.get((contract_type_code or "").strip(), "contrato")
    subject = f"Tu análisis de contrato — Casa Segura — {type_es}"
    text_body = (
        f"Hola,\n\n"
        f"Tu análisis ({public_short_id}) está listo. "
        f"Resumen de banda: {band}.\n\n"
        f"{_BR_DISCLAIMER_ES}\n\n"
        f"— Casa Segura\n"
    )
    html_body = (
        f"<p>Hola,</p>"
        f"<p>Tu análisis (<strong>{public_short_id}</strong>) está listo. "
        f"Banda: <strong>{band}</strong>.</p>"
        f"<p>{_BR_DISCLAIMER_ES}</p>"
        f"<p>— Casa Segura</p>"
    )
    filename = f"casa_segura_{public_short_id}.pdf"
    return EmailComposeResult(subject=subject, text_body=text_body, html_body=html_body, attachment_filename=filename)
