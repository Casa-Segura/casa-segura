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

Backend stack decision: [ADR-0001 — Django backend](docs/adr/ADR-0001-django-backend-stack.md).

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

> [!CAUTION]
> **Privacy:** Treat OCR payloads, delivery targets (email, WhatsApp), report text, prompts, logs, and error bodies as **sensitive**. Do not log PII or raw files beyond what the API needs.
