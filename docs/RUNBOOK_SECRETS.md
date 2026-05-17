# Casa Segura — Secrets rotation runbook (CS-334)

**Last reviewed:** 2026-05-17
**Owners:** see *Custodian* column per row.
**Related:** [SECURITY.md](../SECURITY.md), [CS-333 TLS](Roadmap/tickets/CS-333.md), [CS-332 error tracking](Roadmap/tickets/CS-332.md).

This runbook lists every operational secret the Casa Segura backend consumes, the
custodian, the recommended rotation cadence, and the rollback / incident-response
steps. The deploy gate in `config/settings.py` (CS-333 validator) refuses to boot
when production-only knobs are missing, so a stale or absent secret surfaces at
container start rather than during traffic.

## Conventions

- **Cadence** is the *minimum* — rotate sooner on suspected leak or personnel change.
- **Dual-write window** = the time both old and new credentials are accepted by the
  upstream before the old key is revoked. Default **24h** unless noted; longer windows
  needed only when external providers throttle key generation.
- **Blast radius** describes what an attacker with the secret could read/write.
- Never commit live values. Reference the secret manager (Railway dashboard, Vault,
  or `.env.production` outside git) — `.env.example` documents shape only.
- Never echo secrets in CI logs. Rotation scripts must read the new value from STDIN
  or a referenced file (`--from-file`), not as a CLI argument.

---

## 1. Application core

| Env var | Custodian | Cadence | Blast radius | Notes |
|---|---|---|---|---|
| `SECRET_KEY` | Backend lead | 180 d | Session forgery, password reset tokens | Rotate via `python -c "import secrets; print(secrets.token_urlsafe(64))"`. After rotation all logged-in users (admin only — public users are unauthenticated) must re-login. |
| `INTERNAL_API_TOKEN` | Backend lead | 90 d | `/api/v1/internal/*` QA endpoints (classification eval) | Dual-write window 24h: set both `INTERNAL_API_TOKEN` and `INTERNAL_API_TOKEN_PREV` in env, then drop the previous after rollouts confirm the new value. |
| `FEEDBACK_HASH_SALT` | Backend lead | Yearly (or on suspected leak) | Re-identification of IP / contact-email hashes in `user_error_report` | Rotation invalidates dedupe windows; document in incident timeline. |

## 2. Database & infrastructure

