"""Send a one-off test email through Zavu (sandbox or live).

Requires ``ZAVUDEV_API_KEY`` or ``ZAVU_API_KEY`` and optional ``ZAVU_SENDER_ID``.

Examples::

    python manage.py zavu_send_test_email --to you@example.com
    python manage.py zavu_send_test_email --to you@example.com \\
        --link https://example.com/report.pdf --link-text \"Descargar informe\"
    python manage.py zavu_send_test_email --to you@example.com \\
        --attach-url https://example.com/report.pdf --attach-filename informe.pdf

URLs in body or attachments must meet Zavu URL verification rules when enforced.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from delivery.infrastructure.external.zavu_messaging import (
    send_zavu_email,
    zavu_email_download_link_html,
)


class Command(BaseCommand):
    help = "Send a single test email via Zavu (for integration smoke tests)."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--to", required=True, help="Recipient email address")
        parser.add_argument(
            "--subject",
            default="Casa Segura — prueba de correo (Zavu)",
            help="Email subject",
        )
        parser.add_argument(
            "--text",
            default="",
            help="Plain-text body (default: built from --link if set, else a short stub)",
        )
        parser.add_argument(
            "--link",
            default="",
            help="HTTPS URL to include as primary download link (text + HTML)",
        )
        parser.add_argument(
            "--link-text",
            default="Descargar informe",
            help="Anchor / label for --link",
        )
        parser.add_argument(
            "--attach-url",
            default="",
            help="Optional: Zavu attachment from URL (public PDF, etc.)",
        )
        parser.add_argument(
            "--attach-filename",
            default="informe.pdf",
            help="Filename for --attach-url attachment",
        )
        parser.add_argument(
            "--reply-to",
            default="",
            help="Optional Reply-To address",
        )

    def handle(self, *args, **opts) -> None:
        to: str = opts["to"]
        subject: str = opts["subject"]
        text: str = opts["text"]
        link: str = opts["link"]
        link_text: str = opts["link_text"]
        attach_url: str = opts["attach_url"]
        attach_filename: str = opts["attach_filename"]
        reply_to: str = opts["reply_to"]

        html_body: str | None = None
        attachments: list[dict] | None = None

        if link:
            html_body = zavu_email_download_link_html(url=link, link_text=link_text)
            if not text.strip():
                text = f"{link_text}: {link}"

        if not text.strip():
            text = "Mensaje de prueba de Casa Segura vía Zavu."

        if attach_url:
            attachments = [
                {
                    "filename": attach_filename,
                    "path": attach_url,
                }
            ]

        try:
            message_id = send_zavu_email(
                to=to,
                subject=subject,
                text=text,
                html_body=html_body,
                reply_to=reply_to or None,
                attachments=attachments,
            )
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        except Exception as exc:
            raise CommandError(f"Zavu API error: {exc}") from exc

        self.stdout.write(self.style.SUCCESS(f"Sent. Zavu message id: {message_id}"))
