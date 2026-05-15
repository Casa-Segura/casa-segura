# PRD: F7 — Multi-Channel Delivery & Link Management

**Version:** 1.0
**Status:** Approved for development
**Author:** Product Team
**Date:** 2026-05-10
**Depends on:** F6 (Report Generation), F8 (database schema base)
**Blocks:** None (terminal feature of the pipeline)

---

## 1. Problem Statement

The analysis is done and the report can be generated. Now it has to land in the user's hands via one of three channels: email with PDF attachment, WhatsApp message with a short summary plus link to the full report, or public web link with configurable expiration. The three channels have different constraints: email is asynchronous and supports attachments but requires a reliable SMTP provider; WhatsApp has character limits in templates and requires Zavu integration; the web link is synchronous but requires expiration management and ID privacy.

The feature has four challenges. First, the privacy contract: the user's email or phone is stored only as a hash and as a temporary encrypted value until delivery; after successful delivery the original value is discarded. Second, resends: a user who lost the email can request a resend with the short analysis ID, but the system can only resend to the same original destination (no destination change). Third, link TTL: 30 days by default, expires automatically, and after expiration the link shows a specific message explaining the product's retention policy. Fourth, delivery failures must not block the user: if email bounces or WhatsApp fails, exponential retry is attempted, and an alternative channel is offered at the end.

The disclaimer "Esto no es asesoría legal" appears in the email body, in the first WhatsApp message, and in the report itself. It is invariant.

---

## 2. Scope

**In scope:**

- Three delivery channels: email with PDF attachment, WhatsApp with summary + link, public web link with TTL
- Composition and sending of emails via SMTP provider (configurable)
- Composition and sending of WhatsApp messages via Zavu API
- Public web-link service that renders the HTML report on demand by invoking F6
- Link expiration management (configurable TTL, default 30 days)
- Secure hashing of user email/phone for later resends
- Temporary encryption of email/phone while delivery is in progress (discardable on success)
- Retry policy for failures: exponential backoff with a maximum number of attempts
- Authorized on-demand resend: user with the `public_short_id` and the original address can request resend
- Generation of WhatsApp message with a Zavu-approved template
- User notification when delivery permanently fails, with suggestion of alternative channel
- Operational metrics: successful delivery rate, per-channel latency, per-provider failures

**Out of scope:**

- Generating the report content (that is F6)
- Modifying the report after generation (it is static to the analysis)
- Allowing the user to change destination after the original request (limits phishing surface)
- Delivery to multiple simultaneous destinations (one channel, one destination per analysis)
- SMS as a channel (not in MVP)
- Webhooks to the user's system (does not apply to a consumer product)
- Push notifications (no installed app)
- Email read receipts (no open or click tracking)
- User re-subscription to future messages (no persistent relationship)
- Transactional marketing (no promotions sent)

---

## 3. User Stories

### US-01: User chooses channel and destination when uploading the contract

**As a** user uploading a contract,
**I want to** choose how to receive my report (email, WhatsApp, or link),
**So that** I receive it where it is most convenient.

**Acceptance criteria:**

- The upload interface offers the three channels with a brief explanation of each
- If the user chooses email: prompts for email, validates format, does not send until the analysis is ready
- If they choose WhatsApp: prompts for phone in international format, validates (preferably with explicit country code), confirms they will receive the summary there
- If they choose web link: does not prompt for destination; the system delivers the link on the status page
- For WhatsApp, if the user arrived through a WhatsApp conversation, the destination is inferred from the `from_number` that arrived via Zavu
- The system creates a `DeliveryRequest` with `status=queued` when the analysis closes
- The email or phone is encrypted with a KMS key and persisted in `target_value_encrypted`; the salt+SHA-256 hash is also generated and persisted in `target_hash`

**Destination validations:**

- Email: standard regex, reasonable length, existing domain (resolve MX before accepting)
- Phone: E.164 format (`+503XXXXXXXX`), length between 10 and 15 characters
- Destinations with suspicious domains are not allowed (blacklist of known disposable domains)
- Phones with clearly fraudulent prefixes are not allowed (configurable blacklist)

---

### US-02: System delivers the report by email

**As the** system,
**I want to** send an email to the user with the PDF report attached,
**So that** they receive it in their inbox and can save it.

**Acceptance criteria:**

