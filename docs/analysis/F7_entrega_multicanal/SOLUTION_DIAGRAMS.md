# Solution Diagrams — F7: Multi-Channel Delivery & Link Management

> Generated: 2026-05-15

---

## 1. Class Diagram

### 1.1 Domain + Application

```mermaid
classDiagram
    class DeliveryChannel {
        <<TextChoices>>
        EMAIL_PDF
        WHATSAPP_SUMMARY
        WEB_LINK
    }
    class DeliveryStatus {
        <<TextChoices>>
        QUEUED
        SENDING
        DELIVERED
        FAILED
        EXPIRED
    }
    class DeliveryRequest { <<Pydantic>> }
    class CreateDeliveryRequest { <<Command>> +DeliveryRequest dr }
    class MarkSending { <<Command>> +UUID dr_id }
    class MarkDelivered { <<Command>> +UUID dr_id +str provider_message_id }
    class MarkFailed { <<Command>> +UUID dr_id +str last_error_code +str classification }
    class IncrementResendCount { <<Command>> +UUID analysis_id }
    class GetDeliveryByShortId { <<Query>> +str short_id }
    class GetQueuedReadyToSend { <<Query>> }
    class delivery_handlers {
        <<handlers>>
        +create(cmd, repo) DeliveryRequest
        +mark_sending(cmd, repo) None
        +mark_delivered(cmd, repo) None
        +mark_failed(cmd, repo) None
    }
    class DeliveryService {
        -DeliveryRequestRepository repo
        -ContractAnalysisRepository analysis_repo
        -ReportService report_svc
        -EmailSender email_sender
        -WhatsappSender whatsapp_sender
        -KmsClient kms
        +deliver_to_user(analysis_id) None
        +resend(short_id, target) DeliveryRequest
        +serve_link(short_id) HtmlResponse
        +retry_failed(dr_id) None
        -dispatch(dr) None
        -compute_next_backoff(attempt) timedelta
    }
    class EmailSender {
        -SmtpClient smtp
        -ReportService report_svc
        +send(dr, ctx) ProviderResult
    }
    class WhatsappSender {
        -ZavuClient zavu
        -ReportService report_svc
        +send(dr, ctx) ProviderResult
    }
    class WebLinkServer {
        -ReportService report_svc
        -DeliveryRequestRepository repo
        +serve(short_id) HtmlResponse
    }
    class KmsClient {
        +encrypt(plaintext) tuple~ciphertext, key_id~
        +decrypt(ciphertext, key_id) plaintext
    }
    DeliveryRequest ..> DeliveryChannel
    DeliveryRequest ..> DeliveryStatus
    delivery_handlers ..> CreateDeliveryRequest
    delivery_handlers ..> MarkSending
    delivery_handlers ..> MarkDelivered
    delivery_handlers ..> MarkFailed
    DeliveryService *-- EmailSender
    DeliveryService *-- WhatsappSender
    DeliveryService *-- KmsClient
    DeliveryService ..> delivery_handlers
```

### 1.2 Infrastructure

```mermaid
classDiagram
    class DeliveryRequestModel { <<Django Model>> }
    class DeliveryRequestRepository { <<DjangoFullRepository>> }
    class SmtpClient {
        <<httpx wrapper or smtplib>>
        +send_email(from, to, subject, body_html, attachment_pdf) ProviderResult
    }
    class ZavuClient {
        <<reused from F1>>
        +send_template(to, template_name, params) ProviderResult
    }
    class AwsKmsClient { <<KmsClient impl>> }
    class GcpKmsClient { <<KmsClient impl>> }
    class LocalLibsodiumKmsClient { <<KmsClient impl>> }
    class DeliverTask { <<Celery shared_task>> }
    class RetryDeliveryTask { <<Celery shared_task>> }
    class PublicLinkView { <<DRF APIView>> }
    class ResendView { <<DRF APIView>> }
    class DeliveryStatusView { <<DRF APIView>> }
    class InternalRetryView { <<DRF APIView>> }
    DeliveryRequestRepository ..> DeliveryRequestModel
    DeliverTask ..> DeliveryService
    RetryDeliveryTask ..> DeliveryService
    PublicLinkView ..> DeliveryService
    ResendView ..> DeliveryService
    DeliveryStatusView ..> DeliveryRequestRepository
    InternalRetryView ..> DeliveryService
    AwsKmsClient ..|> KmsClient
    GcpKmsClient ..|> KmsClient
    LocalLibsodiumKmsClient ..|> KmsClient
```

