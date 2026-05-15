# Entity Relationship Diagram — F7: Multi-Channel Delivery & Link Management

> Generated: 2026-05-15
> Source: `PRD_F7_ENTREGA_MULTICANAL.md` §5

---

## Overview

F7 introduces one new transient table `delivery_request` (7-day TTL) plus an audit view `v_delivery_audit`. It also writes five columns on `contract_analysis`: `delivery_status`, `delivery_channel`, `delivery_target_hash`, `link_expires_at`, `resend_count`. The `delivery_request` table records every attempt and stores the **KMS-encrypted** destination address until delivery succeeds (then cleared) or 24 h passes (cleared by F8 cron).

A single `ContractAnalysis` has 1..N `DeliveryRequest` rows (one per original delivery + up to 3 resends).

---

## Mermaid Diagram

```mermaid
erDiagram
    CONTRACT_ANALYSIS ||--o{ DELIVERY_REQUEST : "1 — N"
    DELIVERY_REQUEST ||--o| DELIVERY_REQUEST : "is_resend → parent_delivery_request_id"

    CONTRACT_ANALYSIS {
        uuid id PK
        text public_short_id UK
        text delivery_status
        text delivery_channel
        text delivery_target_hash
        timestamptz link_expires_at
        int resend_count
        timestamptz anonymized_at
        timestamptz created_at
    }

    DELIVERY_REQUEST {
        uuid id PK
        uuid analysis_id FK
        text channel
        text target_hash
        text target_value_encrypted
        text target_value_encrypted_kms_key_id
        bool is_resend
        uuid parent_delivery_request_id FK_self
        timestamptz requested_at
        timestamptz delivered_at
        int attempt_count
        int max_attempts
        timestamptz next_attempt_not_before
        text status
        text last_error_code
        text last_error_message
        text last_error_classification
        text provider_message_id
        timestamptz expires_at
    }
```

---

## Entity Definitions

### DeliveryRequest

**Purpose:** One attempt to deliver the report via a channel. Transient: 7 days after `requested_at`. `target_value_encrypted` is cleared on success or 24 h.

#### ORM Model (`delivery/infrastructure/django/models.py`)

| Field | Type | Nullable | Default | Constraints / Index | Description |
|---|---|---|---|---|---|
| `id` | UUID | No | `gen_random_uuid()` | PK | — |
| `analysis_id` | UUID | No | — | FK→`contract_analysis(id)` ON DELETE CASCADE, INDEX | Owning analysis |
| `channel` | TEXT | No | — | CHECK `email_pdf|whatsapp_summary|web_link` | Channel |
| `target_hash` | TEXT | YES | — | — | salt+SHA-256 of destination (NULL for `web_link`) |
| `target_value_encrypted` | TEXT | YES | — | — | KMS-encrypted destination; cleared on delivery |
| `target_value_encrypted_kms_key_id` | TEXT | YES | — | — | KMS key id used |
| `is_resend` | BOOL | No | FALSE | — | — |
| `parent_delivery_request_id` | UUID | YES | — | FK self-ref | If resend, links to the first delivery |
| `requested_at` | TIMESTAMPTZ | No | `NOW()` | — | — |
| `delivered_at` | TIMESTAMPTZ | YES | — | — | — |
| `attempt_count` | INT | No | 0 | — | — |
| `max_attempts` | INT | No | 3 | — | — |
| `next_attempt_not_before` | TIMESTAMPTZ | YES | — | INDEX partial `WHERE status='queued'` | Scheduler key |
| `status` | TEXT | No | — | CHECK `queued|sending|delivered|failed|expired`, INDEX | Terminal state |
| `last_error_code` | TEXT | YES | — | — | Provider-specific code |
| `last_error_message` | TEXT | YES | — | — | — |
| `last_error_classification` | TEXT | YES | — | CHECK `transient|permanent` | — |
| `provider_message_id` | TEXT | YES | — | — | SMTP message id or Zavu msg id |
| `expires_at` | TIMESTAMPTZ | No | `NOW() + 7 days` | INDEX | Cleanup |

#### Domain Entity

```python
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
```

### ContractAnalysis columns written by F7

| Field | Type | Description |
|---|---|---|
| `delivery_status` | TEXT | `pending|queued|sent_email|sent_whatsapp|available_link|expired|failed` |
| `delivery_channel` | TEXT | `email_pdf|whatsapp_summary|web_link` |
| `delivery_target_hash` | TEXT | Preserved until anonymization |
| `link_expires_at` | TIMESTAMPTZ | `created_at + TTL` |
| `resend_count` | INT | 0..3 |

---

## Migration Notes

- `delivery_request` declared by F7's migration (its `infrastructure/django/migrations/0001_initial.py`).
- Indices listed above are critical for the retry scheduler (`next_attempt_not_before` partial) and the cleanup cron.
- F7 also declares the audit view `v_delivery_audit` via `RunSQL`.

---

**End of document.**
