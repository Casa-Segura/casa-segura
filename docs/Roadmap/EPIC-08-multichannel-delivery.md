---
id: EPIC-08
name: Multi-Channel Delivery (incl. Zavu)
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
research_refs:
  - GENERATED-RESEARCH-Zavu-implementation-typescript-2026-05-12
tags:
  - casa-segura
  - epic
  - epic-08
  - zavu
---

# EPIC-08 — Multi-Channel Delivery (incl. Zavu)

## Goal

Deliver the rendered report through the channel the user chose at submission time: email PDF, WhatsApp via Zavu, or public web link with TTL. Manage delivery state, retries, and link expiration. Honor the privacy invariants in [[PRD_GENERAL]] BR-01 (no persisted report) and US-07 (hashed delivery targets, discard after confirmation).

This is where **Zavu integration lives**. The TypeScript reference at [[GENERATED-RESEARCH-Zavu-implementation-typescript-2026-05-12]] is **prior art**: it was written for the Huella project (TS / Drizzle / Fastify / BullMQ). Casa Segura is Python / **Django 5.2 LTS** + **DRF** / **Django ORM**, with **Celery** on **Redis** for async work. Tickets in this epic adapt the patterns, they do not copy the code. See [ADR-0001 — Django backend stack](../adr/ADR-0001-django-backend-stack.md).

## Definition of done

- [ ] User can choose `email_pdf`, `whatsapp_summary`, or `web_link` at submission time
- [ ] Email path sends PDF as attachment with Spanish subject and body, disclaimer included
- [ ] WhatsApp path sends summary message via Zavu with score, top critical findings, link to full HTML report
- [ ] Web link path serves HTML on demand (regenerated, not persisted per [[PRD_GENERAL]] BR-01)
- [ ] Link respects TTL; expired links return the friendly Spanish message from [[PRD_GENERAL]] US-05
- [ ] Delivery target stored only as hash; original value discarded after delivery confirmation
- [ ] Failed deliveries retry with exponential backoff; permanent failures recorded with reason
- [ ] On-demand resend works given the `public_short_id` + hash match per [[RUBRICA_CONTRATO]] §13.4
- [ ] Zavu webhook for delivery status updates `DeliveryRequest.status`

## In scope

- `DeliveryRequest` lifecycle (already schema'd in [[EPIC-01-persistence]])
- Email transport (SMTP or transactional API; configurable)
- PDF generation orchestration — uses output of [[EPIC-07-report-generation]]
- Zavu Python client wrapper (no published SDK in Python, so a thin requests-based client)
- Zavu template management (templates created in Zavu dashboard; client supplies template name + parameters)
- Webhook endpoint for Zavu delivery status callbacks with signature validation
- Worker / queue pattern for outbound delivery (**Celery** on **Redis**; align with [ADR-0001](../adr/ADR-0001-django-backend-stack.md))
- Rate limiting aligned with Zavu tier
- Retry policy with exponential backoff
- Link TTL enforcement at serve time

## Out of scope (explicit)

- Inbound WhatsApp (receiving photos/PDFs over WhatsApp) — not in PRD scope; see [[STATUS_RECONCILIATION]] delta #5
- Report HTML/PDF generation — [[EPIC-07-report-generation]]
- SMS or other channels not in [[PRD_GENERAL]] US-05
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

### Zavu / WhatsApp channel

- [[CS-238]] — Zavu HTTP client in Python (adapted from [[GENERATED-RESEARCH-Zavu-implementation-typescript-2026-05-12]])
- [[CS-239]] — Zavu template registry (template names + parameter shapes) as code-side contract
- [[CS-240]] — WhatsApp summary composer (score + top findings + link, Spanish, "tú")
- [[CS-241]] — Zavu delivery handler wired to the queue with rate limiter
- [[CS-242]] — Zavu webhook endpoint for delivery status updates (with signature validation)
- [[CS-243]] — Zavu error handling: INVALID_PHONE_NUMBER, RATE_LIMITED, TEMPLATE_NOT_FOUND, generic
- [[CS-244]] — `ZAVU_API_KEY` and `ZAVU_WEBHOOK_SECRET` secrets wired through [[CS-006]] secrets baseline

### Web link channel

- [[CS-245]] — Public link route (`GET /r/{public_short_id}`) with TTL gate
- [[CS-246]] — Expired-link friendly response per [[PRD_GENERAL]] US-05
- [[CS-247]] — On-demand report regeneration (no persistence per BR-01)

### Resend and integrity

- [[CS-248]] — On-demand resend with `public_short_id` + hash verification per [[RUBRICA_CONTRATO]] §13.4

## Risks

| ID | Risk | Mitigation |
|---|---|---|
| R-08-1 | Zavu Python SDK doesn't exist; we adapt from TS | Thin requests-based client; cover with mocked-server tests; reference [[GENERATED-RESEARCH-Zavu-implementation-typescript-2026-05-12]] for endpoint shapes |
| R-08-2 | Templates not pre-approved → outbound fails outside 24h window | [[CS-239]] enforces template-only outbound; in-band sessions never assumed |
| R-08-3 | Rate limits exceeded on burst | Queue with rate limiter set to Zavu tier ceiling |
| R-08-4 | Delivery target leaks through logs | Hashing happens in [[CS-232]]; lint rule against logging raw `to:` fields |
| R-08-5 | Public link guessable | `public_short_id` is base32 of random ≥ 6 chars; expiry caps exposure |

## Notes

- [[GENERATED-RESEARCH-Zavu-implementation-typescript-2026-05-12]] — prior art. Use for: endpoint shapes, error codes, template structure, webhook payload structure, rate limit tiers, status semantics (sent/delivered/read/failed). Do **not** use for: SDK calls, BullMQ patterns (we use **Celery** on **Redis** — see [[CS-233]]), Drizzle migrations, Fastify routes (implement as **Django** views / **DRF** endpoints).
- [[BE-SERVICES]] §5 has the updated `LegalReference` schema; the WhatsApp summary in [[CS-240]] is expected to include the citation line when a critical finding has one.
- [[PRD_GENERAL]] BR-07 disclaimer is in every channel's template — verify in [[CS-236]], [[CS-240]] AC.
