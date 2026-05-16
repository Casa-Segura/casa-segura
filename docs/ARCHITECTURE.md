# Casa Segura — Architecture

> Working name: **Casa Segura** (alt: Buena Seña). See `STATUS.md` Decisions Log.
>
> **Implementation stack:** Django 5.2 LTS + DRF, Django ORM + Django migrations, Celery + Redis, PostgreSQL 15 + pgvector; Pydantic v2 for domain DTOs and queue/LLM payloads ([ADR-0001](./adr/ADR-0001-django-backend-stack.md), `docs/analysis/_shared/GLOBAL_ASSUMPTIONS.md`). The sections below reflect the current **contract-first MVP** direction; optional project verification is tracked separately in `docs/Roadmap/EPIC-12-project-verification.md`.

## 1. What we are building

A mobile-first tool that helps people in El Salvador review real estate contracts before they commit money or sign.

**Primary flow — Contract fraud check.**
User takes clear photos of the contract pages or uploads a PDF. The system extracts text, classifies the contract, evaluates it with the rubric engine, retrieves legal context, and returns a report with green / yellow / red disposition, findings, cited legal basis, and share options.

**Optional flow — Project verification.**
User may photograph a project billboard or use a manual form. The system extracts developer, project name, permit, and address, then runs lightweight checks when providers are configured. This flow is useful context but never gates contract analysis.

## 2. North star

- **Absurdly simple.** Two questions, two answers.
- **Open source from day 0.** MIT license. The trust comes from verifiability, not from operator identity.
- **Mobile-first, low bandwidth.** Target user has a midrange Android over 4G.
- **No PII storage.** Contracts are processed and discarded. Logs are aggregate metrics only.
- **Not legal advice.** Disclaimers visible on every result screen and delivery message.

## 3. System diagram

```
                    ┌──────────────┐         ┌──────────────┐
                    │   Web (FE)   │         │ SMS / Email  │
                    │   Next.js    │         │ Delivery     │
                    └──────┬───────┘         └──────▲───────┘
                           │                        │
                           └────────┬───────────────┘
                                    │ HTTPS / JSON + queue
                            ┌───────▼────────────────┐
                            │   API (BE)             │
                            │   Django 5.2 + DRF     │
                            └───────┬────────────────┘
                                    │
       ┌────────────────────────────┼────────────────────────────┐
       │                            │                            │
┌──────▼──────┐            ┌────────▼────────┐           ┌────────▼────────┐
│ OpenRouter  │            │  Web search     │           │ Redis           │
│ (vision +   │            │  (reputation)   │           │ (sessions,      │
│  text LLMs) │            │                 │           │  Celery broker) │
└─────────────┘            └─────────────────┘           └─────────────────┘
                                    │
                   ┌────────────────┴────────────────┐
                   │                                 │
           ┌───────▼────────┐                 ┌───────▼────────┐
           │  Static data   │                 │ Postgres 15   │
           │  patterns.yaml │                 │ + pgvector    │
           │  blacklist.csv │                 │ (curated rows)│
           └────────────────┘                 └────────────────┘
```

## 4. Stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | Next.js (App Router) on Vercel | Fastest path to mobile-first, v0 output drops in cleanly |
| Backend | Python 3.11+ **Django 5.2 LTS** + **DRF**; **Celery** workers | LTS stability; ORM + admin + migrations; async jobs for LLM/OCR/RAG stages |
| Domain DTOs / payloads | **Pydantic v2** | Framework-free types for domain, LLM structured I/O, and queue envelopes |
| LLM gateway | OpenRouter | Single API for vision + text, model swap without code change |
| Delivery | SMS provider + SMTP + public link | SMS summary, email PDF, and web link are the canonical MVP delivery modes |
| Session & broker | **Redis** (Upstash free tier or managed) | Celery broker; optional stream handoffs; no project-verification gate |
| Database | **PostgreSQL 15+** + **pgvector** | Curated corpus, rubric/catalog data, vectors — not for raw uploads (see privacy §10) |
| OCR strategy | Vision LLM, **not** Tesseract | Better on weathered outdoor signs |
| PDF text | pypdf | Simple text PDFs only in MVP |
| Search | SerpAPI free tier or DuckDuckGo HTML | Reputation lookups |
| Hosting BE | Railway or Fly.io | Free tier, fast deploy |

## 5. Data flow

