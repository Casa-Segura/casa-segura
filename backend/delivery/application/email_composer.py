"""Spanish templates — CS-236."""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

_BR_DISCLAIMER_ES = (
    "Este informe es orientativo y no sustituye asesoría legal. "
    "Revísalo con un profesional antes de decidir."
)


@dataclass(frozen=True, slots=True)
class EmailComposeResult:
    subject: str
    text_body: str
    html_body: str
    attachment_filename: str


def compose_delivery_email(*, public_short_id: str, band_label: str | None = None) -> EmailComposeResult:
    """Build transactional email fields + attachment name — PDF bytes supplied separately."""
    band = (band_label or "informe").strip()
    subject = f"Casa Segura — tu informe está listo ({public_short_id})"
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
    base = getattr(settings, "CASASEGURA_EMAIL_ATTACHMENT_BASENAME", "informe-casa-segura.pdf")
    filename = f"{base.removesuffix('.pdf')}-{public_short_id}.pdf"
    return EmailComposeResult(subject=subject, text_body=text_body, html_body=html_body, attachment_filename=filename)
