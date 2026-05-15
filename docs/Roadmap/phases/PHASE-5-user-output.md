---
project: Casa Segura
doc_type: phase_index
phase: 5
status: living
last_updated: 2026-05-15
tags:
  - casa-segura
  - roadmap
  - phase-5
---

# Phase 5 - User Output

Goal: render analysis results into reusable HTML/PDF reports and deliver them through email, WhatsApp/Zavu, or public web links.

Source epics:

- [EPIC-07 - Report Generation](../EPIC-07-report-generation.md)
- [EPIC-08 - Multi-Channel Delivery](../EPIC-08-multichannel-delivery.md)

## Report Generation

- [CS-200](../tickets/CS-200.md) - Jinja report shell with eight sections.
- [CS-201](../tickets/CS-201.md) - Header identification and disclaimers.
- [CS-202](../tickets/CS-202.md) - Overall verdict and override box.
- [CS-203](../tickets/CS-203.md) - Economic analysis with benchmark bar.
- [CS-204](../tickets/CS-204.md) - Category breakdown with collapsible rows.
- [CS-205](../tickets/CS-205.md) - Highlighted findings with legal cards.
- [CS-206](../tickets/CS-206.md) - Referenced legal bases.
- [CS-207](../tickets/CS-207.md) - Suggested actions.
- [CS-208](../tickets/CS-208.md) - Footer disclaimers, versions, integrity hash.
- [CS-209](../tickets/CS-209.md) - PDF rendering via WeasyPrint.
- [CS-210](../tickets/CS-210.md) - Mobile 360px and self-contained envelope validation.

## Multi-Channel Delivery

- [CS-230](../tickets/CS-230.md) - Delivery Pydantic schemas and enums.
- [CS-231](../tickets/CS-231.md) - Channel-agnostic delivery dispatcher.
- [CS-232](../tickets/CS-232.md) - Hashed delivery target storage.
- [CS-233](../tickets/CS-233.md) - Worker/queue scaffolding ADR and implementation.
- [CS-234](../tickets/CS-234.md) - Retry/backoff and dead-letter handling.
- [CS-235](../tickets/CS-235.md) - Email transport client.
- [CS-236](../tickets/CS-236.md) - Email composition.
- [CS-237](../tickets/CS-237.md) - Email delivery worker path.
- [CS-238](../tickets/CS-238.md) - Zavu HTTP client.
- [CS-239](../tickets/CS-239.md) - Zavu template registry.
- [CS-240](../tickets/CS-240.md) - WhatsApp summary composer.
- [CS-241](../tickets/CS-241.md) - WhatsApp/Zavu dispatch handler.
- [CS-242](../tickets/CS-242.md) - Zavu webhook endpoint.
- [CS-243](../tickets/CS-243.md) - Zavu/SMTP error normalization.
- [CS-244](../tickets/CS-244.md) - Zavu secrets wiring.
- [CS-245](../tickets/CS-245.md) - Public report route with TTL enforcement.
- [CS-246](../tickets/CS-246.md) - Expired-link friendly response.
- [CS-247](../tickets/CS-247.md) - On-demand report regeneration.
- [CS-248](../tickets/CS-248.md) - On-demand resend with hash verification.

## Parallel Pick Guidance

- Backend/report owner: report shell, sections, PDF rendering, and mobile HTML checks.
- Delivery owner: schemas, dispatcher, queue, retry policy, email, Zavu, webhook, and public link route.
- Frontend owner: result page and delivery UI under the cross-cutting frontend tickets.