---

## 2. Sequence Diagrams

### 2.1 Email delivery (happy path)

```mermaid
sequenceDiagram
    participant T as DeliverTask (Celery chain)
    participant Svc as DeliveryService
    participant AR as ContractAnalysisRepository
    participant DR as DeliveryRequestRepository
    participant KMS as KmsClient
    participant Redis as Redis (target blob)
    participant R as ReportService
    participant SMTP as SmtpClient
    participant Prov as SMTP provider

    T->>Svc: deliver_to_user(analysis_id)
    Svc->>AR: load(analysis_id) → channel=email_pdf, target_hash, link_expires_at, project_id, etc.
    Svc->>Redis: GET target_blob:{analysis_id}
    Redis-->>Svc: cleartext email (TTL ≤ 300s placed by F1)
    Svc->>KMS: encrypt(cleartext)
    KMS-->>Svc: (ciphertext, key_id)
    Svc->>DR: save(DeliveryRequest(status=queued, channel=email_pdf, target_hash, target_value_encrypted=ciphertext, kms_key_id))
    Svc->>DR: update(status=sending)
    Svc->>KMS: decrypt(ciphertext, key_id) → cleartext (in memory only)
    Svc->>R: generate_pdf(analysis_id) returns bytes
    Svc->>SMTP: send_email(from="reportes@casasegura.sv", to=cleartext, subject="Tu análisis ...", body_html=..., attachment=pdf)
    SMTP->>Prov: SMTP transaction
    Prov-->>SMTP: 250 OK + message-id
    SMTP-->>Svc: ProviderResult(success=true, provider_message_id)
    Svc->>DR: update(status=delivered, delivered_at=NOW(), target_value_encrypted=NULL, provider_message_id)
    Svc->>AR: update(delivery_status="sent_email")
    Svc->>Redis: DEL target_blob:{analysis_id}
```

### 2.2 Transient failure → backoff retry

```mermaid
sequenceDiagram
    participant Svc as DeliveryService
    participant SMTP as SmtpClient
    participant DR as DeliveryRequestRepository
    participant Beat as Celery Beat

    Svc->>SMTP: send_email(...)
    SMTP-->>Svc: ProviderResult(success=false, transient, code=504)
    Svc->>Svc: compute_next_backoff(attempt=1) = 30s (±20% jitter)
    Svc->>DR: update(status=queued, attempt_count=1, last_error_*, next_attempt_not_before=NOW()+30s)
    Beat->>DR: every 1 min: SELECT WHERE status=queued AND next_attempt_not_before<=NOW()
    DR-->>Beat: list
    Beat->>Svc: retry_delivery.delay(dr_id) each
    Svc->>SMTP: send_email(...) again
    SMTP-->>Svc: 250 OK
    Svc->>DR: update(status=delivered, ...)
```

### 2.3 WhatsApp delivery

```mermaid
sequenceDiagram
    participant Svc as DeliveryService
    participant Zavu as ZavuClient
    participant Meta as WhatsApp/Meta
    participant R as ReportService
    participant KMS as KmsClient

    Svc->>KMS: decrypt(ciphertext, key_id)
    KMS-->>Svc: phone +503XXX
    Svc->>R: generate_html (for params); also compute short URL
    Svc->>Zavu: send_template(to=phone, template="casa_segura_report_delivery", params=[score, band_label, 3 findings, link_url, expiry])
    Zavu->>Meta: API
    Meta-->>Zavu: 200 OK + provider_message_id
    Zavu-->>Svc: success
    Svc->>Svc: DR.status=delivered; AR.delivery_status="sent_whatsapp"
```

### 2.4 Public link view

```mermaid
sequenceDiagram
    actor U as User
    participant LV as PublicLinkView
    participant AR as ContractAnalysisRepository
    participant R as ReportService

    U->>LV: GET /r/CS-2026-A1B2C3
    LV->>AR: get_by_public_short_id(short_id)
    alt not found
        LV-->>U: 404 (HTML page)
    else expired (link_expires_at <= NOW())
        LV-->>U: 410 (link-expired HTML page)
    else ok
        LV->>R: generate_html(analysis_id)
        R-->>LV: html
        LV-->>U: 200 with X-Robots-Tag, Cache-Control: no-store
    end
```

