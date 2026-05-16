# Interaction Diagrams — F7: Multi-Channel Delivery

> Generated: 2026-05-15

---

## Component Overview

```mermaid
graph TD
    F4Chain[F4 Celery chain]
    Task[DeliverTask]
    Beat[Celery Beat retry_due]
    Svc[DeliveryService]
    R[F6 ReportService]
    SMTP[SmtpClient]
    Sms[SmsClient]
    KMS[KmsClient]
    Redis[(Redis target blob)]
    PG[(Postgres)]
    Public[/r/short_id PublicLinkView/]
    Resend[ResendView]

    F4Chain --> Task --> Svc --> R
    Svc --> SMTP
    Svc --> Sms
    Svc --> KMS
    Svc --> Redis
    Svc --> PG
    Public --> Svc
    Resend --> Svc
    Beat --> Svc
```

---

## Flow: US-01 User picks channel at upload

(F1 handles capture; persistence into stub analysis. See F1 docs.)

```mermaid
sequenceDiagram
    actor U as User
    participant F1 as F1 IngestionService
    participant KMS as KmsClient
    participant Redis as Redis
    participant AR as ContractAnalysisRepository

    U->>F1: submit + delivery_channel=email_pdf + delivery_target=u@x.com
    F1->>F1: validate email regex, MX lookup
    F1->>KMS: encrypt(u@x.com)
    KMS-->>F1: (ciphertext, key_id) — NOT used by F1; F7 does the encrypt-at-delivery instead
    Note over F1: simpler: F1 places cleartext in Redis (target_blob:{analysis_id} TTL 300s)
    F1->>Redis: SETEX target_blob:{analysis_id} 300 cleartext
    F1->>AR: stub with delivery_target_hash, delivery_channel, link_expires_at = NOW()+30d
```

---

## Flow: US-02 Email delivery

```mermaid
sequenceDiagram
    participant T as DeliverTask
    participant Svc as DeliveryService
    participant Redis as Redis
    participant KMS as KmsClient
    participant DR as DeliveryRequestRepository
    participant R as F6 ReportService
    participant SMTP as SmtpClient
    participant AR as ContractAnalysisRepository

    T->>Svc: deliver_to_user(analysis_id)
    Svc->>Redis: GET target_blob:{analysis_id}
    Redis-->>Svc: cleartext
    Svc->>KMS: encrypt(cleartext)
    KMS-->>Svc: ciphertext, key_id
    Svc->>DR: create(status=queued, ciphertext, ...)
    Svc->>DR: update(status=sending, attempt_count=1)
    Svc->>R: generate_pdf(analysis_id)
    R-->>Svc: bytes
    Svc->>SMTP: send_email(to=cleartext, subject=..., body=..., attachment=pdf)
    SMTP-->>Svc: ProviderResult
    Svc->>DR: update(status=delivered, delivered_at, provider_message_id, target_value_encrypted=NULL)
    Svc->>AR: update(delivery_status="sent_email")
    Svc->>Redis: DEL target_blob:{analysis_id}
```

---

## Flow: US-03 SMS delivery

```mermaid
sequenceDiagram
    participant Svc as DeliveryService
    participant Redis as Redis
    participant KMS as KmsClient
    participant Sms as SmsClient
    participant DR as DeliveryRequestRepository
    participant AR as ContractAnalysisRepository

    Svc->>Redis: GET target_blob:{analysis_id}
    Redis-->>Svc: phone +503XXX
    Svc->>KMS: encrypt(phone)
    KMS-->>Svc: ciphertext
    Svc->>DR: create(status=queued, channel=sms_summary, ciphertext, target_hash)
    Svc->>DR: update(status=sending)
    Svc->>Sms: send_sms(to=phone, body=summary + link)
    Sms-->>Svc: ProviderResult
    Svc->>DR: update(status=delivered, target_value_encrypted=NULL)
    Svc->>AR: update(delivery_status="sent_sms")
```

---

## Flow: US-04 Public web link served

```mermaid
sequenceDiagram
    actor U as User
    participant LV as PublicLinkView
    participant AR as ContractAnalysisRepository
    participant R as F6 ReportService

    U->>LV: GET /r/CS-2026-A1B2C3
    LV->>AR: get_by_public_short_id(short_id)
    alt not found
        LV-->>U: 404 explanatory HTML
    else expired
        LV-->>U: 410 "Este análisis ya no está disponible" HTML
    else ok
        LV->>R: generate_html(analysis_id)
        R-->>LV: html
        LV-->>U: 200 HTML with X-Robots-Tag noindex, Cache-Control: no-store, HSTS
        Note over LV: Optional in-memory micro-cache 5min for same short_id (saves rendering)
    end
```

