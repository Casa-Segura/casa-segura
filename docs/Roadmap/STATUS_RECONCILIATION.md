---
project: Casa Segura
doc_type: reconciliation
status: pending_review
last_updated: 2026-05-15
tags:
  - casa-segura
  - reconciliation
---

# STATUS Reconciliation — Gap Analysis vs Formal PRDs

> **Scope:** This file is an analysis of deltas between hackathon-era [[STATUS]] and the formal PRDs. It does **not** represent live delivery state. Execution status lives in **`docs/Roadmap/tickets/`**, with summaries in **`docs/Roadmap/EPIC-*.md`** (see Roadmap README).
>
> Per project Rule 7 (surface conflicts, don't average them). [[STATUS]] was written for the hackathon framing. The formal PRDs ([[PRD_GENERAL]], [[FEATURES_MAP]], [[RUBRICA_CONTRATO]], [[BE-SERVICES]]) describe the production product. Where they conflict, the **formal PRDs win** because they are more specified, more recent in intent, and approved.
>
> This note lists every delta. Action column says what to do.

## Material deltas

| # | STATUS says | PRDs say | Action |
|---|---|---|---|
| 1 | Two flows: project (billboard) + contract, gated | Only contract analysis | [[STATUS]] line on "Flow 2 gated by Flow 1" is **wrong for production**. Billboard becomes [[EPIC-12-project-verification]], optional, separate entry point. |
| 2 | D6: Compraventa + arrendamiento only | 8 contract types (CVC, CVP, ARV, ARC, APV, LEA, IVU, FSV) per [[RUBRICA_CONTRATO]] §3 | Scope expanded materially. Update [[STATUS]] D6 or remove. |
| 3 | T024: "LLM-driven pattern check, reads from `fraud_pattern` DB" | F4 rubric engine evaluates 38 criteria per [[RUBRICA_CONTRATO]] §16 | Different abstraction. The `fraud_pattern` table from [[BE-SERVICES]] §2.2 still has a place (it's the curated catalog), but it is consumed by the per-criterion evaluators in [[EPIC-06-rubric-engine]], not as a parallel pipeline. Tickets T024 and T035 are obsolete in their hackathon form. |
| 4 | T037: RAG eval set 10 pairs | PRD doesn't mandate a count | Keep T037's discipline (eval set with threshold tuning), but the count grows to ≥30 pairs spanning the 6 categories. |
| 5 | T060–T066: Zavu **inbound** (receive WhatsApp photo/PDF) | F7 / US-05: **SMS/email/link outbound** (deliver report summary, PDF, or link) | WhatsApp/Zavu is no longer an MVP delivery channel. Inbound conversational media remains post-MVP unless a new ticket explicitly revives it. |
| 6 | Hour-marked milestones (0, 4, 8, 14, 18, 30, 42, 48) | Phase-based per [[FEATURES_MAP]] §3 | Replace milestone table in [[STATUS]] with phase rollup. Keep hour-marks only for the active hackathon track if you run one. |
| 7 | D7: "No custom ML in MVP — all via OpenRouter" | [[BE-SERVICES]] §4.6 uses `paraphrase-multilingual-MiniLM-L12-v2` (sentence-transformers, in-process) for embeddings | Soft conflict. Embeddings aren't "custom ML" (no training), but D7 should be amended to "no custom-trained models; pretrained embeddings allowed". |
| 8 | T015 "Provision Postgres + pgvector" — owner A | [[BE-SERVICES]] §1 confirms same | Aligned. Move to [[CS-020]]. |
| 9 | T020 schemas list: "Finding, ProjectCheckResult, ContractCheckResult" | PRD has no `ProjectCheckResult` | Drop `ProjectCheckResult`. `ContractCheckResult` ~ `ContractAnalysis` from [[RUBRICA_CONTRATO]] §12.2. |
| 10 | Implicit: Tesseract Spanish OCR fallback (T023b) | [[BE-SERVICES]] §3.3 confirms with `OCR_FALLBACK_ENABLED` env | Aligned. Captured in [[EPIC-02-ingestion-ocr]]. |
| 11 | Implicit: T070 README + T071 SECURITY.md | [[PRD_GENERAL]] §3 BR-07 (disclaimer everywhere), §10 (privacy posture) | Both belong in [[EPIC-00-foundation]] and [[EPIC-11-observability]] respectively. |

## Items in STATUS that survive intact

- T001 GitHub org/MIT license/README — [[CS-001]]
- T002 Django + DRF API scaffold — [[CS-002]]
- T003 Next.js scaffold — moved to [[EPIC-10-frontend]] backlog
- T004 OpenRouter account — [[CS-006]] (secrets baseline)
- T005 Redis (Upstash) — [[CS-006]]
- T015 Postgres + pgvector — [[CS-020]]
- T016 Django migrations bootstrap — [[CS-021]]
- T017 ORM models — [[CS-023]]…[[CS-029]]
- Risk log R8–R11 — survives, moved to [[EPIC-03-corpus-rag]] and [[EPIC-02-ingestion-ocr]] risk sections

## Items in STATUS that should be cut

- T007–T009 Vision validation on billboards — moved to [[EPIC-12-project-verification]] (optional epic), no longer blocking
- T010, T011 patterns.yaml / blacklist.csv seeding (hackathon-specific) — superseded by [[EPIC-06-rubric-engine]] criterion catalog
- T060–T066 Zavu inbound — out of MVP scope per PRD

## Recommended STATUS rewrite

Two options:

**Option A — Replace STATUS entirely.** Make [[STATUS]] a phase-based dashboard (which epics are in-flight, blocked, done) and let the tickets live in `Roadmap/tickets/`. Cleaner long-term.

**Option B — Mark STATUS as historical.** Add a banner at the top of [[STATUS]]: "This document describes the hackathon plan. See [[Roadmap/README]] for the current ticket structure." Keep STATUS frozen for historical reference.

Either is fine. **Recommendation: Option A** once the first sprint completes (to avoid losing momentum on a rewrite right now).

## BVA application across the roadmap

Boundary Value Analysis matters most in [[EPIC-06-rubric-engine]] because every criterion in [[RUBRICA_CONTRATO]] has numeric thresholds. Examples of where failures will cluster:

- **Score band edges**: 4.9 / 5.0 / 7.9 / 8.0 (band assignment)
- **Override fires**: each of the 11 overrides has a binary trigger that, when active, *must* force score=0 regardless of category averages
- **Interest rate B2**: scale boundaries at 9, 10, 11, 14, 19 (six bands)
- **Down payment B1**: scale boundaries at 10, 15, 20, 35 (five bands)
- **Total cost B4**: scale boundaries at 1.5, 1.8, 2.0, 2.5 (five bands)
- **Asymmetric penalty**: input scoring better than benchmark must NOT reduce score below benchmark-equivalent
- **RAG similarity threshold**: 0.65 boundary — chunks at 0.649 are excluded, at 0.651 included
- **Retention**: 90-day anonymization boundary (created_at = NOW() - 89d59m vs - 90d00m01s)
- **Link TTL**: 30-day expiration boundary

These are surfaced as BVA tables in the relevant ticket files.
