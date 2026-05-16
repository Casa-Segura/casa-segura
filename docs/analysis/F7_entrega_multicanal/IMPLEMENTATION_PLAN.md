# Implementation Plan — F7: Multi-Channel Delivery & Link Management

> Generated: 2026-05-15
> Stack: Django 5.2 LTS + DRF + Celery + Redis + Postgres + KMS
> Module: `delivery/`
> Depends on: F6 (report generation), F8 (schema).

---

## Directory Structure

```
delivery/
├── domain/
│   ├── entities.py           # DeliveryRequest, DeliveryStatusView, ProviderResult
│   ├── enums.py              # DeliveryChannel, DeliveryStatus, ErrorClassification
│   ├── exceptions.py
│   └── protocols.py          # ChannelSender, KmsClient
├── application/
│   ├── commands.py           # CreateDeliveryRequest, MarkSending, MarkDelivered, MarkFailed, IncrementResendCount
│   ├── queries.py            # GetDeliveryByShortId, GetQueuedReadyToSend
│   ├── handlers/
│   │   └── delivery_handlers.py
│   └── services/
│       ├── delivery_service.py
│       ├── email_sender.py
│       ├── sms_sender.py
│       └── backoff_calculator.py
└── infrastructure/
    ├── django/
    │   ├── apps.py
    │   ├── models.py         # DeliveryRequestModel
    │   ├── repositories.py
    │   ├── serializers.py
    │   ├── views.py          # PublicLinkView, ResendView, DeliveryStatusView, InternalRetryView
    │   ├── urls.py           # /r/{short_id}, /v1/contracts/{short_id}/resend, etc.
    │   └── migrations/
    │       ├── 0001_initial.py
    │       └── 0002_audit_view.py
    ├── celery/
    │   └── delivery_tasks.py # @shared_task deliver_to_user, retry_delivery, retry_due_deliveries, expire_links
    ├── kms/
    │   ├── aws_kms_client.py
    │   ├── gcp_kms_client.py
    │   └── local_libsodium_kms_client.py
    ├── smtp/
    │   └── smtp_client.py
    └── external/
        └── sms_client.py
```

---

## App Configuration

```python
# delivery/infrastructure/django/apps.py
from django.apps import AppConfig

class DeliveryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "delivery.infrastructure.django"
    label = "delivery"
    verbose_name = "Casa Segura — Multi-Channel Delivery"
```

URL include in `config/urls.py`:

```python
url_patterns_v1 = [
    path("contracts/", include("delivery.infrastructure.django.urls_v1")),  # /v1/contracts/{short_id}/resend, /delivery-status
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("v1/", include(url_patterns_v1)),
    path("r/", include("delivery.infrastructure.django.urls_public")),  # /r/{short_id}
    path("internal/", include("delivery.infrastructure.django.urls_internal")),  # /v1/internal/delivery/retry/{id}
]
```

---

## Domain Entities (Pydantic)

```python
# delivery/domain/entities.py
from datetime import datetime
from uuid import UUID
from typing import Literal
from pydantic import BaseModel, ConfigDict
from delivery.domain.enums import DeliveryChannel, DeliveryStatus


class DeliveryRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID | None = None
    analysis_id: UUID
    channel: DeliveryChannel
    target_hash: str | None = None
    target_value_encrypted: str | None = None
    target_value_encrypted_kms_key_id: str | None = None
    is_resend: bool = False
    parent_delivery_request_id: UUID | None = None
    requested_at: datetime
    delivered_at: datetime | None = None
    attempt_count: int = 0
    max_attempts: int = 3
    next_attempt_not_before: datetime | None = None
    status: DeliveryStatus = DeliveryStatus.QUEUED
    last_error_code: str | None = None
    last_error_message: str | None = None
    last_error_classification: Literal["transient","permanent"] | None = None
    provider_message_id: str | None = None
    expires_at: datetime


class ProviderResult(BaseModel):
    success: bool
    provider_message_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    error_classification: Literal["transient","permanent"] | None = None


class DeliveryStatusView(BaseModel):
    public_short_id: str
    delivery_status: str
    delivery_channel: str
    delivered_at: datetime | None
    link_expires_at: datetime | None
    resend_count: int
    resend_remaining: int
```

