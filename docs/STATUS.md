# Casa Segura — Status

> Living document. Update at end of each working session. Tickets move from `Backlog` → `In Progress` → `Done`.

## Phase
**Pre-build · Planning**

## Team

| | Name | Role | Stack |
|---|---|---|---|
| **A** | _tbd_ | Backend / ML | Python, Django 5.2 LTS, DRF, OpenRouter, Celery, Redis |
| **B** | _tbd_ | Frontend | Next.js, Tailwind, v0 |
| **C** | _tbd_ | Integration / Content | Zavu, content curation, README, deck |

---

## Milestones

| ID | Goal | Hour | Owner | Status |
|---|---|---|---|---|
| M1 | Architecture validated, repos created | 0 | All | ☐ |
| M2 | Vision extraction working on 3 real billboards | 4 | A | ☐ |
| M3 | `patterns.yaml` v1 (20 entries), `blacklist.csv` v1 | 6 | C | ☐ |
| M3b | Postgres + pgvector live, ER migrated, seeds loaded | 8 | A | ☐ |
| M3c | Legal corpus ingested (≥1 source) and RAG retrieval working | 14 | A | ☐ |
| M4 | BE endpoints functional locally with OCR + RAG wired | 18 | A | ☐ |
| M5 | FE web complete and deployed | 30 | B | ☐ |
| M6 | WhatsApp integration live | 42 | C | ☐ |
| M7 | README, license, deck, demo recorded | 48 | All | ☐ |

---

## Tickets

> Status legend: ☐ backlog · ◐ in progress · ☑ done · ✗ blocked/cut

### Setup (hour 0–2)

| ID | Title | Owner | Status |
|---|---|---|---|
| T001 | Create GitHub org/repo, MIT license, README skeleton | C | ☐ |
| T002 | BE scaffold: Django + DRF + pyproject + Dockerfile + .env.example | A | ☐ |
| T003 | FE scaffold: Next.js App Router + Tailwind + shadcn | B | ☐ |
| T004 | Set up OpenRouter account, store key in shared secrets | A | ☐ |
| T005 | Set up Upstash Redis, store URL in shared secrets | A | ☐ |
| T006 | Confirm Zavu account active, store key, verify media support | C | ☐ |

### Validation (hour 0–4) — *Highest priority. Blocks everything else.*

| ID | Title | Owner | Status |
|---|---|---|---|
| T007 | Write 10-line vision script: photo → JSON | A | ☐ |
| T008 | Test on 3 real billboard photos (find local examples) | A | ☐ |
| T009 | Decide: vision-first or manual-fallback (panic R1 trigger?) | A + C | ☐ |

### Content / data (hour 0–6)

| ID | Title | Owner | Status |
|---|---|---|---|
| T010 | Write 20 fraud patterns in `patterns.yaml` | C | ☐ |
| T011 | Seed `blacklist.csv` with 5-10 confirmed cases from news | C | ☐ |
| T012 | Write disclaimer copy (web + WhatsApp) | C | ☐ |
| T013 | Write loading state copy variants | C | ☐ |

### Backend — data layer (hour 2–8)

| ID | Title | Owner | Status |
|---|---|---|---|
| T015 | Provision Postgres + pgvector (Supabase or Railway) | A | ☐ |
| T016 | Django migrations bootstrap (all ER tables, vector ext) | A | ☐ |
| T017 | Django ORM models matching ER (legal_document, legal_chunk, fraud_pattern, pattern_legal_link, blacklisted_developer, blacklist_source, check_event) | A | ☐ |
| T018 | Seed script: load `patterns.yaml` → `fraud_pattern` table | C | ☐ |
| T019 | Seed script: load `blacklist.csv` → `blacklisted_developer` + `blacklist_source` | C | ☐ |

### Backend — services (hour 6–18)

| ID | Title | Owner | Status |
|---|---|---|---|
| T020 | Pydantic schemas: Finding (with `legal_reference`), ProjectCheckResult, ContractCheckResult, LegalReference | A | ☐ |
| T021 | `services/vision.py` with retry on JSON validation fail | A | ☐ |
| T022 | `services/reputation.py` (SerpAPI or DDG) with Redis cache | A | ☐ |
| T023 | `services/ocr.py` — `detect_kind` + routing (text PDF / scanned PDF / image) | A | ☐ |
| T023b | OCR Tesseract fallback path with Spanish language pack | A | ☐ |
| T024 | `services/patterns.py` LLM-driven pattern check (reads from DB, not YAML at runtime) | A | ☐ |
| T025 | `services/session.py` create/get/gate (Redis) | A | ☐ |
| T026 | `services/verdict.py` synthesis with strict prompt (no ungrounded citations) | A | ☐ |
| T027 | `POST /check-project` endpoint | A | ☐ |
| T028 | `POST /check-contract` endpoint with gate | A | ☐ |
| T029 | `GET /health` | A | ☐ |
| T030 | Deploy BE to Railway/Fly | A | ☐ |

### Backend — RAG (hour 4–18, parallel track)

| ID | Title | Owner | Status |
|---|---|---|---|
| T031 | Download corpus sources to `corpus/raw/` (Código Civil, Ley Protección al Consumidor) | C | ☐ |
| T032 | `scripts/ingest_corpus.py` — chunk-by-article + tag inference + embed + persist | A | ☐ |
| T033 | Run ingestion, verify counts (~500+ chunks for both sources) | A | ☐ |
| T034 | `services/rag.py` — `retrieve_for_finding` with threshold + pattern shortcut | A | ☐ |
| T035 | Manually link top 10 patterns to known articles in `pattern_legal_link` | C | ☐ |
| T036 | Wire RAG into `verdict.py` for both flows | A | ☐ |
| T037 | Eval set: 10 (finding, expected article) pairs; tune similarity threshold | A | ☐ |

