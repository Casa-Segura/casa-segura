---
id: ADR-0002
title: Rename `platform/` module to `platform_core/`
status: Accepted
date: 2026-05-15
deciders: Backend lane
supersedes: —
related: ADR-0001, docs/analysis/_shared/GLOBAL_ASSUMPTIONS.md §1
---

## Context

`docs/analysis/_shared/GLOBAL_ASSUMPTIONS.md` §1 names the central F8-owned
Django module **`platform/`** (root-level, with `app_label = "platform"` and
`db_table = "project"` / `"contract_analysis"` etc.). Per the layered DDD
layout, that module lives directly under the project root and ships with an
`infrastructure/django/` AppConfig registered in `INSTALLED_APPS`.

The name **collides with the Python standard library's `platform` module**.
With `backend/` on `sys.path` (added by `manage.py`), `import platform`
resolves to our local package first and shadows stdlib. Django itself, plus
several third-party dependencies we already install
(`structlog`, `prometheus_client`, build tools, plus future libraries like
`weasyprint` and packaging helpers), do `import platform` in their start-up
paths. The shadow surfaces as opaque `AttributeError` / `ModuleNotFoundError`
at boot time, well-known footgun in the Django community.

We hit this directly while standing up Phase 0: any code that successfully
imports `platform_core.infrastructure.django.models` would, in the same
interpreter, also touch stdlib `platform` for OS/version reporting and break.

## Decision

Rename the module from `platform/` to **`platform_core/`** throughout the
codebase. Concretely:

- Filesystem: `backend/platform_core/{domain,infrastructure}/...`
- Python package: `platform_core.*`
- Django AppConfig: `PlatformCoreConfig(name="platform_core.infrastructure.django", label="platform_core")`
- `MIGRATION_MODULES`: `{"platform_core": "platform_core.infrastructure.django.migrations"}`
- `db_table` values for the owned models stay as **`project`**,
  **`contract_analysis`**, **`privacy_audit_log`**, **`job_execution_log`**
  — the rename is package-only; table names are unchanged so PRDs, F8 plan,
  and DOMAIN_MODEL §3 stay accurate at the SQL layer.
- Cross-module FK string references use `"platform_core.ContractAnalysis"`
  (e.g. from `ingestion.ContractSubmission.analysis`,
  `delivery.DeliveryRequest.analysis`).

`app_label` is `platform_core` (not `platform`) so that `softdelete` and
Django's introspection do not confuse it with anything else. Migration
modules live under `platform_core.infrastructure.django.migrations`.

## Consequences

**Positive.**
- Eliminates the stdlib shadow at zero functional cost.
- Greppable: a search for `platform_core` finds the module and never matches
  the stdlib accidentally.
- DOMAIN_MODEL §3 (Project, ContractAnalysis) is unchanged at the data
  layer — only the Python package name moves.

**Negative.**
- Per-feature plans F1–F8 in `docs/analysis/` still spell the import path as
  `platform.*` (e.g. `platform.infrastructure.django`). Those docs are now
  slightly stale on this naming choice. Treat any `platform.*` import path
  in those plans as `platform_core.*`. The schema tables/columns they cite
  remain correct.
- `GLOBAL_ASSUMPTIONS.md` §1 lists the module as `platform/` in its layout
  diagram. Will be updated in the same window we update STATUS.md to reflect
  Phase 0 progress.

## Alternatives considered

1. **Keep `platform/` and audit every dependency for `import platform`.**
   Rejected: brittle. Any new dependency can break us silently.
2. **Use `apps/platform/` (subpackage under `apps/`).** Rejected: deviates
   further from the assumption doc layout and adds a level of nesting that
   the rest of the modules (`ingestion/`, `corpus/`, …) don't have.
3. **Rename to `core/`.** Rejected: too generic; `shared/` already covers
   shared repository infrastructure.
4. **Skip implementation; do it later.** Rejected: package renames during
   Phase 1+ require migration-name and import rewrites across feature
   modules. Doing it before any feature module imports `platform_core` is
   cheap; doing it later compounds.
