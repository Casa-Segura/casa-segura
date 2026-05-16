# Casa Segura — Railway deployment

This is the concrete, code-aligned setup guide. It supersedes the generic
Railway guide draft for any conflict — the values below match what
`backend/config/settings.py`, `backend/Dockerfile.*`, and
`backend/railway.toml` actually expect.

> Frontend (Next.js) is deployed to Vercel, not Railway. Not covered here.

---

## 1. What gets deployed

One Railway project containing four services, all from this monorepo:

| Service | What it runs | Source | Build target |
|---|---|---|---|
| `web` | Django + DRF (Gunicorn) | `/backend` | Dockerfile target `web` |
| `worker` | Celery worker (OCR-capable) | `/backend` | Dockerfile target `worker` |
| `beat` | Celery beat scheduler | `/backend` | Dockerfile target `beat` |
| `postgres` | Postgres 15 + pgvector | Railway plugin (custom image, see §3) | — |
| `redis` | Redis (Celery broker) | Railway plugin | — |

The `web`/`worker`/`beat` services share the same `/backend` Root
Directory and the same `Dockerfile`, switching behaviour via the
Dockerfile target plus an overridden `startCommand`.

---

## 2. Create the project

1. Railway dashboard → **New Project** → **Deploy from GitHub repo** →
   select the `casa-segura` repo.
2. When Railway offers to auto-deploy, **cancel**. We add each service
   manually so the Root Directory + Dockerfile target are set from the
   start (auto-deploy will pick the wrong build).
3. Name the project `casa-segura` (or `casa-segura-staging`).

---

## 3. Postgres with pgvector

Casa Segura's schema requires pgvector (CS-026 `legal_chunk.embedding`,
CS-030 HNSW index) plus `pgcrypto` and `uuid-ossp`.

### 3.A (Recommended) Railway's default Postgres

**Confirmed 2026-05-16:** Railway's default Postgres image bundles
pgvector. Use it as-is — do NOT swap the Source Image to
`pgvector/pgvector:*` on a service that already has a volume (see §3.C
for why).

1. **+ New** → **Database** → **Add PostgreSQL**. Leave the image alone.
2. Wait for the deploy to go green.
3. Open the **Data** tab and run:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   CREATE EXTENSION IF NOT EXISTS pgcrypto;
   CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

   SELECT extname, extversion FROM pg_extension
   WHERE extname IN ('vector', 'pgcrypto', 'uuid-ossp');
   ```
   Expect three rows. If `vector` is missing with "extension not
   available", Railway has rolled back the bundle — fall through to §3.B.
4. On `web` / `worker` / `beat` → **Variables** → set
   `DATABASE_URL = ${{Postgres.DATABASE_URL}}` (reference variable —
   autocompleted by Railway).

### 3.B Fallback: external Postgres on Neon

Use this when Railway's default image doesn't ship pgvector (or when you
hit a crash loop like §3.C and want to bail).

1. Create a project at https://neon.tech (free tier is plenty for dev /
   staging). Pick the region nearest your Railway services.
2. Copy the connection string. Format:
   `postgres://user:password@ep-xxx-xxx.region.neon.tech/dbname?sslmode=require`
3. On each Casa Segura service in Railway (`web`, `worker`, `beat`) →
   **Variables** → set `DATABASE_URL` to that string. **Plain text** (not
   a reference variable — Neon isn't a Railway plugin).
4. Delete any half-broken Railway Postgres service.
5. Verify the three extensions in Neon's SQL Editor as in §3.A step 3.

### 3.C If you already broke Postgres by image-swapping

Symptom in logs (repeats every restart):

```
PostgreSQL Database directory appears to contain a database; Skipping initialization
FATAL: configuration file ".../postgresql.conf" contains errors
LOG: unrecognized configuration parameter "autovacuum_worker_slots"
```

Cause: Railway's default Postgres ships with pre-release GUCs (e.g.
`autovacuum_worker_slots`, a PG 19 dev parameter) that older
`pgvector/pgvector:pgNN` images don't recognize. Once the volume was
initialized by Railway's image, no stable pgvector image can read it.