- F7 waits for the F6 signal indicating the report is ready (via internal queue or callback)
- F7 invokes `f6.generate_report_pdf(analysis_id)` and obtains the PDF binary
- F7 composes the email:
  - Sender: `Casa Segura <reportes@casasegura.sv>` (configurable)
  - Subject: `Tu análisis de contrato — Casa Segura — {readable_contract_type}`
  - Body: simple HTML with large score, first finding if applicable, link to HTML report, and disclaimer
  - Attachment: PDF of the report, named `casa_segura_{public_short_id}.pdf`
- F7 sends via the configured provider's SMTP
- The system marks `DeliveryRequest.status='sending'` before sending
- After successful send, marks `status='delivered'` and erases `target_value_encrypted`
- If SMTP fails with a transient error, it retries per BR-04 policy
- If all attempts fail, marks `status='failed'` and emits an operational notification
- If SMTP rejects with a definitive error (invalid address, permanent bounce), it marks `status='failed'` immediately

**Email body (summarized HTML template, kept in Spanish for user delivery):**

```html
<p>Hola,</p>
<p>Aquí está el análisis de tu contrato inmobiliario.</p>

<div style="font-size:48px; color:#EF4444; font-weight:bold;">4.2 / 10 🔴</div>
<p><strong>Procede con cuidado.</strong> Encontramos hallazgos críticos en tu contrato.</p>

<p>El reporte completo está adjunto en PDF, y también puedes verlo en línea:<br>
<a href="https://casasegura.sv/r/CS-2026-A1B2C3">casasegura.sv/r/CS-2026-A1B2C3</a></p>

<p style="background:#FEF3C7; padding:12px; border-left:4px solid #F59E0B;">
⚠️ <strong>Esto no es asesoría legal.</strong> Antes de firmar tu contrato, consulta a un abogado.
</p>

<p>— Casa Segura</p>

<p style="font-size:10px; color:#888;">
ID del análisis: CS-2026-A1B2C3<br>
El enlace web expira el {expiration_date}.<br>
Si crees que este correo fue un error, ignóralo.<br>
Para reportar problemas: errores@casasegura.sv
</p>
```

---

### US-03: System delivers the report by WhatsApp

**As the** system,
**I want to** send a WhatsApp message to the user with summary and link,
**So that** they receive the information quickly without opening email.

**Acceptance criteria:**

- F7 invokes the Zavu client with the destination number and the message template
- The WhatsApp message template must be pre-approved in Zavu (templates require Meta approval for transactional use)
- The message includes:
  - Brief greeting
  - Score with icon per band
  - Up to 3 critical findings summarized in bullets
  - Link to the full report
  - Link expiration date
  - Disclaimer
- The full message does not exceed Zavu limits (typically 4096 characters)
- F7 marks `DeliveryRequest.status='sending'` before sending
- After success, marks `status='delivered'` and erases `target_value_encrypted`
- If Zavu fails, retry policy BR-04
- If Zavu reports that the number does not receive messages (no WhatsApp installed, blocked), marks `failed` and emits operational notification

**WhatsApp message template (delivered in Spanish):**

```
🏠 *Casa Segura — Tu análisis está listo*

Score: *{score}/10* {band_icon} {band_label}

{executive_summary_2_sentences}

{if there are critical findings:}
Hallazgos importantes:
• {finding_1_short_title}
• {finding_2_short_title}
• {finding_3_short_title}

Reporte completo:
{link_url}

⚠️ Esto NO es asesoría legal.
Antes de firmar, consulta a un abogado.

ID: {public_short_id}
El enlace expira el {expiration_date}.
```

**Concrete example:**

```
🏠 *Casa Segura — Tu análisis está listo*

Score: *4.2/10* 🔴 Procede con cuidado

Este contrato te expone a riesgo serio. La tasa está muy por encima del mercado y hay cláusulas que la ley salvadoreña considera nulas.

Hallazgos importantes:
• Tasa de 18% anual, 9 puntos sobre el promedio
• Sin mecanismo de fideicomiso para tu prima
• Cláusula que limita la responsabilidad del vendedor

Reporte completo:
https://casasegura.sv/r/CS-2026-A1B2C3

⚠️ Esto NO es asesoría legal.
Antes de firmar, consulta a un abogado.

ID: CS-2026-A1B2C3
El enlace expira el 9 de junio de 2026.
```

---

### US-04: System serves the public web link with TTL

**As a** user who received a report link,
**I want to** access the full report from my browser,
**So that** I can read it on a large screen and share it if I decide.

**Acceptance criteria:**

