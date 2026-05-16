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
