# Design Patterns — F7: Multi-Channel Delivery

> Generated: 2026-05-15

---

## Patterns Applied

### Strategy (Channel sender)

**Why it fits:** Three channels with very different protocols (SMS provider, SMTP, web link served on demand) but the same upstream contract: `(DeliveryRequest, ReportBuildContext) → ProviderResult`. Encapsulating each channel as a class implementing the same `Protocol` keeps `DeliveryService.dispatch` linear.

**What it covers:** `SmsSender`, `EmailSender`. The `web_link` channel does not need a proactive sender — it's served by `PublicLinkView`.

**Implementation location:** `delivery/infrastructure/channels/{sms,email}_sender.py`; common `ChannelSender` `Protocol` in `delivery/domain/protocols.py`.

---

### Idempotent send with provider message id

**Why it fits:** If the provider accepts the message but the network reply is lost, retrying produces a duplicate. Two defenses: (1) idempotency key derived from `dr_id` passed to the provider when supported; (2) before sending on retry, check the provider for a pre-existing message id via `provider_message_id` lookup (when the provider supports it).

**Implementation location:** `SmtpClient.send_email(idempotency_key=dr_id)`; `SmsClient.send_sms(idempotency_key=dr_id)`.

---

### Exponential backoff with jitter

**Why it fits:** Thundering-herd retries cause provider rate-limits. Backoff with jitter spreads retries.

**Implementation:** `compute_next_backoff(attempt)` returns `30s × 2^(attempt-1) × random(0.8, 1.2)`. Persisted in `next_attempt_not_before`.

---

### Scheduler poll (Celery Beat → ready set)

**Why it fits:** Celery's `apply_async(eta=...)` is acceptable for delayed tasks but harder to inspect and recover from. A periodic `every 1 min` task that queries `WHERE status='queued' AND next_attempt_not_before <= NOW()` is observable, restartable, and works through worker restarts.

**Implementation:** `delivery.retry_due_deliveries` periodic task; partial index on `next_attempt_not_before WHERE status='queued'` keeps the query fast.

---

### Capability Token

**Why it fits:** No user accounts. `public_short_id` is the access key. Authorization is "do you have the id?". The id has ≥ 30 bits of entropy in the suffix, so guessing is infeasible.

**Implementation:** `PublicLinkView` accepts any `short_id`; lookup is the only gate.

---

### Encrypted-in-flight + Hash-at-rest

**Why it fits:** The user's destination must round-trip through the delivery flow but never linger as cleartext. KMS encryption while the `DeliveryRequest` is in queue/sending; cleared on success or 24 h. Hash kept for resend auth.

**Implementation:**
- `KmsClient.encrypt/decrypt` abstraction with three implementations
- `delivery_request.target_value_encrypted` cleared in the same UPDATE that sets `status=delivered`
- `delivery_request.target_value_encrypted_kms_key_id` records which key (allows key rotation: future cleartext encrypted with a new key id, prior values remain decryptable until they expire)

---

### Hash-based authentication for resend

**Why it fits:** Without user accounts, the only way to authenticate a resend request is "prove you know the destination". The user types the destination; F7 hashes it and constant-time-compares against the stored `delivery_target_hash`.

**Implementation:** `hmac.compare_digest` against `sha256(salt + submitted_target)`. Salt is the global `DELIVERY_TARGET_SALT` env var.

---

### Circuit breaker for SMTP / SMS

**Why it fits:** Same rationale as F1's OpenRouter. If SMTP or SMS fails consistently, fail-fast the next requests so they go straight to retry without blocking workers.

**Implementation:** Reused `shared.infrastructure.resilience.circuit_breaker`.

---

## Patterns Considered and Rejected

### Synchronous email send on user click

Tempting: when the user clicks "send report", block the HTTP request until the email goes. Rejected because: SMTP latency varies; UI degrades; retries are easier as background tasks.

### Webhook-based delivery confirmation

Tempting: subscribe to SMTP provider webhooks for `delivered`/`bounced` events. Rejected at MVP because: webhook security adds complexity; the provider's synchronous 250 OK is sufficient evidence; bounces escalate later via the provider's daily report. Re-add when scale justifies.

### Allow channel change on resend

PRD §10 Q-4 close. Rejected because: the user could route the report to an attacker's destination after the original delivery confirmed nothing. The constraint "resend = same destination only" mitigates phishing.

### Open/click pixel tracking

PRD §10 Q-7. Rejected. Casa Segura's no-tracking promise is structural.

### Allow early destruction by user request

PRD §10 Q-4 in F7 / OQ-3 in F8. Recommended for v2; documented but not implemented at MVP.

---

**End of document.**