- F7 exposes endpoint `GET /r/{public_short_id}` (public, no authentication)
- The endpoint looks up `ContractAnalysis` by `public_short_id`
- If it does not exist, returns HTTP 404 with explanatory page
- If it exists and `link_expires_at > NOW()`: invokes `f6.generate_report_html(analysis_id)` and serves the HTML
- If it exists but `link_expires_at <= NOW()`: returns "link expired" page
- The report HTML includes `X-Robots-Tag: noindex, nofollow` so search engines do not index it
- Cache-Control: `no-store` to prevent intermediate CDNs from persisting the report
- Served via HTTPS only
- If the analysis is anonymized, serves the reduced report version (see F6 US-08)
- Anonymous metrics: visit counter per analysis link (no visitor identification)

**"Link expired" page (in Spanish):**

```
🔒 Este análisis ya no está disponible

Casa Segura no almacena reportes de forma permanente para proteger tu privacidad.

Los enlaces a los reportes expiran 30 días después de generarse.

Si necesitas el análisis nuevamente, sube tu contrato otra vez.

← Volver al inicio
```

---

### US-05: User requests report resend

**As a** user who lost their email or wants to receive the report again,
**I want to** request a resend to the original destination with the short analysis ID,
**So that** I don't have to repeat the upload process.

**Acceptance criteria:**

- F7 exposes endpoint `POST /v1/contracts/{public_short_id}/resend` with body:
  ```json
  {
      "target": "usuario@example.com"
  }
  ```
- The system computes the salt+SHA-256 hash of the submitted `target`
- Compares against `ContractAnalysis.delivery_target_hash`
- If it does not match: HTTP 403 with message "cannot resend to a different address"
- If it matches: creates a new `DeliveryRequest` with `status=queued`, same channel as original, attempts delivery
- The resend uses the `target` the user just submitted (it does not recover the original)
- The resend respects the 3-resend-per-analysis limit to avoid abuse
- If the analysis is anonymized or the link already expired, the resend delivers the reduced version or rejects
- The resend is logged for audit

**Response states:**

- `200 OK`: resend queued, "we will send it shortly"
- `403 Forbidden`: address does not match the original
- `404 Not Found`: analysis does not exist or has been fully anonymized and removed
- `429 Too Many Requests`: you have exceeded the resend limit for this analysis

---

### US-06: System handles delivery failures with exponential backoff

**As the** system,
**I want to** retry failed deliveries with a reasonable policy,
**So that** transient failures do not become permanent.

**Acceptance criteria:**

- Each `DeliveryRequest` has `attempt_count` and `max_attempts` (default 3)
- Retry policy: 30 seconds, 5 minutes, 30 minutes (exponential backoff with jitter)
- If after `max_attempts` delivery still fails, `status='failed'` and operational notification is emitted
- If the error is clearly definitive (invalid address, non-existent domain, blocked WhatsApp number), no retry; it goes straight to `failed`
- Retries are queued with `not_before` timestamp
- Worker processes the queue by priority and `not_before`
- If the system crashes during a retry, the worker restarts and resumes

**Error classification:**

- Transient (retry): timeout, provider 5xx, rate limit
- Permanent (no retry): 4xx with invalid address, non-existent domain, number that rejects WhatsApp

---

### US-07: System manages link expiration

**As the** system,
**I want to** mark links as expired after their configured TTL,
**So that** the report stops being accessible and the privacy promise is fulfilled.

**Acceptance criteria:**

- Each `ContractAnalysis` has `link_expires_at` set when the first `DeliveryRequest` is created: `NOW() + TTL interval`
- Default TTL: 30 days, configurable via env var `LINK_TTL_DAYS`
- Cron job runs every hour marking expired links: `UPDATE contract_analysis SET delivery_status='expired' WHERE link_expires_at < NOW() AND delivery_status != 'expired'`
- After the expired mark, the `/r/{short_id}` endpoint no longer serves the report; it shows the "link expired" page
- The `ContractAnalysis` row is not deleted at expiration; only the delivery state changes
- After 90 days from `created_at`, the analysis is fully anonymized (F8 handles this)

---

### US-08: System erases the destination after successful delivery

**As the** system,
**I want to** erase the original email or phone after successful delivery,
**So that** the "no persistent PII" promise is fulfilled.

**Acceptance criteria:**

- When a `DeliveryRequest` transitions to `status='delivered'`, the system erases `target_value_encrypted` (sets it to NULL)
- `target_hash` remains because it is used to validate future resends
- If the system allows resend and the user requests resend with the correct target, it is encrypted again temporarily during the resend
- If the analysis reaches anonymization (90 days), `target_hash` is also erased
- Erasure of `target_value_encrypted` is immediate post-delivery; it does not wait for the cleanup job
- Structured logs never include `target_value_encrypted` or `target_hash` (except in errors where the hash is logged for correlation, never the value)

