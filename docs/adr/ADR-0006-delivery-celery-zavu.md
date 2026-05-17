# ADR-0006: Delivery Celery queues and Zavu email transport

- **Status:** Accepted  
- **Date:** 2026-05-17  
- **Context:** EPIC-08 requires async outbound delivery with retries. Transactional email is implemented via the Zavu HTTP API (`zavudev` SDK). Separately, Zavu signs webhook callbacks with `X-Zavu-Signature` using **`ZAVU_WEBHOOK_SECRET`** (distinct from **`ZAVUDEV_API_KEY`** / `ZAVU_API_KEY` used for outbound sends).

## Decision

| Topic | Choice |
|-------|--------|
| Broker / backend | **Redis** URLs `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` (already in Django settings) |
| Celery app | Django entrypoint **`celery -A config.celery worker`**; tasks module **`delivery.infrastructure.django.tasks`** |
| Queue naming | Default Celery queue; dedicated **`delivery`** queue configurable via `task_routes` when traffic warrants splitting workers |
| Outbound email | **`send_zavu_email`** wrapper (`delivery.infrastructure.external.zavu_messaging`) behind an **`EmailTransport`** abstraction (optional SMTP adapter later per CS-235) |
| Inbound provider callbacks | **`POST /api/v1/webhooks/zavu/`** verifies HMAC per Zavu docs; **SMS** provider callbacks remain **[[CS-242]]** (separate endpoint/secret) |
| Retry ownership | **`delivery.application.retry_policy`** computes `next_attempt_not_before` with jitter ([[CS-234]]); worker respects persisted **`DeliveryRequest.status`** for idempotent replay |

## Consequences

- Operators configure **`ZAVU_WEBHOOK_SECRET`** in Zavu dashboard / sender webhook settings alongside **`ZAVUDEV_API_KEY`** for sends.
- Local dev: **`make celery-worker`** (see backend Makefile); **`docker-compose.dev.yml`** may run a worker profile alongside Redis.

## Related

- [ADR-0001 — Django backend stack](ADR-0001-django-backend-stack.md)  
- [[EPIC-08-multichannel-delivery]](../Roadmap/EPIC-08-multichannel-delivery.md)  
- `backend/delivery/infrastructure/external/zavu_messaging.py`  
- `backend/delivery/interfaces/api/views.py` (`ZavuWebhookView`)
