# Casa Segura — Architecture

> Working name: **Casa Segura** (alt: Buena Seña). See `STATUS.md` Decisions Log.

## 1. What we are building

A two-step tool that helps people in El Salvador avoid real estate fraud, before they commit money and before they sign.

**Flow 1 — Project legitimacy check.**
User photographs the project billboard. System extracts developer, project name, permit, address. Cross-references against public reputation signals and a curated blacklist. Returns a verdict: green / yellow / red.

**Flow 2 — Contract fraud check.**
Gated by Flow 1. User uploads the contract PDF. System checks for fraud-specific patterns (escrow, delivery dates, identity match between Flow 1 and contract, etc.). Returns the same verdict shape.

## 2. North star

- **Absurdly simple.** Two questions, two answers.
- **Open source from day 0.** MIT license. The trust comes from verifiability, not from operator identity.
- **Mobile-first, low bandwidth.** Target user has a midrange Android over 4G.
- **No PII storage.** Contracts are processed and discarded. Logs are aggregate metrics only.
- **Not legal advice.** Disclaimers visible on every result screen and every WhatsApp reply.

## 3. System diagram

```
                    ┌──────────────┐         ┌──────────────┐
                    │   Web (FE)   │         │   WhatsApp   │
                    │   Next.js    │         │   (Zavu)     │
                    └──────┬───────┘         └──────┬───────┘
                           │                        │
                           └────────┬───────────────┘
                                    │ HTTPS / JSON
                            ┌───────▼────────┐
                            │   API (BE)     │
                            │   FastAPI      │
                            └───────┬────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
       ┌──────▼──────┐      ┌───────▼───────┐    ┌────────▼────────┐
       │ OpenRouter  │      │  Web search   │    │  Redis (session │
       │ (vision +   │      │  (reputation) │    │   + Flow 1 gate)│
       │  text LLMs) │      │               │    │                 │
       └─────────────┘      └───────────────┘    └─────────────────┘
                                    │
                            ┌───────▼────────┐
                            │  Static data   │
                            │  patterns.yaml │
                            │  blacklist.csv │
                            └────────────────┘
```

## 4. Stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | Next.js (App Router) on Vercel | Fastest path to mobile-first, v0 output drops in cleanly |
| Backend | Python 3.11 + FastAPI | One team member's strongest stack |
| LLM gateway | OpenRouter | Single API for vision + text, model swap without code change |
| WhatsApp | Zavu | Required by hackathon credits, LATAM-native |
| Session | Redis (Upstash free tier) | Cheap, persists Flow 1 → Flow 2 gate |
| OCR strategy | Vision LLM, **not** Tesseract | Better on weathered outdoor signs |
| PDF text | pypdf | Simple text PDFs only in MVP |
| Search | SerpAPI free tier or DuckDuckGo HTML | Reputation lookups |
| Hosting BE | Railway or Fly.io | Free tier, fast deploy |

## 5. Data flow

**Flow 1:**
1. Client posts photo → `POST /check-project`
2. BE sends photo + extraction prompt to vision model
3. BE receives structured JSON: `{developer, project, permit, address}`
4. BE runs three parallel checks:
   - Web search for `"<developer>" estafa OR denuncia`
   - Blacklist match against `blacklist.csv`
   - Permit format sanity check (regex on Salvadoran permit numbers)
5. BE synthesizes verdict via a final LLM call with the evidence
6. Response includes `session_id` (TTL 24h in Redis)

**Flow 2:**
1. Client posts PDF + session_id → `POST /check-contract`
2. BE rejects if no green/yellow Flow 1 result for session
3. BE extracts text, chunks if long
4. BE runs pattern detection: each pattern in `patterns.yaml` is checked with structured output (found / not found / cite text)
5. BE adds cross-checks:
   - Does seller name match Flow 1 developer?
   - Does property address match Flow 1?
6. Synthesized verdict returned

## 6. Risks and panic buttons

> Each item: **trigger condition → fallback action**.

**R1: Vision model fails on real billboards (>30% extraction errors).**
Trigger: Saturday morning validation script returns garbage on 3+ test photos.
**Panic button:** Replace photo flow with a manual form (developer name, project name, permit number). Less magical, ships reliably. Photo becomes optional add-on.

**R2: Zavu media (photo/PDF) inbound is broken or rate-limited.**
Trigger: Hour 30, can't reliably receive a PDF over WhatsApp.
**Panic button:** WhatsApp becomes text-only — users get a deep link back to web for uploads. Web stays the primary surface.

**R3: PDF extraction is unreliable (scanned contracts).**
Trigger: pypdf returns empty or scrambled text on test contracts.
**Panic button:** MVP supports text-PDF only, with a clear error message and a "take photos of each page" fallback that goes through the vision model.

**R4: Behind schedule at hour 30.**
**Panic button:** Drop WhatsApp. Web-only with both flows is a complete product. Add WhatsApp in v2.

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
| **C** | Integration / content | Zavu webhook, blacklist + patterns curation, README, pitch deck (Faces) |

## 8. Timeline (hour-marked)

| Hours | Milestone | Owner(s) |
|---|---|---|
| 0–4 | Validation: vision script works on 3 real billboards | A |
| 0–6 | Curated `patterns.yaml` (20 patterns) + `blacklist.csv` skeleton | C |
| 0–6 | FE scaffold + v0 prompts for both flow screens | B |
| 6–18 | BE endpoints functional, schemas locked | A |
| 6–18 | FE wired to BE on local, both flow screens render | B |
| 18–30 | Web fully working end-to-end, deployed | A + B |
| 18–30 | Zavu webhook receiving and routing | C |
| 30–42 | WhatsApp formatting, gate logic, polish | C + A |
| 42–48 | README, license, deck, demo recording | C + B |

## 9. Open source posture

- Repo public from hour 1, MIT license.
- README states clearly: not legal advice, project is community-curated, contributions welcome especially from Salvadoran legal professionals.
- `patterns.yaml` and `blacklist.csv` versioned in repo so contributions are pull-requestable.
- Operator identity not required; the code being open is the trust model.
- A `SECURITY.md` covering responsible disclosure for false-positive blacklist entries.

## 10. Privacy and legal posture

- Uploaded files processed in memory, never written to disk.
- No user accounts. Session ID is ephemeral and bound to phone number (WhatsApp) or browser cookie (web).
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