---

### US-09: System notifies operator of persistent failures

**As an** operator,
**I want to** be notified when there are persistent delivery failures,
**So that** I can investigate problems with the SMTP provider or Zavu.

**Acceptance criteria:**

- When a `DeliveryRequest` transitions to `status='failed'` after exhausting retries, a Prometheus metric is emitted with the reason
- If the email channel failure rate exceeds 5% in an hour, an alert fires
- If the WhatsApp failure rate exceeds 10% in an hour, an alert fires (higher threshold because WhatsApp has more legitimate failure reasons)
- Alerts include no user-identifying information
- The operator can query `DeliveryRequest` with `status='failed'` for batch analysis

---

## 4. Business Rules

**BR-01:** The user's email or phone is never stored in cleartext on persistent disk. It is encrypted with a KMS key for temporary use until delivery and discarded after success.

**BR-02:** The salt+SHA-256 hash of the destination is preserved for the life of the analysis (until 90-day anonymization) exclusively to authorize resends. The salt is global to the system, not per user.

**BR-03:** Resend is only allowed to the original destination (validated by hash). Destination change is not allowed. This prevents phishing where an attacker with the analysis ID would attempt to redirect the report.

**BR-04:** Retry policy: maximum 3 attempts, with exponential backoff 30s, 5min, 30min, with ±20% jitter to avoid thundering herd.

**BR-05:** The maximum resends per analysis is 3, counting all requests after the original delivery. This prevents public-endpoint abuse.

**BR-06:** The default link TTL is 30 days since the analysis's `created_at` (not since the last delivery). Configurable by env var.

**BR-07:** The public web link does not require authentication because `public_short_id` acts as a capability token. The short ID's entropy must be sufficient that guessing is infeasible (at least 36 bits of entropy).

**BR-08:** The disclaimer "Esto no es asesoría legal" appears in email body, first WhatsApp message, and in the report itself. It is invariant.

**BR-09:** Casa Segura sends no emails or WhatsApp messages other than the transactional report. There is no newsletter, marketing, or reactivation. Each email/message is a direct response to an explicit user action.

**BR-10:** WhatsApp messages use a Zavu pre-approved template. Ad-hoc messages are not allowed.

**BR-11:** The system does not track email open (no pixel tracking), does not track link clicks, and does not install cookies in the HTML report.

**BR-12:** If the user originally chose WhatsApp channel, resends go via WhatsApp. Same for email. Channel change in resend is not allowed.

**BR-13:** Resending the HTML report via link only requires entering the `public_short_id`, no destination validation, because the link itself is the capability. Accessing the valid link is enough.

**BR-14:** The "link expired" page is standard and reveals no information about the analysis (does not show score, type, or project). It only indicates expiration and how to proceed.

**BR-15:** F7 structured logs include `analysis_id`, `delivery_request_id`, `channel`, `status`, `attempt_count`, `error_code`. They never include `target_value_encrypted` or the `target_hash`.

---

## 5. Data Models

### 5.1 DeliveryRequest (defined in F8, used by F7)

```sql
CREATE TABLE delivery_request (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id UUID NOT NULL REFERENCES contract_analysis(id) ON DELETE CASCADE,

    channel TEXT NOT NULL CHECK (channel IN ('email_pdf', 'whatsapp_summary', 'web_link')),
    target_hash TEXT,
    target_value_encrypted TEXT,
    target_value_encrypted_kms_key_id TEXT,

    is_resend BOOLEAN NOT NULL DEFAULT FALSE,
    parent_delivery_request_id UUID REFERENCES delivery_request(id),

    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delivered_at TIMESTAMPTZ,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    next_attempt_not_before TIMESTAMPTZ,

    status TEXT NOT NULL CHECK (status IN ('queued', 'sending', 'delivered', 'failed', 'expired')),
    last_error_code TEXT,
    last_error_message TEXT,
    last_error_classification TEXT CHECK (last_error_classification IN ('transient', 'permanent')),

    provider_message_id TEXT,
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '7 days')
);

CREATE INDEX idx_delivery_request_analysis ON delivery_request(analysis_id);
CREATE INDEX idx_delivery_request_status ON delivery_request(status);
CREATE INDEX idx_delivery_request_next_attempt ON delivery_request(next_attempt_not_before) WHERE status = 'queued';
CREATE INDEX idx_delivery_request_expires ON delivery_request(expires_at);
```

