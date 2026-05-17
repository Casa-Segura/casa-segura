# Project verification — frontend / backend gate matrix (EPIC‑12 / CS‑356)

Operational reference for the optional `/verificacion-proyecto` surface and Django stubs under `/api/v1/project-verification/`.

## Env contract

| Side | Variable | Default | Truthy tokens |
|---|---|---|---|
| Next.js (`frontend`) | `PROJECT_VERIFICATION_ENABLED` | Off when unset | `true`, `1`, `yes` (case-insensitive, trimmed); **any other non-empty string is treated as off** (safe rollout). |
| Django (`backend`) | `PROJECT_VERIFICATION_ENABLED` | Off when unset/`false` | Parsed by django-environ `env.bool(...)`: typical `True`/`yes`/`1` vs `False`/`0`/`no` (case-insensitive). Malformed booleans surface as Django startup/configuration errors instead of ambiguous half-states. |

## Behaviour matrix

| Frontend gate | Backend gate | User-visible behaviour | Notes |
|---|---|---|---|
| On | On | Routes render (dynamic segment). Manual/billboard server actions POST to stubs; resultado may fetch `demo-result`; errors use CS‑009 envelopes. | Default dev iteration posture when both `.env` files opt in. |
| Off | Off | Next returns **404** for the `/verificacion-proyecto` segment (`not-found` copy). Django endpoints still exist but reply **403** with `error_code: project_verification_disabled`. | Mirrors “nothing to see here” for optional flow while preserving deterministic API probes. |
| On | Off | Hub renders, but POST/GET calls to `CASASEGURA_API_BASE_URL` yield **403** + `project_verification_disabled`; error copy maps via `frontend/src/lib/backend-error-map.ts`. | Deliberately loud — indicates misconfigured deployment pairing. Regression coverage: Django tests with flag off (`backend/tests/test_project_verification_stubs.py`). |
| Off | On | Next hides routes (404 segment). Direct API callers can still exercise stubs via curl/integration tests. | Intentionally rare; used for staged API rehearsals without exposing UI. |

## Related code

- FE gate helper: [`frontend/src/lib/project-verification-env.ts`](../../../frontend/src/lib/project-verification-env.ts).
- Django stubs: [`backend/project_verification/interfaces/api/](../../../backend/project_verification/interfaces/api/).
- CS‑009 handler: [`backend/config/exception_handler.py`](../../../backend/config/exception_handler.py).
