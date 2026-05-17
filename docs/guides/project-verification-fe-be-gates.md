# Project verification — frontend / backend gate matrix (EPIC‑12 / CS‑356)

Operational reference for the optional `/verificacion-proyecto` surface and Django endpoints under `/api/v1/project-verification/`.

## Env contract — core gate

| Side | Variable | Default | Truthy tokens |
|---|---|---|---|
| Next.js (`frontend`) | `PROJECT_VERIFICATION_ENABLED` | Off when unset | `true`, `1`, `yes` (case-insensitive, trimmed); **any other non-empty string is treated as off** (safe rollout). |
| Django (`backend`) | `PROJECT_VERIFICATION_ENABLED` | Off when unset/`false` | Parsed by django-environ `env.bool(...)`: typical `True`/`yes`/`1` vs `False`/`0`/`no` (case-insensitive). Malformed booleans surface as Django startup/configuration errors instead of ambiguous half-states. |

Both sides should stay **paired**. A mismatch is louder than silently half-working — see behaviour matrix below.

## Env contract — resultado demo UX (frontend only)

| Variable | Purpose |
|---|---|
| `PROJECT_VERIFICATION_DEMO_LINKS` | Enables the “Ejemplos de bandas” resultado switchers **outside `NODE_ENV=development`**. In development the links stay on unless you intentionally override UX elsewhere. Values mirror the core gate tokens (`true`/`1`/`yes`). |

## Env contract — reputation readiness (backend)

| Variable | Notes |
|---|---|
| `PROJECT_REPUTATION_PROVIDER` | Normalizes to lowercase; `"none"` (default) skips outbound reputation. `"http"` is allow-listed SSRF guarded. Unknown providers fail `manage.py check` in production-shaped settings (`project_verification.E002`). |
| `PROJECT_REPUTATION_ADAPTER_READY` | Must be `true` before `"http"` is considered operator-approved; otherwise `manage.py check` fails (`project_verification.E001`). |
| `PROJECT_REPUTATION_HTTP_BASE_URL` | Base URL fragment for guarded HTTP lookups (paired with explicit allow-host parsing). |
| `PROJECT_REPUTATION_HTTP_ALLOW_HOSTS` | Comma-separated hostname allow-list (SSRFiltered). |
| `PROJECT_REPUTATION_HTTP_TIMEOUT_SECONDS` | Bounded client timeout for HTTP adapter. |

## Env contract — vision + synthesis knobs (backend)

| Variable | Notes |
|---|---|
| `PROJECT_VERIFICATION_VISION_MODEL` | Overrides the OpenRouter multimodal model for billboard extraction (falls back to `OPENROUTER_OCR_MODEL` when empty). |
| `PROJECT_VERIFICATION_VISION_TIMEOUT_SECONDS` | Bounding timeout for billboard vision calls (seconds). |
| `PROJECT_VERIFICATION_MAX_MEGAPIXELS` | Rejects billboard frames over the cap before invoking the vision model. |
| `PROJECT_VERIFICATION_LLM_SYNTH` | Optional narration-only branch (**default false**): never overrides deterministic bands/score. |

## Behaviour matrix — route + handler pairing

| Frontend gate | Backend gate | User-visible behaviour | Notes |
|---|---|---|---|
| On | On | Routes render (`/verificacion-proyecto/*`). OCR → manual handoff preserves structured prefills (`source=` query), manual POST flashes a short-lived **HTTP-only** verdict cookie (`/resultado`). | Pair with live `CASASEGURA_API_BASE_URL`. |
| Off | Off | Next returns **404** for `/verificacion-proyecto` (`not-found` segment). Django endpoints reply **403** with CS‑009 envelopes (`error_code: project_verification_disabled`). | Mirrors “nothing to see here” while probes stay deterministic. |
| On | Off | Hub renders, but uploads/manual POST/`demo-result` return **403** + `project_verification_disabled`; copy maps via `frontend/src/lib/backend-error-map.ts`. | Misconfigured rollout pairing — fix env before shipping UI. |
| Off | On | Next hides routes (404). Direct API curls/tests keep working. | Staged rehearsals without exposing UI. |

There is intentionally **no browser E2E** in CI for this epic; regressions freeze at **Vitest**, **pytest**, and Django `manage.py check`.

## Readiness probes — recommended before flipping prod

1. **`manage.py check` (backend)** — surfaces reputation misconfiguration (`project_verification` checks **E001/E002**) alongside global Django sanity.
2. **Paired booleans + base URL** — confirm `PROJECT_VERIFICATION_ENABLED`, `CASASEGURA_API_BASE_URL`, optional `PROJECT_VERIFICATION_*` vision keys, optional reputation keys.
3. **Spot POST smoke** — with both flags enabled, `POST /api/v1/project-verification/manual/` should return **`201`** and a JSON envelope including `reference_id`, `verdict`, `headline_key`, `rationale_keys`, and `echo` (never raw OCR text).

## Related code — pointers

- FE gate helper: [`frontend/src/lib/project-verification-env.ts`](../../../frontend/src/lib/project-verification-env.ts).
- Verdict cookie flash serialization: [`frontend/src/lib/project-verification-verdict-flash.ts`](../../../frontend/src/lib/project-verification-verdict-flash.ts) + server helpers in [`frontend/src/server/project-verification-verdict-flash-cookie.ts`](../../../frontend/src/server/project-verification-verdict-flash-cookie.ts).
- Django feature package: [`backend/project_verification/`](../../../backend/project_verification/).
- CS‑009 handler: [`backend/config/exception_handler.py`](../../../backend/config/exception_handler.py).
