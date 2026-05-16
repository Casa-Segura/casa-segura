# Complete Flows — F7: Multi-Channel Delivery

> Generated: 2026-05-15

---

## Flow Index

| # | Flow |
|---|---|
| 1 | Email delivery — happy path |
| 2 | SMS delivery — happy path |
| 3 | Public web link served |
| 4 | Resend (user-initiated) |
| 5 | Retry with exponential backoff |
| 6 | Permanent failure |
| 7 | Link expiration (cron) |
| 8 | Internal manual retry |
| 9 | Delivery status query |

---

## Flow 1: Email delivery — happy path

### Pre-conditions
- F4 has completed analysis and dispatched the Celery chain.
- F1 stored the cleartext email in Redis (`target_blob:{analysis_id}`, TTL ≤ 300 s).
- `contract_analysis.delivery_channel='email_pdf'`, `delivery_target_hash` set, `link_expires_at` set.

### Trigger
Celery chain step `delivery.deliver_to_user(analysis_id)`.

### Happy Path

1. Service reads cleartext from Redis. If missing (TTL expired), abort with `EXTRACTION_TARGET_GONE` → mark analysis `delivery_status='failed'` + ops alert.
2. Service KMS-encrypts cleartext.
3. Service creates `DeliveryRequest(status=queued, channel=email_pdf, target_hash, target_value_encrypted, kms_key_id, attempt_count=0, max_attempts=3)`.
4. Service updates `DeliveryRequest(status=sending, attempt_count=1)`.
5. Service calls `ReportService.generate_pdf(analysis_id)` to obtain PDF bytes.
6. Service composes email:
   - From: `Casa Segura <reportes@casasegura.sv>`
   - Subject: `Tu análisis de contrato — Casa Segura — {readable_contract_type}`
   - Body: simple HTML with score, executive summary one-liner, link to HTML report, disclaimer.
   - Attachment: `casa_segura_{public_short_id}.pdf`
7. Service calls SMTP. Provider returns 250 + message id.
8. Service updates `DeliveryRequest(status=delivered, delivered_at=NOW(), provider_message_id=..., target_value_encrypted=NULL)`.
9. Service updates `contract_analysis(delivery_status='sent_email')`.
10. Service deletes Redis blob.

### Error Scenarios

| ID | Condition | Outcome |
|---|---|---|
| E-1 | Redis blob missing | `failed`, `error_code=EXTRACTION_TARGET_GONE` |
| E-2 | KMS unreachable | `failed`, `error_code=KMS_UNAVAILABLE`; ops alert |
| E-3 | PDF generation fails | Fallback to HTML-only (no attachment), notify user; if HTML also fails → `failed` |
| E-4 | SMTP transient 5xx | Retry per Flow 5 |
| E-5 | SMTP permanent 5xx or invalid address bounce | Flow 6 |
| E-6 | Email blocked by reputation | Permanent; Flow 6 |

---

## Flow 2: SMS delivery — happy path

### Pre-conditions
- `delivery_channel='sms_summary'`, phone in Redis blob, target_hash set.

### Happy Path

1. KMS-decrypt cleartext phone (or use Redis blob directly + encrypt for persistence).
2. Build SMS body with `{score, band_label, link_url, expiry_date, public_short_id}`.
3. POST to SMS provider `/messages` with the approved Casa Segura body.
4. Provider accepts → status `delivered`, provider_message_id stored.
5. `contract_analysis.delivery_status='sent_sms'`.

### Error Scenarios

| ID | Condition | Outcome |
|---|---|---|
| E-1 | Invalid/unreachable phone | Permanent failure; offer email alternative (UI concern) |
| E-2 | SMS body/template invalid | Permanent failure; ops alert |
| E-3 | SMS provider rate limit | Transient retry |

---

## Flow 3: Public web link served

### Trigger
`GET /r/{short_id}` (anonymous).

### Happy Path

1. View looks up `contract_analysis.public_short_id`.
2. If not found → 404 with generic HTML.
3. If `link_expires_at <= NOW()` OR `delivery_status='expired'` → 410 with the "link expired" HTML page.
4. If anonymized → call `ReportService.generate_html` (renders anonymized template).
5. Else → call `ReportService.generate_html` (full template).
6. Return HTML with `X-Robots-Tag: noindex, nofollow`, `Cache-Control: no-store`, `Strict-Transport-Security: max-age=31536000`.

