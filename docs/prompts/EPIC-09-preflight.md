# Preflight prompt — Close F6 gaps & hygiene before Epic 09 (retention jobs)

> **Update 2026-05-17:** The public TTL path now calls **`generate_report_html`** (see `backend/delivery/application/report_html.py` + `tests/test_public_report_route.py`). Treat the **Mission / exit criteria** below as a **completed checklist** unless you are reverifying. For **what is next**, open [`EPIC-09-retention-privacy.md`](../Roadmap/EPIC-09-retention-privacy.md) and Phase 6 tickets **`CS-271`–`CS-276`** ([`CS-270`](../Roadmap/tickets/CS-270.md) scheduler is **`done`**).

Paste everything **below** the divider into **one new Cursor chat** in **Agent mode**. Repo root: **`casa-segura`**. Canonical backend: **`backend/`** (Django 5.2 LTS, DRF, Pydantic v2, Celery on Redis).

**Do not start Epic 09 implementation in this prompt** unless every “exit gate” is satisfied or explicitly documented as intentionally deferred — after this closes, spawn a **second** prompt focused solely on **`docs/Roadmap/EPIC-09-retention-privacy.md`** tickets (`CS-270`–`CS-276`) and Postgres job idempotency.

---

## Roles & attached skills / rules (follow these)

Treat these as **mandatory behavioural context** — load or apply them mentally on every decision:

| Source | Role |
|--------|------|
| **Project** | [`AGENTS.md`](../../AGENTS.md), [`.cursor/rules/backend-python-ruff.mdc`](../../.cursor/rules/backend-python-ruff.mdc) — roadmap truth (`docs/Roadmap/tickets/CS-*.md`), ticket/epic hygiene, **run `poetry run ruff check` from `backend/`** on touched Python |
| **`django-expert`** | Thin Django views/routes; keep DB reads cohesive; **`select_related` / avoid N+1**; transactional patterns where delivery touches rows |
| **`python-design-patterns`** | **Single façade** from `delivery` → `reports` application layer — no scattering “sometimes stub, sometimes F6” |

Optional if you deepen jobs later: **`python-error-handling`**, **`python-type-safety`**, **`django-security`**.

---

## Mission (bounded)

Deliver a **verified “bridge”** between the **minimal public HTML path** (`backend/delivery/application/report_html.py` + `backend/delivery/interfaces/public_views.py`, CS-247 alignment) and the **canonical Epic 06/07 renderer**:

- **`reports.application.services.html_renderer.generate_report_html`**
- Optionally mirror Celery precedent: **`ContractAnalysis.objects.select_related("project")`** and pass **`GenerateReportOptions(project_name=...)`**

**Concrete exit criteria:**

1. **`generate_report_html_for_analysis`** resolves the same **`ContractAnalysis`** row it already validates (TTL / submission completeness), then calls **`generate_report_html`** instead of emitting stub HTML — **unless** analysis is deliberately not finalized (reuse existing guards; translate renderer exceptions ↔ HTTP cleanly).
2. Map renderer domain errors explicitly:
   - `AnalysisNotReadyError`, `AnalysisNotFoundError`, `AnalysisFailedError`, `VersionMissingError`, `TemplateNotFoundError`, etc. from [`reports.domain.errors`](../../backend/reports/domain/errors.py) → `ReportNotFound` / `AnalysisNotReady` **or** a **new** façade exception if 404 vs 422 vs 500 must differ **without leaking PII** in logs beyond `public_short_id` / opaque codes.
3. **Privacy**: never log HTML bodies; keep logging to byte length + timings + **`public_short_id`** only (`AGENTS.md` product lane).
4. **Tests**: extend or add Django tests proving **`GET /r/<id>/`** (or **`generate_report_html_for_analysis`** in isolation with DB fixtures) yields **substring / structural asserts** tied to **`reports`** templates — not the old stub headline — for a **`ContractAnalysis` with `score_total` set**.
5. **Performance**: prefetch **`project`** for template context (match [`reports/infrastructure/celery/report_tasks.py`](../../backend/reports/infrastructure/celery/report_tasks.py) pattern).

---

## Scope OUT (defer to Epic 09 or separate tickets unless trivial)

| Item | Reason |
|------|--------|
| **Epic 09 jobs** (`CS-270`–`CS-276`), anonymization corpus | Different epic owns F8 Part 2 |
| **Full CS-210 CI matrix** | Optional follow‑up (`docs/Roadmap/tickets/CS-210.md`): Playwright, forbid-list scanner, `<200 KB` nominal fixture gate |
| **`RubricVersion.categories`-driven section titles** vs static `section_builders` copy | Separate product decision unless AC explicitly demands parity with DB JSON |
| **CS-033 `38` vs `42` wording** | Doc/product reconciliation ticket — link from PR notes only |

---

## Roadmap hygiene (**after** CI green locally)

Following **`ticket-status-hygiene.mdc`** / **`epic-status-hygiene.mdc`** / **`AGENTS.md`**:

1. **`docs/Roadmap/EPIC-06-rubric-engine.md`** — Tick the **`[ ]` BR-16 public-link gap** line **only once** wired path is deployed + tests prove it (`[ ]` Known gap … `delivery.report_html` … CS-247).
2. Optionally refresh **`docs/Roadmap/tickets/CS-247.md`** body if AC narrative still says stub is acceptable vs now calling F6.
3. **`docs/Roadmap/EPIC-07-report-generation.md`** — confirm DoD bullets still truthful after routing change — **never** `[x]` without verification.

---

## Verification commands (**from `backend/`**)

```bash
poetry run ruff check <paths_you_touched>
# If broad edits:
poetry run ruff check .
poetry run black --check .
poetry run isort --check-only .
poetry run pytest tests/test_public_report_route.py -v --no-header -q
# widen scope if more tests touched:
# poetry run pytest tests/ -k "report or delivery or public_report" --no-header -q
```

Mirror **GitHub Actions** (`ci.yml` backend job expectations).

---

## Success statement (paste back when finishing)

Respond with:

- PR-sized summary (**why** TTL path now mirrors F6)
- Paths touched
- **Test matrix** bullets
- Confirmation **Epic 09 is unblocked structurally** (Epic **`depends_on`**: EPIC-01 ✓ EPIC-08 ✓ — no code change needed for that prerequisite)
- List **anything intentionally NOT done** (`CS-210` CI bullets, categorised JSON headings, CS-033 doc drift).

---

## Reference pointers (quick links)

| Doc / code | Why |
|-----------|-----|
| [`backend/delivery/application/report_html.py`](../../backend/delivery/application/report_html.py) | Delivery façade → `generate_report_html` (CS-247; no longer a stub) |
| [`backend/reports/application/services/html_renderer.py`](../../backend/reports/application/services/html_renderer.py) | Canonical entrypoint |
| [`backend/reports/domain/errors.py`](../../backend/reports/domain/errors.py) | Exception mapping vocabulary |
| [`docs/Roadmap/EPIC-06-rubric-engine.md`](../Roadmap/EPIC-06-rubric-engine.md) | BR-16 public-link item — wired (Epic **`done`**) |
| [`docs/Roadmap/tickets/CS-247.md`](../Roadmap/tickets/CS-247.md) | Scope wording vs behaviour |
| [`docs/Roadmap/EPIC-09-retention-privacy.md`](../Roadmap/EPIC-09-retention-privacy.md) | **Next** epic (`CS-270`–`CS-276`), **Phase 6** |

---

**End — paste everything from “Roles & attached skills” through “Reference pointers”.**