**Contract analysis:**
1. Client posts PDF and/or clear page photos → contract upload endpoint
2. BE validates disclaimer, size/type limits, and privacy-safe envelope
3. BE extracts text using PDF text extraction or vision OCR as appropriate
4. BE classifies the contract and evaluates rubric criteria
5. BE retrieves legal context for supported findings and synthesizes the report
6. User receives or opens the report via `sms_summary`, `email_pdf`, or `web_link`

**Optional project verification:**
1. Client posts billboard photo or manual form fields → project-verification endpoint
2. BE extracts or validates `{developer, project, permit, address}`
3. BE runs permit format checks and optional reputation lookup
4. BE returns a green/yellow/red project-verification verdict without creating a contract-analysis gate

## 6. Risks and panic buttons

> Each item: **trigger condition → fallback action**.

**R1: Vision model fails on real billboards (>30% extraction errors).**
Trigger: Saturday morning validation script returns garbage on 3+ test photos.
**Panic button:** Replace photo flow with a manual form (developer name, project name, permit number). Less magical, ships reliably. Photo becomes optional add-on.

**R2: SMS delivery provider is unavailable or rate-limited.**
Trigger: Can't reliably send report summaries over SMS.
**Panic button:** Keep web link + email PDF as complete delivery paths; SMS resumes when provider health recovers.

**R3: PDF extraction is unreliable (scanned contracts).**
Trigger: pypdf returns empty or scrambled text on test contracts.
**Panic button:** MVP supports text-PDF only, with a clear error message and a "take photos of each page" fallback that goes through the vision model.

**R4: Behind schedule at hour 30.**
**Panic button:** Drop SMS sending. Web link plus email PDF remains a complete product. Add SMS in v2.

**R5: Behind schedule at hour 42.**
**Panic button:** Drop Flow 2. Demo Flow 1 as v1, frame Flow 2 as roadmap. This is the deepest cut and it's still a coherent shipped product.

**R6: Reputation search returns nothing useful.**
Trigger: SerpAPI free tier exhausted or DuckDuckGo throttles.
**Panic button:** Fall back to blacklist-only checks for Flow 1. Verdict becomes "not on blacklist, no public flags found, proceed with normal caution".

## 7. Team plan (3 engineers)

| Person | Role | Owns |
|---|---|---|
| **A** | Python / ML | BE service, OpenRouter integration, pipelines, data extraction, Redis |
| **B** | Frontend | Next.js app, v0 generation, web upload, result rendering, deployment |
| **C** | Integration / content | SMS/email delivery, patterns curation, README, pitch deck (Faces) |

## 8. Timeline (hour-marked)

| Hours | Milestone | Owner(s) |
|---|---|---|
| 0–4 | Validation: vision script works on 3 real billboards | A |
| 0–6 | Curated `patterns.yaml` (20 patterns) + `blacklist.csv` skeleton | C |
| 0–6 | FE scaffold + v0 prompts for both flow screens | B |
| 6–18 | BE endpoints functional, schemas locked | A |
| 6–18 | FE wired to BE on local, both flow screens render | B |
| 18–30 | Web fully working end-to-end, deployed | A + B |
| 18–30 | SMS/email delivery routing | C |
| 30–42 | SMS summary formatting, delivery polish | C + A |
| 42–48 | README, license, deck, demo recording | C + B |

## 9. Open source posture

- Repo public from hour 1, MIT license.
- README states clearly: not legal advice, project is community-curated, contributions welcome especially from Salvadoran legal professionals.
- `patterns.yaml` and `blacklist.csv` versioned in repo so contributions are pull-requestable.
- Operator identity not required; the code being open is the trust model.
- A `SECURITY.md` covering responsible disclosure for false-positive blacklist entries.

## 10. Privacy and legal posture

- Uploaded files processed in memory, never written to disk.
- No user accounts. Any delivery target is hashed and temporarily encrypted only while delivery is pending.
- Logged data: timestamp, verdict, finding count. Never the developer name, address, or contract content.
- Every result screen ends with: *"Esto no es asesoría legal. Antes de firmar, consulta un abogado."*
- The blacklist must have a public dispute mechanism (email + GitHub issue) to remove false-positive developer entries.

## 11. Out of scope for MVP (explicit)

- User accounts, history, saved searches.
- Multi-country support (El Salvador only).
- Contract types other than compraventa and arrendamiento.
- Voice input.
- TensorFlow / custom ML models. *Note: team has the skill, but for MVP every inference goes through OpenRouter. Custom models are a v2+ conversation when we have curated training data.*
- Real-time integration with OPAMSS or CNR (no clean public APIs; manual data only for MVP).
