---
id: ADR-0004
title: Versioning strategy for schema, rubric, corpus, and benchmarks
status: Accepted
date: 2026-05-15
deciders: Backend lane
supersedes: —
related: backend/shared/observability/logging.py `SCHEMA_VERSION`, docs/Roadmap/tickets/CS-010.md, docs/Roadmap/tickets/CS-030.md, docs/Roadmap/tickets/CS-033.md, docs/Roadmap/tickets/CS-034.md, _shared/GLOBAL_ASSUMPTIONS.md §17 GQ-02
---

## Context

Casa Segura emits a `schema_version` on every log line and API error
envelope (see `backend/shared/observability/logging.py`) and persists
three independently-versioned catalogs — `RubricVersion`,
`CorpusVersion`, `BenchmarkVersion` — each referenced by
`ContractAnalysis`. Without explicit bump rules, ops cannot reproduce
an analysis from six months ago, and trial-by-trial drift makes the
dataset useless for trend analysis.

Three forces push for a written rule now:

- F4/F5/F6 store the version triple on every analysis; a replay tool is
  on the roadmap and needs a deterministic lookup.
- Product wants quarterly benchmark refreshes (`_shared/GLOBAL_ASSUMPTIONS.md`
  §17 GQ-02) without losing historical comparisons.
- The `reject_catalog_mutation()` trigger from CS-030 already blocks
  in-place edits; the policy needs to match the schema-level reality.

## Decision

Four versioned identifiers, each with its own format and bump cadence:

| Identifier | Format | When to bump | Mutability |
|---|---|---|---|
| `schema_version` | semver `MAJOR.MINOR.PATCH` | MAJOR on incompatible envelope/log shape; MINOR on backward-compat additive; PATCH on cosmetic | bumped in `shared/observability/logging.py::SCHEMA_VERSION`, no DB row |
| `rubric_version` | semver `1.0.0` | MAJOR on score-impacting criterion change; MINOR on text/prompt edits that keep scores; PATCH on typo fixes | new INSERT row; old row stays; `is_active` flips |
| `corpus_version` | ISO date `YYYY-MM-DD` | each time the legal corpus is re-ingested (any source updated, added, removed) | new INSERT; old rows preserved indefinitely |
| `benchmark_version` | quarterly tag `YYYY-Q{1..4}` | every Q1 review by product (per `_shared/GLOBAL_ASSUMPTIONS.md` §17 GQ-02) | new INSERT |

Catalog rows are immutable after INSERT except for the `is_active` flag
(enforced by the `reject_catalog_mutation()` trigger created in
CS-030). At most one row per catalog may be active; the partial unique
index `uq_<catalog>_version_active_singleton` enforces it at the
database level.

`ContractAnalysis` records the exact three (`rubric_version`,
`corpus_version`, `benchmark_version`) used so any analysis can be
replayed deterministically. Anonymization preserves these IDs.

## Bump procedure

1. Author the new catalog row + seed migration (see CS-033 for rubric,
   CS-034 for corpus).
2. Apply the migration in staging; verify it is idempotent (re-running
   must be a no-op).
3. PR review by another engineer plus product confirmation on the
   semver/date/quarter bump.
4. Activate atomically:

   ```sql
   BEGIN;
   UPDATE rubric_version SET is_active = false;
   UPDATE rubric_version SET is_active = true WHERE version = '<new>';
   COMMIT;
   ```

5. New analyses pick up the active version at the time of submission.
   In-flight analyses keep the version captured at the start of their
   pipeline — the version triple is snapshotted on `ContractAnalysis`
   creation, never re-read.

## Consequences

**Positive.**
- Full reproducibility: any historical analysis can be re-run against
  the exact rubric/corpus/benchmark it used.
- No in-place catalog edits possible; downstream cost-tracking and
  trend dashboards stay coherent.
- The four identifiers track independent concerns and can move on
  independent cadences without coupling.

**Negative.**
- Cannot "fix a typo" in a published rubric — must publish a PATCH
  version (cheap, but procedural).
- Four versioning schemes (semver, semver, date, quarter) to remember.
  Mitigated by the table above and the seed-migration recipe in
  CS-033/CS-034.

## Alternatives considered

1. **Single global `app_version`.** Rejected: rubric, corpus, and
   benchmark bump on independent cadences (per-edit, per-ingestion,
   quarterly). Coupling them would force needless cascade bumps and
   destroy the value of independent version tracking on
   `ContractAnalysis`.
2. **Mutable catalog with audit log only.** Rejected: easy to forget
   to write the audit row, and there is no way to reproduce a prior
   state from a forward-only audit log without reconstructing every
   intermediate write.
3. **Git SHA as version.** Rejected: ambiguous for partial reseeds
   (a SHA bumps even when the rubric file did not change), and not
   human-readable. Semver/date/quarter conveys intent at a glance.