## Enumerations

```python
# delivery/domain/enums.py
from django.db import models


class DeliveryChannel(models.TextChoices):
    EMAIL_PDF = "email_pdf"
    SMS_SUMMARY = "sms_summary"
    WEB_LINK = "web_link"


class DeliveryStatus(models.TextChoices):
    QUEUED = "queued"
    SENDING = "sending"
    DELIVERED = "delivered"
    FAILED = "failed"
    EXPIRED = "expired"


class ErrorClassification(models.TextChoices):
    TRANSIENT = "transient"
    PERMANENT = "permanent"
```

## Commands and Queries

```python
# delivery/application/commands.py
from uuid import UUID
from pydantic import BaseModel
from delivery.domain.entities import DeliveryRequest
from delivery.domain.enums import DeliveryStatus


class CreateDeliveryRequest(BaseModel):
    delivery_request: DeliveryRequest


class MarkSending(BaseModel):
    delivery_request_id: UUID


class MarkDelivered(BaseModel):
    delivery_request_id: UUID
    provider_message_id: str
    delivered_at_now: bool = True


class MarkFailed(BaseModel):
    delivery_request_id: UUID
    last_error_code: str
    last_error_message: str | None = None
    last_error_classification: str = "transient"


class ScheduleRetry(BaseModel):
    delivery_request_id: UUID
    next_attempt_not_before: float  # epoch seconds


class IncrementResendCount(BaseModel):
    analysis_id: UUID
```

```python
# delivery/application/queries.py
from shared.domain.entities.cqrs import BaseGetAttributes, BaseFilterAttributes, Query


class GetDeliveryByShortId(BaseGetAttributes, Query):
    short_id: str


class GetQueuedReadyToSend(BaseFilterAttributes, Query):
    pass
```

## Dependencies

| Package | Reason |
|---|---|
| Existing F1/F6 deps | reused |
| `boto3` (optional) | AWS KMS |
| `google-cloud-kms` (optional) | GCP KMS |
| `pynacl` | local libsodium fallback |
| `email-validator` | email format check at submit |
| `dnspython` | MX lookup |

---

## Story: US-01 channel selection (input from F1)

F1 stored `delivery_channel`, `delivery_target_hash`, `link_expires_at`. F1 placed cleartext target in Redis with TTL ≤ 300 s.

## Story: US-02 email send

`EmailSender.send(dr, ctx)`:

```python
class EmailSender:
    def __init__(self, *, smtp: SmtpClient, report_service: ReportService, settings):
        self.smtp = smtp
        self.report_service = report_service
        self.settings = settings

    def send(self, dr: DeliveryRequest, cleartext_target: str, ctx: dict) -> ProviderResult:
        pdf_bytes = self.report_service.generate_pdf(dr.analysis_id)
        subject = f"Tu análisis de contrato — Casa Segura — {ctx['readable_contract_type']}"
        body_html = render_to_string("email/report_delivery.html", ctx)
        try:
            msg_id = self.smtp.send_email(
                from_addr=self.settings.SMTP_FROM,
                from_name=self.settings.SMTP_FROM_NAME,
                to=cleartext_target,
                subject=subject,
                body_html=body_html,
                attachment_pdf=(f"casa_segura_{ctx['public_short_id']}.pdf", pdf_bytes),
                idempotency_key=str(dr.id),
                timeout=self.settings.SMTP_TIMEOUT_SECONDS,
            )
            return ProviderResult(success=True, provider_message_id=msg_id)
        except TransientSmtpError as e:
            return ProviderResult(success=False, error_code=e.code, error_message=str(e), error_classification="transient")
        except PermanentSmtpError as e:
            return ProviderResult(success=False, error_code=e.code, error_message=str(e), error_classification="permanent")
```

### Tests

- [ ] 250 OK + provider_message_id → delivered
- [ ] 4xx invalid address → permanent
- [ ] 5xx timeout → transient
- [ ] PDF generation fails → fallback HTML or fail clean
- [ ] Provider quota exceeded → permanent

## Story: US-03 SMS send

`SmsSender.send(dr, cleartext_phone, ctx)` calls `SmsClient.send_sms(to, body, idempotency_key)`.

### Tests

