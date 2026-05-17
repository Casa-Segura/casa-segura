# Backend completion prompt — EPIC-06 (BVA / property tests) + EPIC-08 (multi-channel delivery)

Paste everything below the line into a **new Cursor chat** (Agent mode). Repo root: **`casa-segura`**, canonical backend: **`backend/`** (Django 5.2 LTS, DRF, Pydantic v2, Celery on Redis).

---

## Your mission

1. **Finish EPIC-06** — implement and verify **CS-167, CS-168, CS-169, CS-170, CS-171** (rubric boundary-value and property-based tests).  
2. **Finish EPIC-08** — bring **multi-channel delivery** to “done” for **all open delivery tickets**: **CS-230 through CS-248** plus **CS-357** (20 tickets total). Reconcile with any **already-started code** under `backend/delivery/`, `backend/config/` (Celery, settings, URLs), `docs/adr/ADR-0006-delivery-celery-zavu.md`, and related tests — do not duplicate; **complete and wire** what exists, **fill gaps**, and **align ticket acceptance criteria**.

After each ticket’s acceptance criteria are **implemented and verified**, update that ticket’s frontmatter in `docs/Roadmap/tickets/CS-*.md` per **`AGENTS.md`**: `status`, checked AC boxes, and the owning **`docs/Roadmap/EPIC-06-rubric-engine.md`** / **`docs/Roadmap/EPIC-08-multichannel-delivery.md`** definition-of-done bullets where applicable (`epic-status-hygiene.mdc`).

---

## Non-negotiables (read first)

- **Roadmap truth:** `docs/Roadmap/tickets/CS-*.md` is authoritative for scope and **`depends_on`**. Respect dependencies; if you must implement out of order, document the assumption in PR notes.
- **Privacy:** Do not log PII — OCR payloads, delivery targets (`to:` email/phone), report bodies, webhook payloads beyond opaque IDs, or raw provider errors with destinations. Hash targets per product rules; follow existing patterns in the delivery app.
- **Quality bar:** Match existing **`backend/`** style — typing on public APIs, Pydantic for domain DTOs, thin Django views, logic in application services. Run **`make test`** (or targeted pytest) from **`backend/`** before claiming work complete.

---

## Python & Django engineering standards (apply throughout)

**Python**

- Prefer **explicit type hints** on public functions and service boundaries; use **`X | None`** over `Optional`; narrow types after guards.
- Keep **I/O at edges** (HTTP, Celery tasks, ORM) and **pure functions** for scoring, rounding, and message composition where possible.
- Use **small, composable modules**; avoid duplicating rubric or delivery logic across layers.
- **Tests:** `pytest`, `parametrize` for tables, **`hypothesis`** where CS-171 requires property tests; mark slow suites if needed (`@pytest.mark.slow`) per ticket notes.

**Django / DRF**

- **Models:** migrations for schema changes; no raw SQL unless project already does; respect existing app boundaries (`rubric`, `delivery`, `ingestion`, etc.).
- **APIs:** DRF serializers/views consistent with project patterns; validate inputs strictly; return stable error shapes without leaking internals.
- **Celery:** tasks idempotent where possible; explicit retry/dead-letter behavior per **CS-234** / ADR-0006; safe logging (no secrets, no raw destinations).
- **Security:** CSRF/session rules per existing public vs authenticated routes; verify webhook **HMAC** / signature patterns for Zavu per project ADR and tickets.

**Discovery before coding**

- Locate real symbols (e.g. band helpers, B1/B2 scorers, override orchestration) — do **not** assume names from tickets if the codebase differs; **import the single source of truth** referenced by CS-156 / CS-152 / CS-157 as appropriate.

---

## Part A — EPIC-06 tickets (QA / rubric)

Implement fully per each file under `docs/Roadmap/tickets/`:

