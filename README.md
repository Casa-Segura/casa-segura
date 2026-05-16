# Casa Segura

**Automated analysis of Salvadoran real estate contracts** — upload a PDF or photos, get a structured report (rubric score, findings, economic context, citations) so you can decide whether to negotiate or talk to a lawyer **before** signing. User-facing experiences use Spanish in the informal **tú** register.

> [!IMPORTANT]
> **Aviso legal (BR-07):** Todo lo que vea el usuario debe incluir la frase exacta **«Esto no es asesoría legal»**. Este repositorio es código y documentación de producto; **no** sustituye asesoría jurídica.

## What this project is (and is not)

**In scope:** ingestion + OCR, classification, rubric-driven evaluation, report generation, and multichannel delivery (e.g. web link, email, WhatsApp) aligned with the formal PRDs — focused on **understanding the contract text**, not on validating people or projects against government registries.

**Explicitly out of scope for MVP:** material registry checks, billboard / “valla” verification as a gate, blacklists, user accounts as a primary model, personalized legal advice, permanent storage of raw contract blobs, and non-Salvadoran contracts. Details: [PRD General](docs/Casa%20Segura%20Formal%20PRDs/PRD_GENERAL.md).

## How we ship work

Requirements are decomposed into **features F1–F8**, **epics**, and **tickets (`CS-*`)** with `depends_on`, acceptance criteria, and `status`. We add capability **incrementally**; the roadmap—not this README—is the checklist for what is actually done.

| Resource | Use it for |
|----------|------------|
| [Roadmap index](docs/Roadmap/README.md) | PRD → epic → ticket mapping and numbering blocks |
| [Phase index](docs/Roadmap/phases/README.md) | Picking work by delivery phase |
| [Parallel work plan](docs/Roadmap/PARALLEL_WORK_PLAN.md) | Lanes: `FE WORK`, `BE WORK`, `INFRA WORK`, `API / AI CONNECTIONS` |
| [AGENTS.md](AGENTS.md) | Ticket/epic hygiene, canonical paths (`backend/`, `frontend/`), privacy norms |

Supporting references: [Feature map](docs/Casa%20Segura%20Formal%20PRDs/FEATURES_MAP.md), [Architecture](docs/ARCHITECTURE.md), [Domain model](docs/Casa%20Segura%20Formal%20PRDs/DOMAIN_MODEL.md).

## Technology