- [ ] Phone valid + SMS provider → 200 OK → delivered
- [ ] Invalid/unreachable number → permanent
- [ ] Template name unknown → permanent + ops alert
- [ ] SMS provider transient → retry

## Story: US-04 Public link

`PublicLinkView` looks up by short_id, checks expiration, calls `ReportService.generate_html`. Adds proper headers. The link does **not** require user identification.

## Story: US-05 Resend

`ResendView` constant-time-compares submitted hash; creates new DeliveryRequest; updates resend_count atomically.

```python
# delivery/infrastructure/django/views.py
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
import hmac, hashlib, os
from shared.infrastructure.django.permissions import IsCapabilityHolder

class ResendView(APIView):
    permission_classes = []  # capability is the destination match

    delivery_service = DeliveryService(...)
    analysis_repository = ContractAnalysisRepository()

    def post(self, request, short_id: str):
        target = request.data.get("target")
        if not target:
            return Response({"error": {"code": "INVALID_DELIVERY_TARGET"}}, status=400)
        analysis = self.analysis_repository.get_by_public_short_id(short_id)
        if analysis is None:
            return Response({"error": {"code": "ANALYSIS_NOT_FOUND"}}, status=404)
        if analysis.resend_count >= 3:
            return Response({"error": {"code": "RESEND_LIMIT_EXCEEDED"}}, status=429)
        salt = os.environ["DELIVERY_TARGET_SALT"]
        submitted_hash = hashlib.sha256((salt + target).encode()).hexdigest()
        if not hmac.compare_digest(submitted_hash, analysis.delivery_target_hash):
            return Response({"error": {"code": "TARGET_MISMATCH"}}, status=403)
        with transaction.atomic():
            self.analysis_repository.increment_resend_count(analysis.id)
            dr = self.delivery_service.resend(analysis_id=analysis.id, channel=analysis.delivery_channel, target_cleartext=target)
        return Response({"delivery_request_id": str(dr.id), "channel": dr.channel, "estimated_delivery_seconds": 60}, status=202)
```

## Story: US-06 retry backoff

`BackoffCalculator.next(attempt_count) -> float seconds` returns `base * 2^(attempt_count-1) * jitter(0.8,1.2)` where `base=30s`.

Celery Beat task `delivery.retry_due_deliveries` runs every minute:

```python
@shared_task(name="delivery.retry_due_deliveries")
def retry_due_deliveries() -> dict:
    from delivery.infrastructure.django.repositories import DeliveryRequestRepository
    from delivery.infrastructure.celery.delivery_tasks import retry_delivery
    repo = DeliveryRequestRepository()
    due = repo.list_queued_due()
    for dr_id in due:
        retry_delivery.delay(str(dr_id))
    return {"scheduled": len(due)}
```

## Story: US-07 link expiration

Owned by F8's cron schedule but implemented here:

```python
@shared_task(name="delivery.expire_links")
def expire_links() -> dict:
    from platform.infrastructure.django.models import ContractAnalysisModel
    from django.utils import timezone
    count = ContractAnalysisModel.objects.filter(
        link_expires_at__lt=timezone.now(),
    ).exclude(delivery_status__in=["expired", "failed"]).update(delivery_status="expired")
    return {"marked_expired": count}
```

## Story: US-08 erase encrypted destination

Inline on success + F8's safety-net cron (`delivery.cleanup_delivery_targets`):

```python
@shared_task(name="delivery.cleanup_delivery_targets")
def cleanup_delivery_targets() -> dict:
    from delivery.infrastructure.django.models import DeliveryRequestModel
    from django.utils import timezone
    from datetime import timedelta
    count1 = DeliveryRequestModel.objects.filter(
        status="delivered",
        target_value_encrypted__isnull=False,
        delivered_at__lt=timezone.now() - timedelta(minutes=5),
    ).update(target_value_encrypted=None, target_value_encrypted_kms_key_id=None)
    count2 = DeliveryRequestModel.objects.filter(
        expires_at__lt=timezone.now(),
        target_value_encrypted__isnull=False,
    ).update(target_value_encrypted=None, target_value_encrypted_kms_key_id=None)
    return {"cleared_after_delivery": count1, "cleared_expired": count2}
```

