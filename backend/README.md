# Backend (Django 5.2 + DRF)

The Casa Segura API and async pipeline. Layered DDD per
[`docs/analysis/_shared/GLOBAL_ASSUMPTIONS.md`](../docs/analysis/_shared/GLOBAL_ASSUMPTIONS.md)
§1. See ADRs [0001](../docs/adr/ADR-0001-django-backend-stack.md) ·
[0002](../docs/adr/ADR-0002-rename-platform-module-to-platform_core.md) ·
[0003](../docs/adr/ADR-0003-cs031-project-name-normalization-divergence.md) ·
[0004](../docs/adr/ADR-0004-versioning.md).

## Layout

```
backend/
├── config/          Django project settings, root URLs, exception handler
├── common/          Custom User model, permissions, auth backend (skill default)
├── shared/          Repository system, observability, domain exceptions, utils
├── platform_core/   F8 — Project, ContractAnalysis, retention, audit
├── ingestion/       F1 — ContractSubmission, OcrJob (transient)
├── classification/  F2 — (models land with feature)
├── corpus/          F3 — LegalDocument, LegalChunk (vector 384), CorpusVersion
├── rubric/          F4 — RubricVersion, Criterion (catalog)
├── economics/       F5 — BenchmarkVersion, EconomicBenchmark
├── reports/         F6 — (models land with feature)
├── delivery/        F7 — DeliveryRequest
└── tests/           factory_boy factories + smoke
```

Every module follows `domain/` (Pydantic), `application/`, `infrastructure/django/`,
`infrastructure/celery/` layout.

## Quick start

```bash
# 1. Local services (Postgres+pgvector, Redis) from repo root:
docker compose -f ../docker-compose.dev.yml up -d

# 2. Install deps + run migrations + seed catalogs + start dev server:
make install
make migrate
make seed-rubric
make seed-corpus
make runserver
```

## Make recipes (CS-021)

`make help` lists everything. Most-used:

| Command | Purpose |
|---|---|
| `make migrate` | Apply pending migrations |
| `make makemigrations` | Generate migrations from model changes |
| `make migrations-check` | Fail if model changes aren't captured (CI lane) |
| `make rollback APP=ingestion TO=0001_initial` | Roll back a single app to a specific migration |
| `make fresh-db` | **DANGER**: drop + recreate `casasegura` DB, install extensions, migrate. Local only. |
| `make check` | `manage.py check` + `check --deploy` |
| `make format` | black + isort |
| `make lint` | ruff |
| `make type-check` | mypy |
| `make test` | pytest (whole suite) |
| `make seed-rubric` | Idempotent `seed_rubric_version --activate` |
| `make seed-corpus` | Idempotent `seed_corpus_version --activate` |
| `make runserver` | Django dev server on :8000 |
| `make celery-worker` / `make celery-beat` | Async runtime |
| `make dev-up` / `make dev-down` / `make dev-logs` | Wrapper around `docker compose -f ../docker-compose.dev.yml ...` |

## Database

PostgreSQL 16 + pgvector (matches `pgvector/pgvector:pg16` in the dev
compose). Required extensions, created automatically by the compose init
SQL: `vector`, `pgcrypto`, `uuid-ossp`.

**Naming convention** for the schema:

| Concern | Rule |
|---|---|
| Table names | `snake_case`, singular (`project`, `contract_analysis`, `legal_chunk`) |
| Column names | `snake_case` |
| FK column names | `<referenced_table>_id` for synthetic PKs; `<column>` when the referenced PK is a string (e.g. `rubric_version`) |
| Index names | `idx_<table_or_short>_<purpose>`, ≤ 30 chars (Django limit) |
| Unique constraint names | `uq_<scope>_<purpose>` |
| Check constraint names | `ck_<table>_<purpose>` or domain-specific like `ca_score_range` |
| Trigger names | `<table>_<purpose>` (e.g. `corpus_version_immutable`) |

**Migration policy** (CS-010 / CS-021):

- One migration per logical unit. RunSQL only when ORM-native is awkward
  (composite FKs, triggers, views).
- Per-module migrations live under `<module>/infrastructure/django/migrations/`
  per `MIGRATION_MODULES` in `config/settings.py`.
- Catalog rows are immutable after publication; the
  `reject_catalog_mutation` trigger enforces it on the three versioned
  catalogs.
- For rollback during local dev: `make rollback APP=<module> TO=<migration_name>`.
- For a clean slate during local dev: `make fresh-db`.

## Environment

Copy `.env.example` to `.env` and fill in secrets. `backend/.env` is
gitignored. Variables consumed by `config/settings.py` via `django-environ`.

### Python interpreter

[`pyproject.toml`](pyproject.toml) allows **`>=3.11,<4.0`**. **GitHub Actions uses Python 3.11.** **`.python-version`** is only a convenience pin for pyenv-local dev — use **3.11.x** for parity with CI, or another supported **3.12.x / 3.13.x** version.

Do **not** use **Python 3.14+** yet for `make install`: dependency **`tiktoken`** builds native code via PyO3, whose bundled PyO3 only supports Python through **3.13** today (install fails with “newer than PyO3's maximum”). Use **pyenv**:

```bash
pyenv install 3.11.11   # or any installed 3.11.x / 3.12.x / 3.13.x
cd backend && pyenv local 3.11.11 && python3 --version
poetry env remove --all && poetry env use "$(command -v python3)" && make install
```

Rust is unnecessary when a **manylinux/macOS wheel** exists for your Python (typical on **3.11–3.13**).

## Tests

`pytest-django` with transactional rollback per test. Factories live in
`tests/factories.py`; helpers `random_vector_384`, `make_public_short_id`,
`age_to`, `expire_in`. Run with `make test`. CI runs the same suite against
`pgvector/pgvector:pg16` + `redis:7-alpine` services (see
[`.github/workflows/ci.yml`](../.github/workflows/ci.yml)).
