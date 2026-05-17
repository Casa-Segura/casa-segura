"""Feedback persistence — CS-336.

Stores a minimal, privacy-preserving error report. PII is hashed before
persistence:

* ``contact_email_hash`` — SHA-256 (no clear email).
* ``ip_hash`` — SHA-256 (for rate-limit + dedupe, not for re-identification).
* ``description_excerpt`` — capped at ``MAX_DESCRIPTION_CHARS`` so a
  user can't paste contract text into the queue.
"""

from __future__ import annotations

import uuid

from django.db import models

from feedback.domain.enums import FeedbackCategory

MAX_DESCRIPTION_CHARS = 2000


class UserErrorReport(models.Model):
    """One discrepancy / error report submitted by a user."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    public_short_id = models.CharField(
        max_length=24,
        null=True,
        blank=True,
        help_text="Optional analysis ID the report references (CS-YYYY-XXXXXX).",
    )
    category = models.CharField(
        max_length=32,
        choices=[(c.value, c.value) for c in FeedbackCategory],
        help_text="Topic the user is reporting about (CS-336 enum).",
    )
    description_excerpt = models.TextField(
        help_text=f"Free-text description, capped at {MAX_DESCRIPTION_CHARS} chars.",
    )
    contact_email_hash = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text="SHA-256 of the contact email (never stored in clear).",
    )
    ip_hash = models.CharField(
        max_length=64,
        help_text="SHA-256 of the requester IP — used only for rate limits and dedupe.",
    )
    consent_to_contact = models.BooleanField(
        default=False,
        help_text="Whether the user opted in to be contacted back about the report.",
    )
    user_agent_excerpt = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text="Truncated User-Agent header for triage.",
    )
    created_at = models.DateTimeField(auto_now_add=True, help_text="When the report was filed.")

    class Meta:
        db_table = "user_error_report"
        indexes = [
            models.Index(fields=["public_short_id"], name="idx_uer_short_id"),
            models.Index(fields=["category"], name="idx_uer_category"),
            models.Index(fields=["created_at"], name="idx_uer_created"),
            models.Index(fields=["ip_hash"], name="idx_uer_ip_hash"),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(category__in=[c.value for c in FeedbackCategory]),
                name="uer_category_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"UserErrorReport({self.id} {self.category})"


__all__ = ["MAX_DESCRIPTION_CHARS", "UserErrorReport"]