### 2.5 Resend

```mermaid
sequenceDiagram
    actor U as User
    participant RV as ResendView
    participant AR as ContractAnalysisRepository
    participant Svc as DeliveryService

    U->>RV: POST /v1/contracts/CS-2026-A1B2C3/resend body={target: "u@x.com"}
    RV->>AR: get_by_public_short_id
    AR-->>RV: analysis with delivery_target_hash, channel, resend_count
    RV->>RV: assert resend_count < 3 (else 429)
    RV->>RV: hash submitted target with global salt
    RV->>RV: compare against delivery_target_hash (constant-time)
    alt mismatch
        RV-->>U: 403 TARGET_MISMATCH
    else match
        RV->>Svc: resend(short_id, target="u@x.com")
        Svc->>Svc: create new DeliveryRequest(is_resend=true, parent_delivery_request_id=original, status=queued, target_value_encrypted=KMS(target))
        Svc->>Svc: dispatch immediately
        Svc-->>RV: ok
        RV-->>U: 202 {delivery_request_id, estimated_delivery_seconds, channel}
    end
```

### 2.6 Link expiration

```mermaid
sequenceDiagram
    participant Beat as Celery Beat (F8 cron)
    participant AR as ContractAnalysisRepository
    participant LV as PublicLinkView

    Beat->>AR: UPDATE contract_analysis SET delivery_status='expired' WHERE link_expires_at<NOW() AND delivery_status NOT IN ('expired','failed')
    AR-->>Beat: N rows updated
    Note over LV: subsequent GET /r/{id} returns 410
```

---

## 3. State Diagram (per DeliveryRequest)

```mermaid
stateDiagram-v2
    [*] --> queued
    queued --> sending
    sending --> delivered: provider OK
    sending --> queued: transient err (with next_attempt_not_before)
    sending --> failed: permanent err OR max_attempts
    queued --> expired: 7-day TTL
    sending --> expired: 7-day TTL
    delivered --> [*]
    failed --> [*]
    expired --> [*]
```

---

## 4. Activity Diagram

```mermaid
flowchart TD
    A[F4 chain triggers delivery] --> B{channel}
    B -->|web_link| C[No proactive send; link is already valid]
    B -->|email_pdf| D[Decrypt target]
    B -->|whatsapp_summary| D
    D --> E[Generate report PDF or summary via F6]
    E --> F[Dispatch via provider]
    F --> G{result}
    G -->|success| H[status=delivered; clear ciphertext; update analysis]
    G -->|transient| I{attempt<max}
    I -->|yes| J[Schedule next_attempt_not_before with backoff]
    I -->|no| K[status=failed; ops alert]
    G -->|permanent| K
    C --> Z[End]
    H --> Z
    K --> Z
    J --> L[Beat scheduler retries]
    L --> F
```

---

## 5. Component Diagram

```mermaid
graph TD
    F4Chain[F4 Celery chain]
    Task[DeliverTask]
    Beat[Celery Beat: retry_due_deliveries]
    Svc[DeliveryService]
    AR[ContractAnalysisRepository]
    DR[DeliveryRequestRepository]
    R[F6 ReportService]
    SMTP[SmtpClient]
    Zavu[ZavuClient]
    KMS[KmsClient]
    Provider1[SMTP provider]
    Provider2[Zavu API → Meta WhatsApp]
    Redis[(Redis: target blob 300s)]
    PG[(Postgres)]
    PubLink[PublicLinkView /r/{short_id}]
    Resend[ResendView]
    StatusV[DeliveryStatusView]
    Internal[InternalRetryView]

    F4Chain --> Task --> Svc
    Beat --> Svc
    Svc --> AR --> PG
    Svc --> DR --> PG
    Svc --> R
    Svc --> SMTP --> Provider1
    Svc --> Zavu --> Provider2
    Svc --> KMS
    Svc --> Redis
    PubLink --> Svc
    Resend --> Svc
    StatusV --> DR
    Internal --> Svc
```

---

## 6. Use Case Diagram

```mermaid
graph LR
    User[Anonymous user]
    F4sys[F4 chain]
    Op[Operator]
    User --> UC1((View report via /r/short_id))
    User --> UC2((Request resend))
    User --> UC3((Query delivery status))
    F4sys --> UC4((Deliver report via chosen channel))
    Op --> UC5((Force retry a failed delivery))
```

**End of document.**