**Do NOT** try to edit `postgresql.conf` in the volume (Railway's own
suggestion) — even if the service comes up, the next image bump will
break it again. Instead:

1. Delete the broken Postgres service entirely (not just the volume).
2. Either:
   - Restart from §3.A with Railway's default image (now known to bundle
     pgvector), **without** touching the Source Image field, OR
   - Move to Neon per §3.B.

---

## 4. Redis

1. **+ New** → **Database** → **Add Redis**.
2. No extra config. Railway exposes `REDIS_URL` on the service.

---

## 5. The three Django services

For each of `web`, `worker`, `beat`:

1. **+ New** → **GitHub Repo** → same repo.
2. Service **Settings**:
   - **Source → Root Directory**: `/backend` (with leading slash, no
     trailing slash — typing `backend/` or `backend` will subtly break
     railpack autodetection and you'll see
     `directory .../snapshot-target-unpack/backend does not exist`).
   - **Source → Watch Paths**: `/backend/**`
   - **Build → Builder**: **`Dockerfile`** (set this **explicitly** in
     the dashboard — railpack, Railway's new default, can ignore the
     `[build].builder = "DOCKERFILE"` line in `railway.toml` and
     autodetect Python instead, which fails on the monorepo layout).
   - **Build → Dockerfile Path**: see table below (one Dockerfile per
     service; do not leave blank — the default `Dockerfile` no longer
     exists).
   - **Deploy → Start Command**: see table below (overrides
     `railway.toml`).
   - **Deploy → Healthcheck Path**: `/api/health/` (web only; blank for
     worker/beat).

| Service | Dockerfile Path | Start Command |
|---|---|---|
| `web` | `Dockerfile.web` *(default from `railway.toml`)* | `sh -c 'gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --access-logfile -'` |
| `worker` | `Dockerfile.worker` | `celery -A shared.infrastructure.celery worker -l INFO --concurrency=2` |
| `beat` | `Dockerfile.beat` | `celery -A shared.infrastructure.celery beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler` |

> **Why one Dockerfile per service.** Railway's dashboard does not expose
> `--target` for multi-stage builds reliably, so each process ships its own
> `backend/Dockerfile.<service>`. The three files share identical `base` +
> `runtime-base` stages (edits to those stages must be mirrored across all
> three). The `worker` image adds Tesseract + Poppler + libheif for OCR;
> `web` and `beat` skip those layers for a smaller image.

