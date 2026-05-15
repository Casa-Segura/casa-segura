---
id: EPIC-00
name: Foundation & Tooling
phase: 0
status: backlog
depends_on: []
prd_refs:
  - ARCHITECTURE
  - BE-SERVICES
  - PRD_GENERAL §5
feature: cross-cutting
owner: tbd
tags:
  - casa-segura
  - epic
  - epic-00
---

# EPIC-00 — Foundation & Tooling

## Goal

Bootstrap the repository and the developer environment so every other epic can start writing service code without paving the road first. This covers monorepo layout, **Django 5.2 LTS** + **Django REST Framework (DRF)** and Next.js scaffolds, CI, secrets baseline, logging conventions with the versioning fields the PRDs demand (`rubric_version`, `corpus_version`, analysis correlation IDs), and the error envelope contract that every API response will speak. Stack rationale and boundaries: [ADR-0001 — Django backend stack](../adr/ADR-0001-django-backend-stack.md).

This epic is BE-heavy on purpose — the FE scaffold is a thin shell that waits on stable BE contracts (per your direction).

## Definition of done

- [ ] Repo public on GitHub under MIT, README states project posture and "not legal advice" disclaimer
- [ ] `apps/api` runs locally via `python manage.py runserver` (or project-documented equivalent) with one health endpoint, types check clean, tests run green
- [ ] `apps/web` runs `next dev` locally with one page, types check clean
- [ ] CI runs lint + type-check + test + build on every PR, blocks merge on failure
- [ ] `.env.example` enumerates every variable the system needs across all services (per [[BE-SERVICES]] §9)
- [ ] Structured logging emits JSON with correlation ID and version stamps on every record
- [ ] Standard error response shape is documented and used by every endpoint
- [ ] Versioning ADR exists: how `rubric_version`, `corpus_version`, API `schema_version` are bumped

## In scope

- Monorepo skeleton (`apps/api`, `apps/web`, `packages/` if shared types emerge)
- Tooling: ruff, black, mypy, pytest on Python; ESLint, Prettier, TypeScript, Vitest on web
- Dockerfile for the API, docker-compose for local Postgres + Redis
- Pre-commit hooks
- Logging configuration
- Error envelope schema
- Disclaimer copy registry (a single source of truth for "Esto no es asesoría legal" so [[PRD_GENERAL]] BR-07 is mechanically enforceable)

## Out of scope (explicit)

- Database schema — owned by [[EPIC-01-persistence]]
- Any service-layer code beyond /health — those live in their feature epics
- Production deploy targets — that's [[EPIC-11-observability]]
- Auth — the product has no user accounts (D3); nothing to scaffold
- Frontend pages beyond a placeholder — see [[EPIC-10-frontend]]

## Dependencies

- Blocks: every other epic
- Blocked by: none

## Tickets

- [[CS-001]] — Initialize public repo with MIT license and README skeleton
- [[CS-002]] — Django + DRF API scaffold with pyproject, ruff, mypy, pytest (per [ADR-0001](../adr/ADR-0001-django-backend-stack.md))
- [[CS-003]] — Next.js scaffold with Tailwind, shadcn/ui, ESLint, Prettier
- [[CS-004]] — CI pipeline (lint, type-check, test, build) on PR
- [[CS-005]] — Pre-commit hooks for both `apps/api` and `apps/web`
- [[CS-006]] — Secrets baseline (.env.example with every variable from [[BE-SERVICES]] §9)
- [[CS-007]] — Structured logging with correlation IDs and version fields
- [[CS-008]] — Health and readiness endpoints
- [[CS-009]] — Standard error envelope schema
- [[CS-010]] — Versioning ADR (rubric, corpus, API schema)

## Risks

| ID | Risk | Mitigation |
|---|---|---|
| R-00-1 | Monorepo tooling friction slows everyone | Pick boring defaults; revisit only if proven necessary |
| R-00-2 | Disclaimer copy drifts across surfaces | Single registry module, imported everywhere; lint rule against literal strings |

## Notes

- [[BE-SERVICES]] §9 has the complete env var list
- [[PRD_GENERAL]] BR-07 requires the disclaimer in every user-facing surface — mechanise via [[CS-006]] / [[CS-009]]