### Frontend (hour 6–30)

| ID | Title | Owner | Status |
|---|---|---|---|
| T040 | Landing page (Screen 1) — generate via v0 | B | ☐ |
| T041 | Flow 1 upload (Screen 2) | B | ☐ |
| T042 | Flow 1 loading (Screen 3) with rotating copy | B | ☐ |
| T043 | Flow 1 result (Screen 4) — green/yellow/red variants | B | ☐ |
| T044 | Flow 2 upload (Screen 5) with gate redirect | B | ☐ |
| T045 | Flow 2 loading (Screen 6) | B | ☐ |
| T046 | Flow 2 result (Screen 7) with download summary | B | ☐ |
| T047 | Server actions calling BE | B | ☐ |
| T048 | Session cookie wiring (mirrors BE Redis session) | B | ☐ |
| T049 | Deploy to Vercel | B | ☐ |
| T050 | Mobile QA on real Android | B | ☐ |

### WhatsApp (hour 18–42)

| ID | Title | Owner | Status |
|---|---|---|---|
| T060 | `POST /webhook/zavu` with signature validation | C + A | ☐ |
| T061 | Phone number → session mapping in Redis | A | ☐ |
| T062 | Inbound photo handler → call /check-project | C | ☐ |
| T063 | Inbound PDF handler → call /check-contract | C | ☐ |
| T064 | Outbound formatting (green/yellow/red templates) | C | ☐ |
| T065 | Onboarding message + gate message + error messages | C | ☐ |
| T066 | End-to-end test on real WhatsApp number | C | ☐ |

### Polish + ship (hour 42–48)

| ID | Title | Owner | Status |
|---|---|---|---|
| T070 | README: what, why, how, contributing, disclaimer | C | ☐ |
| T071 | SECURITY.md with disclosure email + dispute path | C | ☐ |
| T072 | Pitch deck via Faces | C | ☐ |
| T073 | Demo recording (90 seconds) | B | ☐ |
| T074 | Final QA pass on web | B | ☐ |
| T075 | Final QA pass on WhatsApp | C | ☐ |
| T076 | Submission | All | ☐ |

---

## Risk log

| ID | Risk | Trigger condition | Panic button | Status |
|---|---|---|---|---|
| R1 | Vision model fails on real billboards | T008 returns garbage on 3+ photos | Manual form fallback for project data | ☐ Open |
| R2 | Zavu media inbound broken | Hour 30, can't receive PDF reliably | WhatsApp text-only, deep-link to web | ☐ Open |
| R3 | PDF extraction unreliable | pypdf returns empty on test contracts | MVP supports text-PDF only; photo-of-pages fallback later | ☐ Open |
| R4 | Behind schedule at hour 30 | M5 not hit | Drop WhatsApp, ship web-only | ☐ Open |
| R5 | Behind schedule at hour 42 | M6 not hit | Drop Flow 2, ship Flow 1 only | ☐ Open |
| R6 | Reputation search throttled | SerpAPI exhausted or DDG blocks | Blacklist-only checks for Flow 1 | ☐ Open |
| R7 | LLM hallucinates findings | QA shows fabricated cites | Tighten synthesis prompt; require evidence cite for every finding | ☐ Open |
| R8 | Legal corpus ingestion blows the schedule | Hour 6, less than 1 source ingested | Ship without RAG; findings lose citations but still work | ☐ Open |
| R9 | RAG retrieves irrelevant articles | QA shows weak matches surfacing as citations | Raise threshold to 0.75; if still bad, use only `pattern_legal_link` shortcuts | ☐ Open |
| R10 | pgvector deploy difficulty on hosting tier | Hour 8, can't get extension installed | Switch to Supabase (pgvector enabled by default) | ☐ Open |
| R11 | Tesseract Spanish accuracy too low | OCR fallback returns gibberish | Drop Tesseract; on vision quota hit, return retry message | ☐ Open |

---

## Decisions log

| ID | Decision | Date | Notes |
|---|---|---|---|
| D1 | Working name = Casa Segura | _today_ | Alt: Buena Seña. Final pick at hour 30 based on team vote. |
| D2 | License = MIT | _today_ | |
| D3 | No user accounts in MVP | _today_ | Phone number / browser cookie only |
| D4 | No persistent storage of uploaded content | _today_ | Privacy-by-design |
| D5 | El Salvador only for v1 | _today_ | Multi-country is v2+ |
| D6 | Compraventa + arrendamiento only | _today_ | Other contract types are v2+ |
| D7 | No custom ML in MVP | _today_ | All inference via OpenRouter |
| D8 | Spanish only, "tú" not "usted" | _today_ | Warmer tone for vulnerable users |

---

## Open questions

- [ ] Where do we host the BE — Railway or Fly? (Decision by hour 6)
- [ ] SerpAPI free credits enough for the demo, or do we need DDG fallback from start?
- [ ] Domain name — buy one or use Vercel subdomain for MVP?
- [ ] Who is the public point of contact in the README, or do we genuinely keep it operator-anonymous?

---

## Update template

> Copy this block at the end of each working session.

```
### Update — [date, hour mark]
- Done: T0xx, T0yy
- In progress: T0zz
- Blocked: T0aa (reason)
- Risks triggered: none / Rx (action taken)
- Next session focus:
```