### Notes

- Optional in-memory micro-cache 5 min per short_id to reduce F6 load on hot reports.
- The view increments an anonymous Prometheus counter; no per-visitor tracking.

---

## Flow 4: Resend

### Trigger
`POST /v1/contracts/{short_id}/resend` body `{target: "u@x.com"}`.

### Happy Path

1. View looks up analysis by short_id; 404 if not found.
2. Check `resend_count < 3`; if not → 429 `RESEND_LIMIT_EXCEEDED`.
3. Hash submitted target with global salt.
4. `hmac.compare_digest(submitted_hash, analysis.delivery_target_hash)`.
5. On mismatch → 403 `TARGET_MISMATCH`.
6. On match:
   - Create new `DeliveryRequest(is_resend=true, parent_delivery_request_id=<last_one>, status=queued, ciphertext=KMS(target), target_hash=submitted_hash, channel=analysis.delivery_channel)`.
   - `UPDATE contract_analysis SET resend_count = resend_count + 1 WHERE id=...`.
   - Dispatch immediately (Celery `apply_async()`).
   - Return 202 with `{delivery_request_id, estimated_delivery_seconds, channel}`.

### Post-conditions

- New DeliveryRequest row; resend_count incremented atomically.

---

## Flow 5: Retry with exponential backoff

### Trigger
Provider returns transient error during sending.

### Happy Path

1. `DeliveryService` catches the transient classification.
2. `backoff = 30s × 2^(attempt-1) × random(0.8, 1.2)`.
3. UPDATE `DeliveryRequest(status=queued, attempt_count+=1, last_error_code, last_error_classification='transient', next_attempt_not_before=NOW()+backoff)`.
4. Celery Beat task `delivery.retry_due_deliveries` runs every 1 min:
   - `SELECT id FROM delivery_request WHERE status='queued' AND next_attempt_not_before <= NOW() LIMIT 100`.
   - For each: `retry_delivery.delay(dr_id)`.
5. `retry_delivery` re-invokes `dispatch(dr)`.
6. After `max_attempts` exhausted with no success → Flow 6.

### Backoff Schedule

| Attempt | Backoff (base) |
|---|---|
| 1 → 2 | 30 s |
| 2 → 3 | 5 min |
| 3 → final | 30 min (final attempt) |

With ±20% jitter applied uniformly.

---

## Flow 6: Permanent failure

### Trigger
- Provider returns permanent error (invalid address, blocked number) OR
- `attempt_count >= max_attempts`.

### Happy Path

1. UPDATE `DeliveryRequest(status=failed, last_error_*, target_value_encrypted=NULL)`.
2. UPDATE `contract_analysis(delivery_status='failed')`.
3. Prometheus counter `f7_delivery_outcome_total{channel, outcome='failed'}` incremented.
4. If failure rate exceeds threshold over the window, an ops alert fires.

### User experience

The user has no automated notification (we cannot reach them by definition). They may:
- Check status via `/v1/contracts/{short_id}/delivery-status` (which they can call if they have the short id).
- Use the web-link channel (which is always available via the short_id).

---

## Flow 7: Link expiration

### Trigger
Hourly Celery Beat task `delivery.expire_links` (F8 owns the schedule; F7 owns the implementation).

### Happy Path

```sql
UPDATE contract_analysis
SET delivery_status = 'expired'
WHERE link_expires_at < NOW()
  AND delivery_status NOT IN ('expired','failed');
```

Subsequent `GET /r/{short_id}` returns 410.

---

## Flow 8: Internal manual retry

### Trigger
`POST /v1/internal/delivery/retry/{delivery_request_id}` with `X-Internal-Auth`.

### Happy Path

1. Verify auth header.
2. Load DeliveryRequest by id.
3. If `status != failed`, reject (400).
4. If `expires_at < NOW()`, reject (410 — original encrypted target may already be gone).
5. Reset `attempt_count=0`, `status=queued`, `next_attempt_not_before=NOW()`.
6. Operator can also override `max_attempts` if needed.

---

## Flow 9: Delivery status query

### Trigger
`GET /v1/contracts/{short_id}/delivery-status`.

### Happy Path

Returns:

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

No PII; the user does not see the destination.

---

**End of document.**