---

## Flow: US-05 Resend

```mermaid
sequenceDiagram
    actor U as User
    participant RV as ResendView
    participant AR as ContractAnalysisRepository
    participant Svc as DeliveryService

    U->>RV: POST /v1/contracts/CS-2026-A1B2C3/resend body={"target":"u@x.com"}
    RV->>AR: get_by_public_short_id
    AR-->>RV: analysis
    RV->>RV: if resend_count >= 3 → 429
    RV->>RV: compute hash(u@x.com) constant-time
    alt mismatch
        RV-->>U: 403 TARGET_MISMATCH
    else match
        RV->>Svc: resend(short_id, target)
        Svc->>Svc: create new DeliveryRequest(is_resend=true, parent_delivery_request_id=last)
        Svc->>AR: increment resend_count
        Svc->>Svc: dispatch immediately
        Svc-->>RV: ok
        RV-->>U: 202 Accepted
    end
```

---

## Flow: US-06 Retry with exponential backoff

```mermaid
sequenceDiagram
    participant Svc as DeliveryService
    participant SMTP as SmtpClient
    participant DR as DeliveryRequestRepository
    participant Beat as Celery Beat (every 1 min)
    participant Task as RetryDeliveryTask

    Svc->>SMTP: send_email
    SMTP-->>Svc: transient 504
    Svc->>Svc: backoff = 30s × 2^(attempt-1) × jitter(0.8..1.2); attempt=1 → 30s
    Svc->>DR: update(status=queued, attempt_count=1, next_attempt_not_before=NOW()+30s)
    Beat->>DR: SELECT WHERE status=queued AND next_attempt_not_before <= NOW() LIMIT 100
    DR-->>Beat: list of dr_ids
    Beat->>Task: retry_delivery.delay(dr_id) each
    Task->>Svc: retry_failed(dr_id)
    Svc->>SMTP: send_email
    SMTP-->>Svc: 250 OK
    Svc->>DR: update(status=delivered, ...)
```

---

## Flow: US-07 Link expiration cron

```mermaid
sequenceDiagram
    participant Beat as Celery Beat (hourly)
    participant AR as ContractAnalysisRepository
    participant PG as Postgres

    Beat->>AR: expire_links()
    AR->>PG: UPDATE contract_analysis SET delivery_status='expired' WHERE link_expires_at<NOW() AND delivery_status NOT IN ('expired','failed')
    PG-->>AR: N rows
    AR-->>Beat: {marked_expired: N}
```

---

## Flow: US-08 Erase encrypted destination

```mermaid
sequenceDiagram
    participant Svc as DeliveryService
    participant DR as DeliveryRequestRepository
    participant Beat as Celery Beat (every 5 min, F8 safety net)
    participant PG as Postgres

    Svc->>DR: update(status=delivered, target_value_encrypted=NULL)
    Note over Svc,DR: F7 clears immediately on success
    Beat->>PG: UPDATE delivery_request SET target_value_encrypted=NULL, target_value_encrypted_kms_key_id=NULL WHERE status='delivered' AND target_value_encrypted IS NOT NULL AND delivered_at < NOW() - INTERVAL '5 minutes'
    Beat->>PG: UPDATE delivery_request SET target_value_encrypted=NULL ... WHERE expires_at < NOW() AND target_value_encrypted IS NOT NULL
```

---

## Class Diagram

```mermaid
classDiagram
    class DeliveryService
    class EmailSender
    class SmsSender
    class WebLinkServer
    class KmsClient
    class SmtpClient
    class SmsClient
    class DeliveryRequestRepository
    class ContractAnalysisRepository
    class DeliverTask
    class RetryDeliveryTask
    class PublicLinkView
    class ResendView
    class DeliveryStatusView
    class InternalRetryView

    DeliveryService *-- EmailSender
    DeliveryService *-- SmsSender
    DeliveryService *-- KmsClient
    DeliveryService o-- DeliveryRequestRepository
    DeliveryService o-- ContractAnalysisRepository
    EmailSender o-- SmtpClient
    SmsSender o-- SmsClient
    DeliverTask ..> DeliveryService
    RetryDeliveryTask ..> DeliveryService
    PublicLinkView ..> DeliveryService
    ResendView ..> DeliveryService
    DeliveryStatusView ..> DeliveryRequestRepository
    InternalRetryView ..> DeliveryService
```

**End of document.**
