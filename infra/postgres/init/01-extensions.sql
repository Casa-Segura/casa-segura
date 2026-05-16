-- Casa Segura — Postgres extensions bootstrap.
-- Runs ONCE on first container start (postgres image executes any *.sql in
-- /docker-entrypoint-initdb.d/ against the database named in POSTGRES_DB).
--
-- Extensions:
--   vector     — pgvector, required by corpus.LegalChunk.embedding (F3 RAG).
--   pgcrypto   — gen_random_uuid(), hashing helpers used by F7/F8.
--   uuid-ossp  — legacy UUID generation (kept for compatibility per F8 §3).

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Also install the extensions on `template1` so every future CREATE DATABASE
-- inherits them. Most importantly, this lets Django's `test_casasegura`
-- (created by pytest-django on every test session) reach migrations without
-- failing on `type "vector" does not exist` when applying the LegalChunk
-- migration. Without this block, CI's Backend tests job aborts at the very
-- first migration that references a `vector(384)` column.
\connect template1
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