| Ticket | Title (summary) |
|--------|-----------------|
| **CS-167** | BVA: score **band** boundaries (`band_from_total` or equivalent — see CS-156); table 0.0–10.0; floating round-trip 7.949999 vs 7.950000 per **CS-152** rounding policy; isolate from overrides. |
| **CS-168** | BVA: **B2** EAR ladder vs benchmark fixture (**9%** nominal); unverifiable / non-EAR path → score **4** + `Art. 19 lit. j`; document closed-boundary convention in tests. |
| **CS-169** | BVA: **B1** down-payment ladder + **asymmetric** clamp (**CS-153**); mirror pair 8% vs 10%; edges 9.99/10.00, fraud-pattern → 0. |
| **CS-170** | BVA: **eleven overrides** — golden **positive** + **near-miss negative** Spanish fixtures under `tests/fixtures/overrides/*.txt`; assert orchestration **0 / red** / `override_triggered` per CS-157; matrix in ticket. |
| **CS-171** | **Hypothesis** property: asymmetric monotonicity invariant for **B1/B2/B4** (+ optional term) after clamp; **≥200** iterations PR smoke, **≥2000** documented for nightly; exclude invalid F5 ranges; structured counterexample on failure. |

**Out of scope** (per tickets): hex color assertions; full monthly→annual formula tests (CS-131); percent extraction accuracy (EPIC-04); LLM fuzzing.

---

## Part B — EPIC-08 tickets (delivery)

Complete per `docs/Roadmap/tickets/` — **depends_on** chains matter (e.g. **CS-357** depends on **CS-237**).

| Ticket | Title (summary) |
|--------|-----------------|
| **CS-230** | Delivery Pydantic schemas & enums |
| **CS-231** | Channel-agnostic delivery dispatcher |
| **CS-232** | Hashed targets + encrypted payloads; post-delivery erasure |
| **CS-233** | Celery delivery worker queue |
| **CS-234** | Retry / backoff / dead-letter |
| **CS-235** | Email transport (Zavu primary) |
| **CS-236** | Spanish transactional email + PDF attachment |
| **CS-237** | Email delivery worker E2E |
| **CS-238** | SMS provider client |
| **CS-239** | SMS message registry |
| **CS-240** | SMS summary composer (Spanish “tú”) |
| **CS-241** | SMS handler + rate limiting |
| **CS-242** | SMS provider callback (if applicable) |
| **CS-243** | Normalize provider errors for retries |
| **CS-244** | SMS secrets via CS-006 baseline |
| **CS-245** | Public report route + TTL + anti-caching |
| **CS-246** | Expired-link friendly response |
| **CS-247** | On-demand report regeneration port (no persistence per BR-01) |
| **CS-248** | Resend endpoint + hash verification + cap |
| **CS-357** | **Ready** — reconcile Zavu webhooks with `DeliveryRequest` via `provider_message_id` |

**Integration note:** EPIC-08 officially consumes **EPIC-07** output (HTML/PDF). Until EPIC-07 lands, keep a **clear port/stub** boundary (e.g. stub PDF) so transport stays testable — but wire the real call path when **`ContractAnalysis`** / report builder hooks exist.

---

## Verification checklist

From **`backend/`**:

```bash
make test
# or faster iteration, e.g.:
# uv run pytest tests/test_<name>.py -v
```

Ensure **CI-relevant** linters/type checks the repo already runs still pass (see `.github/workflows/ci.yml` if unsure).

---

## Done means

- All AC boxes for **CS-167–171** and **CS-230–248, CS-357** are satisfied and marked **`[x]`** only when verified.  
- Ticket **`status: done`** (or repo-standard terminal state) updated for each.  
- Epic files **`EPIC-06`**, **`EPIC-08`** updated so Definition of done matches shipped reality.  
- No secrets committed; **`.env.example`** / docs updated if new env vars are required (**CS-244**, webhooks, etc.).

Start by reading **`AGENTS.md`**, the listed **`CS-*.md`** tickets, **`ADR-0001`**, **`ADR-0006`**, and scanning **`backend/delivery/`** + **`backend/rubric/`** for current implementation state.