| Layer | Stack |
|-------|--------|
| **Web** | [Next.js](https://nextjs.org/) 16 (App Router), React 19, TypeScript 5, Tailwind CSS 4, ESLint, Vitest |
| **API & domain** | [Django](https://www.djangoproject.com/) 5.2 LTS, [Django REST Framework](https://www.django-rest-framework.org/), **Pydantic v2**, drf-spectacular (OpenAPI) |
| **Async / jobs** | Celery, Redis |
| **Database** | PostgreSQL 16 + **pgvector** (vectors + relational data per PRDs) |
| **Local dependencies** | [Docker Compose](docker-compose.dev.yml) — Postgres + Redis for development |

Backend stack decisions live in [`docs/adr/`](docs/adr/): [ADR-0001 — Django backend](docs/adr/ADR-0001-django-backend-stack.md) · [ADR-0002 — `platform_core` rename](docs/adr/ADR-0002-rename-platform-module-to-platform_core.md) · [ADR-0003 — CS-031 normalization](docs/adr/ADR-0003-cs031-project-name-normalization-divergence.md) · [ADR-0004 — Versioning strategy](docs/adr/ADR-0004-versioning.md).

Service-level guides: [backend/README.md](backend/README.md) (Django/DRF API, ORM conventions, migrations, transactions) · [frontend/README.md](frontend/README.md) (Next.js app) · [RAILWAY.md](RAILWAY.md) (Railway deployment for `web` / `worker` / `beat` services).

Design tokens and UX references: [`docs/Design/casa-segura.pen`](docs/Design/casa-segura.pen) (Pencil), formal UI notes under PRDs / `docs/`.

## Repository layout

```text
backend/     # Django project, ORM, DRF, Celery tasks, ingestion/analysis services
frontend/    # Next.js app — landing, upload, delivery selection, report viewing
docs/        # Formal PRDs, roadmap (tickets/epics), ADRs, analysis notes
infra/       # Local dev helpers (e.g. Postgres init)
```

## Quick start (development)

> [!NOTE]
> Adjust environment using `backend/.env`, `frontend/.env`, and examples in each package. Never commit secrets.

1. **Start Postgres and Redis**

   ```bash
   docker compose -f docker-compose.dev.yml up -d
   ```

2. **Backend** — from `backend/`, install dependencies (e.g. with Poetry), run migrations, then start the Django dev server (see project settings under `backend/config`).

3. **Frontend**

   ```bash
   cd frontend
   npm install
   cp .env.example .env   # set CASASEGURA_API_BASE_URL and related vars
   npm run dev
   ```

   Open [http://localhost:3000](http://localhost:3000). More detail: [frontend/README.md](frontend/README.md).

### Pre-commit hooks (CS-005)

Local hooks defined in [`.pre-commit-config.yaml`](.pre-commit-config.yaml) run `ruff` (lint + format) on `backend/**/*.py`, `prettier --check` on `frontend/**/*.{ts,tsx,js,jsx,json,md}`, plus generic hygiene (end-of-file, trailing whitespace, YAML/TOML/merge-conflict checks). All hook versions are pinned to match `backend/pyproject.toml`. ESLint and mypy are deferred to CI for speed/path reasons (notes inline in the config). Install once per clone:

```bash
pip install pre-commit          # or: pipx install pre-commit
pre-commit install              # registers the git hook
pre-commit run --all-files      # one-time sweep, optional
```

> [!CAUTION]
> **Privacy:** Treat OCR payloads, delivery targets (email, WhatsApp), report text, prompts, logs, and error bodies as **sensitive**. Do not log PII or raw files beyond what the API needs.

## Backend API contract

### Health and readiness

```
GET /api/health/   →  200 { "status": "ok", "service": "casa-segura-api", "schema_version": "1.0.0", "hostname": "..." }
GET /api/ready/    →  200 { "status": "ok", "schema_version": "1.0.0", "checks": { "database": "ok", "redis": "ok" }, "reasons": [] }
                   →  503 if DB or Redis unreachable, with `reasons` array of failure codes.
```

### Error envelope (CS-009)

Every response — success or failure — mirrors the inbound `X-Request-ID` header (or generates a UUID4 fallback). Failures additionally return the same value in the body as `correlation_id`.

**Success example:**

```http
HTTP/1.1 200 OK
Content-Type: application/json
X-Request-ID: 5e8f1f6c-23a1-4f3a-9c0e-1b2a3c4d5e6f

{ ...domain payload... }
```

**Failure example** (canonical envelope from `backend/config/exception_handler.py`):

```http
HTTP/1.1 400 Bad Request
Content-Type: application/json
X-Request-ID: 5e8f1f6c-23a1-4f3a-9c0e-1b2a3c4d5e6f

{
  "error_code": "validation_error",
  "message": "Request payload failed validation.",
  "details": { "submission_hash": ["This field is required."] },
  "correlation_id": "5e8f1f6c-23a1-4f3a-9c0e-1b2a3c4d5e6f",
  "schema_version": "1.0.0"
}
```

Public error codes registered in `backend/shared/domain/exceptions.py::PUBLIC_ERROR_CODES`. Feature modules may extend by adding to that registry (no shadowing).

## Observability (CS-007)

`backend/shared/observability/logging.py::configure_logging` ships structured JSON logs in production (one record per line) with a stable shape: `timestamp`, `level`, `service`, `correlation_id`, `schema_version`, `rubric_version`, `corpus_version`, plus event-specific fields the caller binds.

`backend/shared/observability/middleware.py::CorrelationIdMiddleware` pulls `X-Request-ID` from the request (or generates UUID4), binds it to structlog contextvars for the request lifetime, and echoes it on the response header. Limit: 128 chars; empty/oversized values fall back to UUID4.

Minimal usage:

```python
import structlog

logger = structlog.get_logger(__name__)

def handle_submission(submission_id):
    logger.info("submission_received", submission_id=str(submission_id), strategy="pypdf")
    # → {"timestamp": "...", "level": "info", "event": "submission_received",
    #    "service": "casa-segura-api", "correlation_id": "...", "schema_version": "1.0.0",
    #    "submission_id": "...", "strategy": "pypdf", "rubric_version": null, "corpus_version": null}
```

Metrics exposed at `/metrics/` via `django-prometheus`.
