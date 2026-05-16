---
id: EPIC-08
name: Multi-Channel Delivery
phase: 5
status: backlog
depends_on:
  - EPIC-01
  - EPIC-07
prd_refs:
  - PRD_GENERAL US-05
  - FEATURES_MAP §4 (F7)
  - RUBRICA_CONTRATO §13
  - BE-SERVICES §1, §5
feature: F7
owner: tbd
tags:
  - casa-segura
  - epic
  - epic-08
  - delivery
---

# EPIC-08 — Multi-Channel Delivery

## Goal

Deliver the rendered report through the channel the user chose at submission time: SMS summary, email PDF, or public web link with TTL. Manage delivery state, retries, and link expiration. Honor the privacy invariants in [[PRD_GENERAL]] BR-01 (no persisted report) and US-07 (hashed delivery targets, discard after confirmation).

Casa Segura is Python / **Django 5.2 LTS** + **DRF** / **Django ORM**, with **Celery** on **Redis** for async work. Delivery tickets use Django services and queue workers; no Node/Fastify/Zavu implementation is part of the MVP. See [ADR-0001 — Django backend stack](../adr/ADR-0001-django-backend-stack.md).

## Definition of done

- [ ] User can choose `sms_summary`, `email_pdf`, or `web_link` at submission time
- [ ] Email path sends PDF as attachment with Spanish subject and body, disclaimer included
- [ ] SMS path sends a concise summary with score/band, link to full HTML report, and disclaimer shorthand
- [ ] Web link path serves HTML on demand (regenerated, not persisted per [[PRD_GENERAL]] BR-01)
- [ ] Link respects TTL; expired links return the friendly Spanish message from [[PRD_GENERAL]] US-05
- [ ] Delivery target stored only as hash; original value discarded after delivery confirmation
- [ ] Failed deliveries retry with exponential backoff; permanent failures recorded with reason
- [ ] On-demand resend works given the `public_short_id` + hash match per [[RUBRICA_CONTRATO]] §13.4
- [ ] Provider acknowledgements update `DeliveryRequest.status` without logging raw destinations

## In scope

- `DeliveryRequest` lifecycle (already schema'd in [[EPIC-01-persistence]])
- Email transport (SMTP or transactional API; configurable)
- PDF generation orchestration — uses output of [[EPIC-07-report-generation]]
- SMS provider wrapper (thin adapter around the configured transactional SMS provider)
- SMS message composer with strict segment-budget guardrails
- Provider callback endpoint if selected SMS provider supports delivery callbacks
- Worker / queue pattern for outbound delivery (**Celery** on **Redis**; align with [ADR-0001](../adr/ADR-0001-django-backend-stack.md))
- Rate limiting aligned with provider tier
- Retry policy with exponential backoff
- Link TTL enforcement at serve time

## Out of scope (explicit)

- Inbound SMS conversations (receiving photos/PDFs over SMS) — not in MVP; web upload remains primary
- Report HTML/PDF generation — [[EPIC-07-report-generation]]
- WhatsApp/Zavu or other channels not in [[PRD_GENERAL]] US-05
- Per-user delivery history UI — there is no user account ([[PRD_GENERAL]] D3)

## Dependencies

- Blocks: end-to-end demo, MVP delivery
- Blocked by: [[EPIC-07-report-generation]] (need the rendered report), [[EPIC-01-persistence]] (`DeliveryRequest` model)

## Tickets

### Delivery service core

- [[CS-230]] — Pydantic schemas for delivery: DeliveryRequest payload, channel enum, status enum
- [[CS-231]] — Delivery service interface (channel-agnostic dispatcher)
- [[CS-232]] — Hashed delivery target storage; clear original after confirmation
- [[CS-233]] — Celery + Redis worker / queue scaffolding (ADR + impl)
- [[CS-234]] — Retry policy with exponential backoff and dead-letter

### Email channel

- [[CS-235]] — Email transport client (SMTP or transactional API)
- [[CS-236]] — Email composition: subject, body, PDF attachment, disclaimer
- [[CS-237]] — Email delivery handler wired to the queue

### SMS channel

- [[CS-238]] — SMS provider client in Python
- [[CS-239]] — SMS template/message registry as code-side contract
- [[CS-240]] — SMS summary composer (score + link, Spanish, "tú")
- [[CS-241]] — SMS delivery handler wired to the queue with rate limiter
- [[CS-242]] — SMS provider callback endpoint if provider supports delivery status callbacks
- [[CS-243]] — SMS/SMTP error handling: INVALID_PHONE_NUMBER, RATE_LIMITED, PROVIDER_UNAVAILABLE, generic
- [[CS-244]] — `SMS_*` provider secrets wired through [[CS-006]] secrets baseline

### Web link channel

- [[CS-245]] — Public link route (`GET /r/{public_short_id}`) with TTL gate
- [[CS-246]] — Expired-link friendly response per [[PRD_GENERAL]] US-05
- [[CS-247]] — On-demand report regeneration (no persistence per BR-01)

### Resend and integrity

- [[CS-248]] — On-demand resend with `public_short_id` + hash verification per [[RUBRICA_CONTRATO]] §13.4

## Risks

| ID | Risk | Mitigation |
|---|---|---|
| R-08-1 | SMS provider choice changes endpoint/error shapes | Thin adapter interface; cover with mocked-provider tests; keep provider-specific details outside domain DTOs |
| R-08-2 | SMS sender registration or carrier filtering delays launch | [[CS-239]] enforces concise transactional template text; fall back to email/link while SMS is unavailable |
| R-08-3 | Rate limits exceeded on burst | Queue with rate limiter set to provider tier ceiling |
| R-08-4 | Delivery target leaks through logs | Hashing happens in [[CS-232]]; lint rule against logging raw `to:` fields |
| R-08-5 | Public link guessable | `public_short_id` is base32 of random ≥ 6 chars; expiry caps exposure |

## Notes

- [[BE-SERVICES]] §5 has the updated `LegalReference` schema; SMS should link to the full report instead of attempting to fit citations into the message body.
- [[PRD_GENERAL]] BR-07 disclaimer is in every channel's template — verify in [[CS-236]], [[CS-240]] AC.