## Story: US-09 ops notification

Prometheus alert rule:

```yaml
- alert: F7DeliveryFailureRateHighEmail
  expr: rate(f7_delivery_outcome_total{channel="email_pdf",outcome="failed"}[1h]) > 0.05
  for: 5m
- alert: F7DeliveryFailureRateHighSms
  expr: rate(f7_delivery_outcome_total{channel="sms_summary",outcome="failed"}[1h]) > 0.10
  for: 5m
```

---

## Part 2 — Staged Execution Plan

### Stage Overview

| # | Stage | Deliverable |
|---|---|---|
| 1 | Domain entities/enums/exceptions/protocols | Pydantic + TextChoices |
| 2 | Commands/queries | CQRS |
| 3 | Handlers | Plain functions |
| 4 | Service classes | DeliveryService, SmsSender, EmailSender |
| 5 | KMS clients | AWS, GCP, Local libsodium |
| 6 | Django model + migration + audit view | DeliveryRequestModel |
| 7 | Repository | DeliveryRequestRepository + ContractAnalysisRepository augment |
| 8 | Celery tasks + Beat schedules | deliver_to_user, retry_delivery, retry_due_deliveries, expire_links, cleanup_delivery_targets |
| 9 | DRF views + URLs | PublicLinkView, ResendView, DeliveryStatusView, InternalRetryView |
| 10 | Email template | `templates/email/report_delivery.html` |
| 11 | Tests | unit + integration + e2e |
| 12 | Observability | Prometheus metrics + alerts |
| 13 | Documentation | RUNBOOK entries |

### Stage 6 — Django model

```python
# delivery/infrastructure/django/models.py
import uuid
from django.db import models
from delivery.domain.enums import DeliveryChannel, DeliveryStatus, ErrorClassification


class DeliveryRequestModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    analysis_id = models.UUIDField(db_index=True, help_text="ContractAnalysis id.")
    channel = models.CharField(max_length=16, choices=DeliveryChannel.choices, help_text="Channel.")
    target_hash = models.TextField(null=True, blank=True, help_text="salt+SHA-256 of destination.")
    target_value_encrypted = models.TextField(null=True, blank=True, help_text="KMS-encrypted destination; cleared on success.")
    target_value_encrypted_kms_key_id = models.TextField(null=True, blank=True, help_text="KMS key id used.")
    is_resend = models.BooleanField(default=False, help_text="True if this is a user-initiated resend.")
    parent_delivery_request_id = models.UUIDField(null=True, blank=True, help_text="If resend, FK self.")
    requested_at = models.DateTimeField(auto_now_add=True, help_text="Creation time.")
    delivered_at = models.DateTimeField(null=True, blank=True, help_text="Successful delivery time.")
    attempt_count = models.IntegerField(default=0, help_text="Number of send attempts.")
    max_attempts = models.IntegerField(default=3, help_text="Max attempts allowed.")
    next_attempt_not_before = models.DateTimeField(null=True, blank=True, help_text="Earliest time to retry.")
    status = models.CharField(max_length=16, choices=DeliveryStatus.choices, db_index=True, help_text="Lifecycle status.")
    last_error_code = models.CharField(max_length=64, null=True, blank=True, help_text="Last error code.")
    last_error_message = models.TextField(null=True, blank=True, help_text="Last error message.")
    last_error_classification = models.CharField(max_length=16, choices=ErrorClassification.choices, null=True, blank=True, help_text="Classification.")
    provider_message_id = models.TextField(null=True, blank=True, help_text="Provider message id.")
    expires_at = models.DateTimeField(db_index=True, help_text="Cleanup trigger.")

    class Meta:
        db_table = "delivery_request"
        indexes = [
            models.Index(fields=["analysis_id"], name="idx_dr_analysis"),
            models.Index(fields=["status"], name="idx_dr_status"),
            models.Index(fields=["expires_at"], name="idx_dr_expires"),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(channel__in=["sms_summary","email_pdf","web_link"]),
                name="dr_channel_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"DeliveryRequest {self.id} ({self.channel}, {self.status})"
```

Migration 0002 creates the partial index for the scheduler:

