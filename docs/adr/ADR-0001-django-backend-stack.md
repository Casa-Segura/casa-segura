# ADR-0001: Django backend stack (implementation standard)

- **Status:** Accepted  
- **Date:** 2026-05-15  
- **Context:** High-level docs and feature plans must agree on how Casa Segura is implemented so engineers do not follow outdated HTTP/ORM/migration assumptions.

## Decision

The backend implementation standard is:

| Area | Choice |
|------|--------|
| Web API | **Django 5.2 LTS** + **Django REST Framework** (3.15+) |
| Domain models & payloads | **Pydantic v2** `BaseModel` — framework-free DTOs, LLM structured output, Celery/Redis message envelopes (no Django imports in `domain/`) |
| Persistence | **Django ORM** on **PostgreSQL 15+** with the **`pgvector`** extension (`pgvector.django.VectorField` or equivalent) |
| Schema changes | **Django migrations** only (no Alembic) |
| Async work | **Celery** 5.4+ with **Redis** as broker; **`django-celery-beat`** for schedules where needed |
| Cache / sessions / streams | **Redis** (sessions, rate limits, optional Redis Streams for pipeline handoffs per `GLOBAL_ASSUMPTIONS.md`) |

## Consequences

- **Positive:** One ORM and one migration story; admin, Postgres types, and community patterns align with long-term LTS.  
- **Positive:** Pydantic stays the boundary for typed domain and queue contracts without tying business rules to the ORM.  
- **Superseded assumptions:** Implementation docs must **not** assume **FastAPI** as the app container, **SQLAlchemy** as the primary ORM, or **Alembic** for migrations. Any remaining mention of those is **historical** only if explicitly labeled stale or superseded.

## Related

- `docs/analysis/_shared/GLOBAL_ASSUMPTIONS.md` §1 (authoritative detail)  
- `docs/ARCHITECTURE.md`, `docs/BE Documents/BE-SERVICES.md`, `docs/RAG Legal context/ARCHITECTURE-LEGAL-LAYER.md` (stack alignment)
