---
project: Casa Segura
doc_type: phase_index
phase: 5
status: living
last_updated: 2026-05-17
tags:
  - casa-segura
  - roadmap
  - phase-5
---

# Phase 5 - User Output

Goal: render analysis results into reusable HTML/PDF reports and deliver them through SMS, email, or public web links.

Source epics:

- [EPIC-07 - Report Generation](../EPIC-07-report-generation.md)
- [EPIC-08 - Multi-Channel Delivery](../EPIC-08-multichannel-delivery.md)

Source-of-truth links:

- [PRD_F6_GENERACION_REPORTE](../../Casa%20Segura%20Formal%20PRDs/PRD_F6_GENERACION_REPORTE.md) - report structure, disclaimers, and output expectations.
- [PRD_F7_ENTREGA_MULTICANAL](../../Casa%20Segura%20Formal%20PRDs/PRD_F7_ENTREGA_MULTICANAL.md) - delivery channels and user-facing delivery behavior.
- [DOMAIN_MODEL](../../Casa%20Segura%20Formal%20PRDs/DOMAIN_MODEL.md) - delivery request and report-related data contracts.
- [F6 analysis plan](../../analysis/F6_generacion_reporte/IMPLEMENTATION_PLAN.md) - report implementation breakdown.
- [F7 analysis plan](../../analysis/F7_entrega_multicanal/IMPLEMENTATION_PLAN.md) - delivery implementation breakdown.

## Ready Now

**Backend (2026-05-17):** Multi-channel delivery core for [[EPIC-08-multichannel-delivery]] is implemented under `backend/delivery/` (schemas, dispatcher, Celery task, email/SMS/web-link workers, public `/r/…/`, Zavu + SMS webhooks, resend). End-to-end channel selection at upload remains a separate integration item (see EPIC-08 DoD).

## FE WORK

- [CS-204](../tickets/CS-204.md) - Category breakdown with collapsible rows.
- [CS-210](../tickets/CS-210.md) - Mobile 360px and self-contained envelope validation.
- [CS-246](../tickets/CS-246.md) - Expired-link friendly response.

Coordinate visible report and delivery UI with [CS-291](../tickets/CS-291.md) through [CS-296](../tickets/CS-296.md) in [Cross-Cutting Work](CROSS-cutting.md). Keep Spanish `tú` copy, mobile 360px behavior, and disclaimer placement consistent.

## BE WORK

- [CS-200](../tickets/CS-200.md) - Jinja report shell with eight sections.
- [CS-201](../tickets/CS-201.md) - Header identification and disclaimers.
- [CS-202](../tickets/CS-202.md) - Overall verdict and override box.
- [CS-203](../tickets/CS-203.md) - Economic analysis with benchmark bar.
- [CS-205](../tickets/CS-205.md) - Highlighted findings with legal cards.
- [CS-206](../tickets/CS-206.md) - Referenced legal bases.
- [CS-207](../tickets/CS-207.md) - Suggested actions.
- [CS-208](../tickets/CS-208.md) - Footer disclaimers, versions, integrity hash.
- [CS-209](../tickets/CS-209.md) - PDF rendering via WeasyPrint.
- [CS-230](../tickets/CS-230.md) - Delivery Pydantic schemas and enums.
- [CS-231](../tickets/CS-231.md) - Channel-agnostic delivery dispatcher.
- [CS-232](../tickets/CS-232.md) - Hashed delivery target storage.
- [CS-235](../tickets/CS-235.md) - Email transport client.
- [CS-236](../tickets/CS-236.md) - Email composition.
- [CS-237](../tickets/CS-237.md) - Email delivery worker path.
- [CS-245](../tickets/CS-245.md) - Public report route with TTL enforcement.
- [CS-247](../tickets/CS-247.md) - On-demand report regeneration.
- [CS-248](../tickets/CS-248.md) - On-demand resend with hash verification.

## INFRA WORK

- [CS-233](../tickets/CS-233.md) - Worker/queue scaffolding ADR and implementation.
- [CS-234](../tickets/CS-234.md) - Retry/backoff and dead-letter handling.
- [CS-244](../tickets/CS-244.md) - SMS secrets wiring.

Delivery targets, report content, logs, and webhook payloads are privacy-sensitive. Keep queue, retry, dead-letter, and secrets behavior reviewable.

## API / AI CONNECTIONS

- [CS-238](../tickets/CS-238.md) - SMS provider client.
- [CS-239](../tickets/CS-239.md) - SMS message registry.
- [CS-240](../tickets/CS-240.md) - SMS summary composer.
- [CS-241](../tickets/CS-241.md) - SMS dispatch handler.
- [CS-242](../tickets/CS-242.md) - SMS provider callback endpoint.
- [CS-243](../tickets/CS-243.md) - SMS/SMTP error normalization.

This lane owns external delivery contracts and webhook surfaces. BE still owns persistence and service boundaries around those integrations.

## Parallel Pick Guidance

- BE owns report rendering, PDF generation, delivery schemas, dispatching, public links, and resend/regeneration paths.
- FE owns user-visible report behavior and delivery surfaces through the cross-cutting frontend tickets.
- Infra owns queues, retries, secrets, and operational safety for delivery.
- API / AI owns SMS, SMTP normalization, webhooks, and externally visible delivery contracts.