### 5.2 Audit view

```sql
CREATE VIEW v_delivery_audit AS
SELECT
    dr.id,
    dr.analysis_id,
    ca.public_short_id,
    dr.channel,
    dr.status,
    dr.attempt_count,
    dr.is_resend,
    dr.requested_at,
    dr.delivered_at,
    EXTRACT(EPOCH FROM (dr.delivered_at - dr.requested_at)) AS delivery_time_seconds,
    dr.last_error_code
FROM delivery_request dr
JOIN contract_analysis ca ON dr.analysis_id = ca.id
ORDER BY dr.requested_at DESC;
```

### 5.3 Updates to `contract_analysis` written by F7

```sql
-- F7 writes these columns (the table is defined in F8)
-- delivery_status and delivery_channel reference the current delivery

ALTER TABLE contract_analysis ADD COLUMN IF NOT EXISTS delivery_status TEXT DEFAULT 'pending' CHECK (
    delivery_status IN ('pending', 'queued', 'sent_email', 'sent_whatsapp', 'available_link', 'expired', 'failed')
);
ALTER TABLE contract_analysis ADD COLUMN IF NOT EXISTS delivery_channel TEXT CHECK (
    delivery_channel IN ('email_pdf', 'whatsapp_summary', 'web_link')
);
ALTER TABLE contract_analysis ADD COLUMN IF NOT EXISTS delivery_target_hash TEXT;
ALTER TABLE contract_analysis ADD COLUMN IF NOT EXISTS link_expires_at TIMESTAMPTZ;
ALTER TABLE contract_analysis ADD COLUMN IF NOT EXISTS resend_count INTEGER NOT NULL DEFAULT 0;
```

---

## 6. Integration Points

### 6.1 Consumes: F6 (Report Generation)

F7 invokes F6 at two moments:

```python
# For email: generate PDF
pdf_bytes = f6.generate_report_pdf(analysis_id=analysis.id)

# For web link: generate HTML on demand
html_text = f6.generate_report_html(analysis_id=analysis.id)
```

### 6.2 SMTP provider

F7 sends emails via authenticated SMTP.

Configuration:

- `SMTP_HOST` env var
- `SMTP_PORT` env var (587 STARTTLS, 465 SSL)
- `SMTP_USERNAME` env var
- `SMTP_PASSWORD` env var (secret)
- `SMTP_FROM` env var (default `reportes@casasegura.sv`)
- `SMTP_FROM_NAME` env var (default `Casa Segura`)
- `SMTP_REPLY_TO` env var (default same as FROM)
- `SMTP_TIMEOUT_SECONDS` env var (default 30)

Provider recommendation: SendGrid, Amazon SES, or Postmark. Any with good IP reputation.

### 6.3 Zavu (WhatsApp)

F7 sends WhatsApp messages via the Zavu API.

Configuration:

- `ZAVU_API_BASE_URL` env var (default `https://api.zavu.com/v1`)
- `ZAVU_API_KEY` env var (secret)
- `ZAVU_PHONE_NUMBER_ID` env var (WhatsApp Business number ID)
- `ZAVU_TEMPLATE_NAME_REPORT_DELIVERY` env var (approved template name)
- `ZAVU_WEBHOOK_SECRET` env var (to validate incoming webhooks; already configured in F1)

Typical send endpoint:

```http
POST https://api.zavu.com/v1/messages
Authorization: Bearer {ZAVU_API_KEY}
Content-Type: application/json

{
    "to": "+503XXXXXXXX",
    "type": "template",
    "template": {
        "name": "casa_segura_report_delivery",
        "language": "es",
        "components": [
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": "{score}"},
                    {"type": "text", "text": "{band}"}
                ]
            }
        ]
    }
}
```

### 6.4 Encryption system (KMS)

F7 encrypts `target_value` with the configured KMS key.

Configuration:

- `KMS_PROVIDER` env var (default `aws`; alternative `gcp`, `local`)
- `KMS_KEY_ID` env var (key ARN or equivalent)
- Operations: `encrypt`, `decrypt` with the specified key

If `KMS_PROVIDER=local`, libsodium is used with a master key in a protected env var.

### 6.5 Web-link service

F7 exposes the public endpoint `GET /r/{public_short_id}`. Ideally served via an optimized web server (not the main API) with aggressive cache of generated HTML during short TTL (5 minutes) to reduce F6 load.

---

## 7. API Surface