> **Why `web` needs `preDeployCommand`.** `railway.toml` runs
> `python manage.py migrate && collectstatic` before traffic shifts.
> Migrations are idempotent so running them on every deploy is safe. The
> `worker` and `beat` services do **not** need it (they don't serve HTTP
> and don't own the schema), and Railway only runs `preDeployCommand` on
> the service that owns the deploy. If you want extra safety, keep
> `preDeployCommand` only on `web` and clear it from worker/beat in their
> dashboard.

> **Domain only on `web`.** Settings → Networking → Generate Domain
> only for the `web` service. Worker and beat are private.

---

## 6. Environment variables

Set these on **all three** Django services (`web`, `worker`, `beat`)
unless noted. Use Railway **reference variables** for `DATABASE_URL` and
`CELERY_BROKER_URL` so they auto-update if the DB/Redis service is
replaced — type `${{` in the value field and Railway autocompletes.

| Variable | Value | Notes |
|---|---|---|
| `SECRET_KEY` | random 50-char string | Generate per environment; never reuse |
| `DEBUG` | `False` | Production only |
| `ALLOWED_HOSTS` | comma-separated hostnames | The Railway `*.up.railway.app` host is added automatically by `settings.py` via `RAILWAY_PUBLIC_DOMAIN`; only set this if you have additional custom hosts |
| `LOG_LEVEL` | `INFO` | `DEBUG` only for short troubleshooting |
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` | Reference variable. Overrides discrete `DB_*` knobs |
| `CELERY_BROKER_URL` | `${{Redis.REDIS_URL}}` | Reference variable |
| `CELERY_RESULT_BACKEND` | `${{Redis.REDIS_URL}}` | Reference variable |
| `OPENROUTER_API_KEY` | `sk-or-v1-...` | Secret; from OpenRouter dashboard |
| `OPENROUTER_OCR_MODEL` | `mistralai/pixtral-large-2411` | Or whatever model the current EPIC-02 plan locks |
| `OPENROUTER_PDF_PLUGIN_ENGINE` | `mistral-ocr` | |
| `OPENROUTER_DEFAULT_TEXT_MODEL` | `mistralai/pixtral-large-2411` | |
| `OPENROUTER_HTTP_REFERER` | `https://<web>.up.railway.app` | Set after `web` has a domain |
| `OPENROUTER_X_TITLE` | `Casa Segura` | |
| `ZAVU_API_KEY` | secret | If integration is live |
| `ZAVU_WEBHOOK_SECRET` | secret | For verifying inbound WhatsApp |
| `INTERNAL_AUTH_SECRET` | random 50-char string | |
| `KMS_PROVIDER` | `local` | Until KMS epic ships |
| `ACTIVE_RUBRIC_VERSION` | `1.0.0` | The seeded value from CS-033 |
| `ACTIVE_CORPUSF_VERSION` | `<date>` | Note: settings.py also accepts `ACTIVE_CORPUS_VERSION`; current env honours the legacy typo first |
| `CSRF_TRUSTED_ORIGINS` | `https://<custom-domain>` | Optional — only if you front the API with a custom domain |

Variables that should **NOT** be set on Railway (they're for local dev
only): `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`,
`DB_ENGINE`. When `DATABASE_URL` is present, settings.py ignores them.

---

## 7. Initial deploy + verification

After all three services + Postgres + Redis are wired:

1. Trigger a deploy on `web`. Watch logs for:
   - `Operations to perform: Apply all migrations…` (preDeploy step)
   - `xxx static files copied to '/app/staticfiles'`
   - `Listening at: http://0.0.0.0:$PORT (gunicorn)`
2. `curl https://<web-domain>/api/health/` → expect 200 with the
   standard health envelope.
3. `curl https://<web-domain>/api/ready/` → expect 200 if DB + Redis are
   reachable; 503 with reason codes otherwise (CS-008 behaviour).
4. Trigger a deploy on `worker`. Logs should show
   `celery@... ready` within ~20s.
5. Trigger a deploy on `beat`. Logs should show
   `beat: Starting...` (only one beat instance — never scale to >1).

---

## 8. Things this guide deliberately skips

- **PR preview environments.** Not configured.
- **Custom domain / SSL.** Railway gives `*.up.railway.app` by default.
- **Backups.** Default daily snapshots; revisit before real user data.
- **Zavu webhook URL configuration on Zavu's side.** Once `web` has a
  domain, hand that URL to whoever owns the Zavu integration.
- **Frontend on Vercel.** Separate doc (TBD).

---

## 9. Files involved (for code review)

- `backend/railway.toml` — Build config + `web` defaults + preDeploy.
- `backend/Dockerfile.web` / `Dockerfile.worker` / `Dockerfile.beat` —
  One image per process. Stages `base` and `runtime-base` are shared
  byte-for-byte across the three files.
- `backend/config/settings.py` — `DATABASE_URL` parsing,
  `RAILWAY_PUBLIC_DOMAIN` auto-host, WhiteNoise, `SECURE_PROXY_SSL_HEADER`.
- `backend/.env.example` — Documents Railway-only env vars in its tail
  section (commented; not meant for local `.env`).