```python
operations = [
    migrations.RunSQL(
        "CREATE INDEX idx_dr_next_attempt ON delivery_request(next_attempt_not_before) WHERE status='queued';",
        reverse_sql="DROP INDEX IF EXISTS idx_dr_next_attempt;",
    ),
    migrations.RunSQL(
        """
        CREATE VIEW v_delivery_audit AS
        SELECT dr.id, dr.analysis_id, ca.public_short_id, dr.channel, dr.status, dr.attempt_count,
               dr.is_resend, dr.requested_at, dr.delivered_at,
               EXTRACT(EPOCH FROM (dr.delivered_at - dr.requested_at)) AS delivery_time_seconds,
               dr.last_error_code
        FROM delivery_request dr
        JOIN contract_analysis ca ON dr.analysis_id = ca.id
        ORDER BY dr.requested_at DESC;
        """,
        reverse_sql="DROP VIEW IF EXISTS v_delivery_audit;",
    ),
]
```

### Stage 12 — Metrics

| Metric | Type | Labels | Purpose |
|---|---|---|---|
| `f7_delivery_outcome_total` | Counter | `channel`, `outcome` | Funnel |
| `f7_delivery_latency_seconds` | Histogram | `channel` | P50/P95 |
| `f7_delivery_attempt_count` | Histogram | `channel` | Retry distribution |
| `f7_resend_total` | Counter | `channel` | Resend volume |
| `f7_link_views_total` | Counter | — | Public link traffic |
| `f7_link_expired_marked_total` | Counter | — | Expiration job throughput |
| `f7_target_cleared_total` | Counter | `reason` | KMS hygiene |
| `f7_circuit_breaker_state` | Gauge | `target` (`smtp`, `sms`) | Resilience |

---

## Error Codes

| Code | HTTP | Description |
|---|---|---|
| `ANALYSIS_NOT_FOUND` | 404 | Short id invalid |
| `LINK_EXPIRED` | 410 | Link expired |
| `RESEND_LIMIT_EXCEEDED` | 429 | > 3 resends |
| `TARGET_MISMATCH` | 403 | Destination hash mismatch |
| `INVALID_DELIVERY_TARGET` | 400 | Format invalid |
| `KMS_UNAVAILABLE` | — | Internal; surfaced as 500 |
| `SMTP_TRANSIENT_FAILURE` | — | Internal; triggers retry |
| `SMTP_PERMANENT_FAILURE` | — | Internal; mark failed |
| `SMS_TRANSIENT_FAILURE` | — | Internal; triggers retry |
| `SMS_INVALID_PHONE_NUMBER` | — | Permanent |
| `EXTRACTION_TARGET_GONE` | — | Cleartext target missing from Redis (rare) |

---

## Configuration matrix

| Variable | Default | Purpose |
|---|---|---|
| `LINK_TTL_DAYS` | 30 | Public link TTL |
| `DELIVERY_TARGET_SALT` | — | Required; salt for SHA-256 hashing |
| `KMS_PROVIDER` | `aws` | `aws|gcp|local` |
| `KMS_KEY_ID` | — | Active key id |
| `SMTP_HOST` | — | Required |
| `SMTP_PORT` | 587 | STARTTLS |
| `SMTP_USERNAME` | — | — |
| `SMTP_PASSWORD` | — | Secret |
| `SMTP_FROM` | `reportes@casasegura.sv` | — |
| `SMTP_FROM_NAME` | `Casa Segura` | — |
| `SMTP_REPLY_TO` | `reportes@casasegura.sv` | — |
| `SMTP_TIMEOUT_SECONDS` | 30 | — |
| `SMS_PROVIDER` | `local` | Provider adapter id |
| `SMS_API_BASE_URL` | — | Provider base URL when required |
| `SMS_API_KEY` | — | Provider credential |
| `SMS_FROM` | — | Registered sender or phone number |
| `DELIVERY_MAX_RESENDS` | 3 | — |
| `DELIVERY_BACKOFF_BASE_SECONDS` | 30 | — |
| `DELIVERY_BACKOFF_JITTER_PCT` | 0.20 | — |
| `DELIVERY_RETRY_POLL_SECONDS` | 60 | Celery Beat period |
| `DELIVERY_REQUEST_TTL_DAYS` | 7 | — |

---

**End of document.**