### 7.1 `GET /r/{public_short_id}`

Public endpoint that serves the HTML report.

**Response 200 (active):**

Full HTML of the report. Headers:

```
Content-Type: text/html; charset=utf-8
X-Robots-Tag: noindex, nofollow
Cache-Control: no-store
Strict-Transport-Security: max-age=31536000
```

**Response 404:**

Simple HTML page with "Análisis no encontrado".

**Response 410 (Gone — expired link):**

HTML page with explanation of the retention policy.

### 7.2 `POST /v1/contracts/{public_short_id}/resend`

Request report resend to the original destination.

**Request:**

```json
{
    "target": "usuario@example.com"
}
```

**Response 202 Accepted:**

```json
{
    "delivery_request_id": "uuid",
    "estimated_delivery_seconds": 60,
    "channel": "email_pdf"
}
```

**Response 403 Forbidden:**

```json
{
    "error": {
        "code": "TARGET_MISMATCH",
        "message": "El destino no coincide con el original. Por seguridad, solo podemos reenviar al destino que recibiste el reporte la primera vez."
    }
}
```

**Response 429 Too Many Requests:**

```json
{
    "error": {
        "code": "RESEND_LIMIT_EXCEEDED",
        "message": "Has alcanzado el límite de reenvíos para este análisis."
    }
}
```

### 7.3 `GET /v1/contracts/{public_short_id}/delivery-status`

Query delivery status.

**Response 200:**

```json
{
    "public_short_id": "CS-2026-A1B2C3",
    "delivery_status": "delivered",
    "delivery_channel": "email_pdf",
    "delivered_at": "2026-05-10T14:25:43Z",
    "link_expires_at": "2026-06-09T14:25:43Z",
    "resend_count": 0,
    "resend_remaining": 3
}
```

### 7.4 `POST /v1/internal/delivery/retry/{delivery_request_id}` (requires `X-Internal-Auth`)

Force manual retry of a failed delivery (for operators).

---

## 8. LLM Prompts

F7 does not use an LLM. Message composition uses static templates.

---

## 9. Non-Functional Requirements

- **P50 latency for email send:** under 3 seconds from queue to SMTP accepted by provider.
- **P95 latency:** under 10 seconds.
- **P50 latency for WhatsApp send:** under 2 seconds from queue to Zavu accepted.
- **P50 latency for web link:** under 1 second TTFB on first load.
- **Public endpoint availability:** over 99% (serving the link is critical).
- **Email delivery success rate:** over 95% on first attempt, over 99% after retries.
- **WhatsApp delivery success rate:** over 90% on first attempt (WhatsApp has more legitimate failure reasons).
- **Throughput:** support at least 200 concurrent deliveries in production.
- **In-transit encryption:** TLS 1.2+ mandatory for all external communications.
- **At-rest encryption:** `target_value_encrypted` protected by KMS; the rest of the database per infrastructure policy.
- **Observability:** Prometheus metrics per channel: latency, success rate, failure rate by error code, retry distribution.

---

## 10. Open Questions

1. What is the final SMTP provider? SendGrid is best known but its IP reputation fluctuates. Amazon SES requires leaving the sandbox. Postmark is premium. The decision affects cost and deliverability.

2. Does the WhatsApp template in Zavu require prior approval by Meta? If so, the approval process takes days and limits message iteration. Product must submit the first approval with time to spare.

3. Should the web-link TTL be configurable per analysis or only global? For now it is global. Product might want 7 days for sensitive analyses and 90 days for relaxed ones, but it introduces complexity without clear need.

4. Should the user be allowed to request "early destruction" of the analysis before the TTL? This would be a common ARCO right (access, rectification, cancellation, opposition). My recommendation: yes, via endpoint with destination hash verification, same as resend.

5. Should the "link expired" page offer the option to upload the contract again with one click? This would require storing the original contract hash (not the content) and pre-populating something, which goes against the "no accounts" posture. My proposal: no, simply redirect to the home page.

6. Should Casa Segura respond to users who reply to the email? The simple option is `noreply@casasegura.sv` which does not accept replies. The better option for service is `reportes@casasegura.sv` with a monitored inbox. Product must decide.

7. Should the system record when someone opens the link to show the user that their report was viewed? This requires telemetry that goes against the no-tracking principle. Recommend no.

8. What to do if the user on WhatsApp requests resend conversationally ("send me the report again")? The bot should respond with instructions, not process it directly. Needs logic in F1 (which is the WhatsApp handler).

---

**End of document.**
