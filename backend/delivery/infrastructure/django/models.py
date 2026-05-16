"""Delivery: transient delivery requests (email/WhatsApp/web link).

DOMAIN_MODEL §4.3. Auto-purges after `expires_at` (7d) via the
`platform.cleanup_delivery_targets` (target value only, +5m) and the
parent cleanup job (full row, +7d).

Privacy invariants:
    - `target_value_encrypted` is wiped at `status=delivered` or expiry.
    - `target_hash` survives so that authorized resends can validate
      capability without restoring the plaintext target."""

from __future__ import annotations

import uuid
from datetime import timedelta

from django.db import models
from django.db.models import Q
from django.utils import timezone

from delivery.domain.enums import DeliveryRequestStatus, ErrorClassification
from platform_core.domain.enums import DeliveryChannel


def _delivery_default_expiry() -> timezone.datetime:
    """Default expiry for delivery requests: now + 7 days."""
    return timezone.now() + timedelta(days=7)


class DeliveryRequest(models.Model):
    """User-facing request to deliver a report. Transient (7d TTL) — DOMAIN §4.3."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    analysis = models.ForeignKey(
        "platform_core.ContractAnalysis",
        on_delete=models.CASCADE,
        related_name="delivery_requests",
        help_text="The analysis being delivered",
    )
    channel = models.CharField(
        max_length=24,
        choices=DeliveryChannel.choices,
        help_text="Channel chosen by the user",
    )
    target_hash = models.CharField(
        max_length=128,
        help_text="Salt+SHA-256 hash of email or phone (preserved for resend capability checks)",
    )
    target_value_encrypted = models.TextField(
        null=True,
        blank=True,
        help_text="KMS-encrypted destination. Erased on successful delivery or +24h, whichever first.",
    )
    requested_at = models.DateTimeField(auto_now_add=True, help_text="When the user requested delivery")
    delivered_at = models.DateTimeField(null=True, blank=True, help_text="When delivery succeeded")
    attempt_count = models.PositiveSmallIntegerField(default=0, help_text="Delivery attempts made")
    max_attempts = models.PositiveSmallIntegerField(default=3, help_text="Hard cap on retries")
    next_attempt_not_before = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Backoff gate: next attempt may only happen after this timestamp",
    )
    status = models.CharField(
        max_length=16,
        choices=DeliveryRequestStatus.choices,
        default=DeliveryRequestStatus.QUEUED,
        help_text="Lifecycle status (distinct from ContractAnalysis.delivery_status)",
    )
    last_error = models.TextField(blank=True, default="", help_text="Truncated last error message")
    last_error_classification = models.CharField(
        max_length=16,
        choices=ErrorClassification.choices,
        null=True,
        blank=True,
        help_text="Whether the failure is transient (retry) or permanent",
    )
    expires_at = models.DateTimeField(
        default=_delivery_default_expiry,
        help_text="Cleanup job purges rows past this timestamp (default +7d)",
    )

    class Meta:
        db_table = "delivery_request"
        verbose_name = "Delivery Request"
        verbose_name_plural = "Delivery Requests"
        constraints = [
            models.CheckConstraint(
                check=Q(channel__in=[c.value for c in DeliveryChannel]),
                name="ck_delivery_channel_enum",
            ),
            models.CheckConstraint(
                check=Q(status__in=[s.value for s in DeliveryRequestStatus]),
                name="ck_delivery_status_enum",
            ),
            models.CheckConstraint(
                check=Q(last_error_classification__isnull=True)
                | Q(last_error_classification__in=[c.value for c in ErrorClassification]),
                name="ck_delivery_error_classification_enum",
            ),
        ]
        indexes = [
            models.Index(fields=["analysis"], name="idx_delivery_analysis"),
            models.Index(fields=["status"], name="idx_delivery_status"),
            models.Index(fields=["expires_at"], name="idx_delivery_expires"),
            models.Index(
                fields=["next_attempt_not_before"],
                name="idx_delivery_next_attempt",
                condition=Q(status=DeliveryRequestStatus.QUEUED.value) & Q(next_attempt_not_before__isnull=False),
            ),
        ]

    def __str__(self) -> str:
        return f"DeliveryRequest({self.id}, {self.channel}, {self.status})"
