---
project: Casa Segura
doc_type: setup_checklist
phase: 1
last_updated: 2026-05-15
tags:
  - casa-segura
  - roadmap
  - phase-1
  - setup
---

# Phase 1 — configuration checklist (Fase F deliverable)

This is the **single list** of manual configuration you (the operator)
need to apply on top of the code that landed in this Phase 1 pass.
Everything below is `.env` / OS-level / one-shot CLI — no further coding.

## 1. `backend/.env`

Copy `backend/.env.example` to `backend/.env` and fill in:

| Key | What to put |
|---|---|
| `SECRET_KEY` | 50-char random string. `python -c "import secrets; print(secrets.token_urlsafe(48))"` works. |
| `DB_PASSWORD` | Must match `docker-compose.dev.yml` Postgres password. |
| `OPENROUTER_API_KEY` | Your `sk-or-v1-…` key. **Required** for CS-054 (image + scanned-PDF OCR). |
| `OPENROUTER_OCR_MODEL` | Leave as `mistralai/pixtral-large-2411` (validated). |
| `OPENROUTER_PDF_PLUGIN_ENGINE` | Leave as `mistral-ocr`. |
| `OPENROUTER_DEFAULT_TEXT_MODEL` | Leave as `mistralai/pixtral-large-2411` for Phase 1 (separate text model decision deferred). |
| `OPENROUTER_HTTP_REFERER`, `OPENROUTER_X_TITLE` | Already filled with sensible defaults; adjust if you want them in the OpenRouter dashboard. |
| `ZAVU_API_KEY`, `ZAVU_WEBHOOK_SECRET`, `ZAVU_BASE_URL` | Phase 2. Leave placeholder values for now. |
| `KMS_KEY_ID`, `INTERNAL_AUTH_SECRET` | Generate or leave defaults — not exercised by Phase 1 flows. |
| `ACTIVE_RUBRIC_VERSION` | Set to `1.0.0` after running `seed_rubric_version --activate`. |
| `ACTIVE_CORPUSF_VERSION` | Set to the date tag you pass to `ingest_corpus`, e.g. `2026-05-15`. The typo (`CORPUSF` vs `CORPUS`) is deliberate — `settings.py` reads both spellings, with `CORPUSF` taking precedence to stay aligned with the live `.env`. |
| `ACTIVE_BENCHMARK_VERSION` | Phase 2; blank is fine. |

Phase 1 also reads the following keys; the defaults in `.env.example` work
out of the box and only need overrides if you want to tune:

`RAG_SIMILARITY_THRESHOLD`, `RAG_TOP_K`, `EMBEDDING_MODEL`,
`EMBEDDING_DEVICE`, `EMBEDDING_BATCH_SIZE`, `OCR_TESSERACT_ENABLED`,
`OCR_TESSERACT_LANG`, `OCR_TESSERACT_MIN_CONFIDENCE`,
`OCR_VISION_LLM_TIMEOUT`, `OCR_MAX_PAGES`, `OCR_MAX_BYTES`,
`OPENROUTER_TIMEOUT_SECONDS`, `OPENROUTER_MAX_RETRIES`.

## 2. OS-level dependencies (macOS)

```sh
brew install tesseract tesseract-lang   # provides spa.traineddata
```

On Linux:

```sh
sudo apt-get install -y tesseract-ocr tesseract-ocr-spa
```

If you do **not** install Tesseract, the fallback path returns
`not_analyzable: ocr_unavailable` instead of crashing — set
`OCR_TESSERACT_ENABLED=false` to skip the fallback entirely.

## 3. Python toolchain

```sh
pyenv install 3.14.4    # matches backend/.python-version (changed in 94a2bde —
                        # 3.11.9 was uninstalled and broke `poetry` from backend/).
                        # `requires-python` in pyproject is still >=3.11,<4.0 so any
                        # 3.11/3.12/3.13/3.14 you already have on the machine works.
cd backend
poetry install          # installs Phase-1 deps (pypdf, sentence-transformers,
                        # ruff, django-stubs, etc.); poetry.lock needs a fresh
                        # `poetry lock` after pulling Phase 1 because 7 new
                        # runtime deps were added.
```

First-run note: `sentence-transformers` will download
`paraphrase-multilingual-MiniLM-L12-v2` (~120 MB) into the HF cache the
first time embeddings are computed. If your environment can't reach
HuggingFace, set `HF_HOME` to a pre-populated cache directory.

## 4. Database + Redis

```sh
docker compose -f docker-compose.dev.yml up -d   # postgres+pgvector+redis
cd backend
make migrate                                     # applies new 0003 corpus migration
```

Postgres needs the `vector` extension (already in the compose image).
The new migration `corpus/0003_pattern_link_and_rag_log.py` adds:
- `pattern_legal_link` table (CS-086)
- `rag_query_log` table (CS-089)

## 5. Seeds + corpus ingestion

```sh
cd backend
# CS-033 + CS-034 (idempotent, already merged):
python manage.py seed_rubric_version --activate
python manage.py seed_corpus_version --activate

# CS-080–CS-084 + CS-090 — load the 7 legal markdown files, embed, activate:
python manage.py ingest_corpus --version 2026-05-15 --activate
```

If `ingest_corpus` is slow on first run, that's the MiniLM model
downloading. Subsequent runs reuse the cached model.

## 6. Smoke verification

```sh
cd backend
make test                                      # full pytest suite
curl -s http://localhost:8000/api/health/      # → {"status": "ok"}
curl -F file=@sample.pdf \
     -F disclaimer_method=checkbox \
     -F source=web \
     http://localhost:8000/api/v1/submissions/ # → 201 with submission_id
curl -s -X POST -H "Content-Type: application/json" \
     -d '{"finding":"renuncia de derechos del inquilino"}' \
     http://localhost:8000/api/v1/corpus/retrieve/   # → citations
```

## 7. Known open items (not blocking Phase 1)

- `CS-050`, `CS-059`: multi-file (1–50) upload, image-dimension validator,
  and explicit `DISCLAIMER_REQUIRED` enforcement are Phase 2 follow-ups.
- `CS-006` (secrets baseline): a few PRD-canonical key names
  (`OCR_FALLBACK_ENABLED`, `TESSERACT_LANG`, `PDF_MAX_PAGES`,
  `DB_POOL_MIN_SIZE/MAX_SIZE`, `ANONYMIZATION_AFTER_DAYS`,
  `JOB_BATCH_SIZE`, `JOB_TIMEZONE`, report-link TTL) are not yet in
  `.env.example`. Phase 1 uses functionally-equivalent names
  (`OCR_TESSERACT_ENABLED`, `OCR_MAX_PAGES`, etc.) — reconcile when
  retention/admin tickets land.
- `CS-033`: full 38-criterion rubric YAML loader is the next dependency
  for closing CS-086 with real rubric data instead of synthetic patterns.
- Live `CS-087` tuning sweep against the real embedded corpus is the
  final closure step for EPIC-03 — needs steps 4 + 5 above completed.