| Env var | Custodian | Cadence | Blast radius | Notes |
|---|---|---|---|---|
| `DATABASE_URL` / `DB_PASSWORD` | Infra on-call | 180 d, or on personnel change | Full DB read/write | Rotate via Railway → Postgres → "Reset password" → update env → roll restart. Connection-pool drain: deploy → wait for `CONN_MAX_AGE` (60s) → kill old workers. Document timing in the incident ticket. |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` (Redis URL) | Infra on-call | 180 d | Task queue replay, denial of service | Same Railway flow as Postgres. Drain workers via `celery -A config control shutdown` before flipping. |
| `RAILWAY_PUBLIC_DOMAIN` | Infra on-call | On environment migration | Routing / CSRF trust origin | Update in lockstep with DNS. |

## 3. LLM / model providers

| Env var | Custodian | Cadence | Blast radius | Notes |
|---|---|---|---|---|
| `OPENROUTER_API_KEY` | Backend lead | 90 d, or quarterly billing review | LLM call quota burn, cost spike | OpenRouter supports key labels — issue a new key, deploy, then revoke the old one after 24h. |
| `OPENROUTER_BASE_URL` | Backend lead | On provider change only | Routing | TLS-only enforced by CS-333 validator. |

## 4. Delivery providers (F7 / EPIC-08)

| Env var | Custodian | Cadence | Blast radius | Notes |
|---|---|---|---|---|
| `ZAVUDEV_API_KEY` (or `ZAVU_API_KEY`) | Delivery lead | 90 d | Outbound email / SMS spoofing as Casa Segura | Zavu dashboard → API keys → rotate. Dual-write 12h. |
| `ZAVU_WEBHOOK_SECRET` | Delivery lead | 90 d | Inbound webhook forgery | After rotating, re-register the webhook endpoint with the new HMAC secret. |
| `ZAVU_SENDER_ID` | Delivery lead | On product change only | Sender identification | Coordinate with the carrier/email approval window. |
| `SMS_API_KEY` / `SMS_WEBHOOK_SECRET` | Delivery lead | 90 d | Same as Zavu, alt provider | Mirror the Zavu cadence. |
| `DELIVERY_TARGET_HASH_SALT` | Backend lead | Yearly, or on suspected leak | Re-identification of `delivery_target_hash` rows | Rotation invalidates resend dedupe; coordinate with retention job (EPIC-09). |

## 5. Observability

| Env var | Custodian | Cadence | Blast radius | Notes |
|---|---|---|---|---|
| `ERROR_TRACKING_DSN` | Infra on-call | 180 d | Sentry quota burn, event-source spoof | Sentry dashboard → project → Client Keys → rotate DSN. Keep both DSNs valid 24h. |
| `ERROR_TRACKING_ENABLED` | Backend lead | N/A (feature flag) | Toggles SDK | When `false`, SDK never opens a network connection (CS-332 AC). |
| `DEPLOY_RELEASE` / `DEPLOY_STAGE` | CI/CD | Per deploy | Tag scope | Set automatically by CI from git SHA + target environment. |

## 6. Active catalog versions

These are *not* secrets but are listed for the same audit cadence — drifting versions silently break BR-16 reproducibility.

| Env var | Custodian | Cadence | Notes |
|---|---|---|---|
| `ACTIVE_RUBRIC_VERSION` | Product / Rubric lead | Per rubric release | Must match an immutable `RubricVersion` row. |
| `ACTIVE_CORPUS_VERSION` | Product / Corpus lead | Per corpus release | Tracks the legal corpus snapshot. |
| `ACTIVE_BENCHMARK_VERSION` | Product / Economics lead | Quarterly | Tied to the BCR / ABANSA refresh cycle. |

## 7. Incident response — suspected leak

1. **Triage** — open an incident ticket with severity, suspected secret, suspected window.
2. **Revoke** — invalidate the leaked credential at the provider before generating a replacement.
3. **Replace** — generate the new value, paste into the secret manager, redeploy.
4. **Audit** — run `SELECT count(*) FROM <relevant table> WHERE created_at > <leak window start>` for any tables touched by that credential.
5. **Communicate** — if any production user data was exposed, notify per [SECURITY.md](../SECURITY.md) disclosure path.
6. **Post-mortem** — root cause, detection delta, remediation. Capture as ADR if process change required.

## 8. Deploy gate checklist (run before promoting a build to production)

- [ ] `DEPLOY_STAGE=production` set.
- [ ] `SECRET_KEY` is **not** the `django-insecure-...` default.
- [ ] `DATABASE_URL` resolves to a managed Postgres instance (not loopback).
- [ ] `OPENROUTER_API_KEY`, `ZAVUDEV_API_KEY`, `ZAVU_WEBHOOK_SECRET` all set.
- [ ] `DELIVERY_TARGET_HASH_SALT` is not the dev default.
- [ ] `ERROR_TRACKING_DSN` set (or `ERROR_TRACKING_ENABLED=false` deliberately).
- [ ] All env URLs in `OPENROUTER_BASE_URL`, `ZAVU_API_BASE_URL`, `SMS_PROVIDER_BASE_URL`, `PUBLIC_REPORT_BASE_URL` are `https://`.
- [ ] `ALLOW_INSECURE_TLS_DEV_ONLY` is **unset** or `false`.

Settings validates the second-to-last bullet at boot (`shared/security/tls.py:validate_tls_posture`); the rest are operator checks.

## 9. Key scope — environment isolation

- Staging and production credentials are **never** shared. The CS-334 acceptance criterion explicitly forbids cross-env reuse of DSNs.
- Local development uses the `.env` template (`backend/.env.example`) with throwaway placeholders. The TLS validator allows cleartext only when `ALLOW_INSECURE_TLS_DEV_ONLY=true` *and* `DEPLOY_STAGE` is not in the production set.

---

*Update this file in lockstep with `config/settings.py` env declarations and the CS-334 ticket.*
