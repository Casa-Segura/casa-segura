# Casa Segura — Legal Grounding Layer (Architecture Enhancement)

> Companion document to `ARCHITECTURE.md`, `BE-SERVICES.md`, and `UI-UX.md`.
> This proposes a focused enhancement: **turn every Casa Segura finding from a vibe into a citation**.

## 1. The problem

Today's verdict is a colored chip plus a finding title and one or two sentences:

> 🟡 **Hay algo que revisar**
> · Sin mecanismo de fideicomiso
> · Fecha de entrega vaga

This works for trust at first glance, but for a Salvadoran adult about to commit life savings, "seems sketchy" is a thin reed. They want to know:

- *Is this actually illegal, or just inadvisable?*
- *Which law? Which article?*
- *If I show this to a lawyer, what do I cite?*
- *If I push back at the developer, what do I tell them?*

The product currently has no legal grounding. The verdict synthesis prompt sees evidence (reputation hits, blacklist match, pattern findings) and emits a verdict, but its only "knowledge" of Salvadoran housing law is whatever the model absorbed in pretraining — fuzzy, undated, not citable.

The enhancement: **every finding above a confidence threshold gets a `legal_basis` array of {law, article, paraphrased quote, link}.** The verdict screen surfaces these as expandable rows. The user goes from "be careful" to "Art. 4 of the Ley de Inquilinato says your contract has to be in writing with these four elements — yours is missing the property identification."

## 2. North star (extends the existing one)

Add to the existing principles in `ARCHITECTURE.md` §2:

- **Cite or stay silent.** If a finding cannot be grounded in a specific article, it doesn't get the legal-basis enrichment. The verdict still includes it, but without false legal weight. Better than confidently wrong citations.
- **Source-of-truth is the corpus.** All citations come from the curated `casa-segura-legal/` repo. The LLM is not allowed to invent law. If retrieval returns nothing relevant, the finding goes uncited.
- **Public-domain by design.** Salvadoran laws are public-domain government works. The corpus is in the open repo, structured, versionable, and PR-able.
- **The disclaimer doesn't change.** Every screen still ends with *"Esto no es asesoría legal."* Citing law makes the disclaimer more important, not less.

## 3. Updated system diagram

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
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
 ┌─────────────┐           ┌────────────────┐          ┌──────────────┐
 │ OpenRouter  │           │  Web search    │          │ Redis        │
 │ (vision +   │           │  (reputation)  │          │ (session)    │
 │  text LLMs) │           │                │          │              │
 └─────────────┘           └────────────────┘          └──────────────┘
        │                           │                           │
        └─────────────┬─────────────┴───────────────────────────┘
                      │
              ┌───────▼──────────────────────┐
              │  Static data + legal corpus  │
              │  patterns.yaml               │
              │  blacklist.csv               │
              │  legal/laws/*.md      ◄──── NEW
              │  legal/index.faiss    ◄──── NEW (article embeddings)
              └──────────────────────────────┘
                      ▲
                      │
                ┌─────┴───────┐
                │ legal_index │  ◄── NEW service: builds & queries the index
                └─────────────┘
```

Three things change:

1. **`legal/` data directory** added next to `data/`, holding the markdown corpus and a built embedding index.
2. **`legal_index` service** added under `services/`, responsible for retrieval-time queries against the corpus.
3. **`verdict.synthesize_*`** is upgraded to call `legal_index` for each finding before final synthesis, attaching `legal_basis` arrays.

Nothing else moves. WhatsApp, Zavu, vision, blacklist, reputation, sessions: unchanged.

## 4. The data layer: the curated legal corpus

See `casa-segura-legal/` (sibling deliverable). Every law file follows a fixed template:

```
---
law_id: ley-inquilinato
title: Ley de Inquilinato
decreto: D.L. 2591
fecha_emision: 1958-02-18
ultima_reforma: 2008-09-18
estado: vigente
source_url: ...
relevance_to_casa_segura: high
covers: [rentals, mesones, ...]
---

# Ley de Inquilinato

## Plain-language summary
...

## Application to Casa Segura
- finding `id` → art. N

## Article 1 — Scope
...

## Article 4 — Written contract required
[paraphrased article text + Casa Segura signal callout]
```

Each `## Article N` becomes one chunk. The chunk's metadata (law_id, article number, anchor URL, finding tags) accompanies the embedding. There are roughly 200 chunks across the 5 laws currently (Inquilinato has the most articles).

This is the only source of legal grounding. Adding a new law = adding a new file + reindex. PR-able. Diffable.

## 5. The retrieval layer: `legal_index` service

```python
# services/legal_index.py

from pathlib import Path
from pydantic import BaseModel
import frontmatter  # parse YAML headers
import re
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

class LegalChunk(BaseModel):
    law_id: str
    law_title: str
    article: str            # "Art. 4"
    anchor: str             # "art-4"
    text: str               # paraphrased article body
    tags: list[str]         # ["rentals", "written_contract", ...]
    source_url: str

class LegalCitation(BaseModel):
    law_id: str
    law_title: str
    article: str
    quote_es: str           # one-sentence paraphrase, < 30 words
    relevance_score: float  # 0..1 cosine sim
    url: str                # "/laws/01-...#art-4"
    official_source: str

class LegalIndex:
    def __init__(self, corpus_dir: Path, model_name: str):
        self.chunks: list[LegalChunk] = []
        self.embedder = SentenceTransformer(model_name)
        self.faiss_index: faiss.Index | None = None
        self._load(corpus_dir)
        self._build_index()

    def _load(self, corpus_dir: Path):
        for md_path in (corpus_dir / "laws").glob("*.md"):
            post = frontmatter.load(md_path)
            if post.get("estado") != "vigente":
                continue
            chunks = self._split_by_article(post.content, post.metadata)
            self.chunks.extend(chunks)

    def _split_by_article(self, body: str, meta: dict) -> list[LegalChunk]:
        # Splits on `### Art. N` headings, keeps the article body as text.
        ...

    def _build_index(self):
        vectors = self.embedder.encode([c.text for c in self.chunks])
        self.faiss_index = faiss.IndexFlatIP(vectors.shape[1])
        faiss.normalize_L2(vectors)
        self.faiss_index.add(vectors)

    async def search(
        self, query: str, k: int = 3, threshold: float = 0.45
    ) -> list[LegalCitation]:
        q = self.embedder.encode([query])
        faiss.normalize_L2(q)
        scores, idxs = self.faiss_index.search(q, k)
        hits = []
        for score, idx in zip(scores[0], idxs[0]):
            if score < threshold:
                continue
            chunk = self.chunks[idx]
            hits.append(LegalCitation(
                law_id=chunk.law_id,
                law_title=chunk.law_title,
                article=chunk.article,
                quote_es=self._first_sentence(chunk.text),
                relevance_score=float(score),
                url=f"/laws/{chunk.law_id}.md#{chunk.anchor}",
                official_source=chunk.source_url,
            ))
        return hits
```

Notes:

- **Embedding model:** for Spanish, a multilingual model that handles `es` well — `paraphrase-multilingual-MiniLM-L12-v2` or `intfloat/multilingual-e5-base` are both reasonable defaults. Lightweight, runs CPU.
- **Index storage:** built at startup from markdown, kept in memory. ~200 chunks × 384 dims = trivial. No external vector DB needed for MVP. If the corpus grows, swap to Chroma or pgvector with no API change.
- **Threshold:** 0.45 cosine sim is a starting point. Tuning data: a fixture set of 20 finding-text → expected-article pairs, run at startup as a regression check.
- **Stay vigente-only.** The frontmatter `estado` filter prevents `derogado` articles (which Inquilinato has many of in chapter V) from showing up.
- **Tag the chunks at build time** with finding-IDs from the `## Application to Casa Segura` section. A finding can pre-target chunks via tag boost rather than relying purely on semantic similarity.

## 6. Wiring into the verdict pipeline

The two endpoints (`/check-project` and `/check-contract`) gain one step before synthesis:

```python
# services/verdict.py (sketch)

async def synthesize_contract(
    contract_text: str,
    pattern_findings: list[Finding],
    cross_check: CrossCheck,
    legal_index: LegalIndex,
) -> ContractCheckResult:
    # 1. Enrich each finding with legal basis (NEW)
    enriched = []
    for f in pattern_findings:
        query = f"{f.title}. {f.explanation}"
        citations = await legal_index.search(query, k=2, threshold=0.50)
        f.legal_basis = citations  # may be empty
        enriched.append(f)

    # 2. Synthesize verdict using all evidence (existing, prompt updated)
    verdict = await _llm_synthesize(
        prompt_template="synthesize_contract.txt",
        findings=enriched,
        cross_check=cross_check,
    )
    return verdict
```

The synthesis LLM prompt gets a new instruction:

> *"Each finding may have a `legal_basis` array. Do not invent legal citations. Do not contradict the citations provided. Use them in the recommendation when explaining why this matters legally — translate the citation to plain Spanish. If a finding has no legal_basis, do not fabricate one."*

The synthesis prompt remains "use only the evidence below" — citation enrichment doesn't loosen that constraint, it tightens it.

## 7. Updated Pydantic schemas

```python
# models/findings.py

from pydantic import BaseModel
from typing import Optional

class LegalCitation(BaseModel):
    law_id: str
    law_title: str
    article: str            # "Art. 4"
    quote_es: str           # paraphrased, < 30 words
    url: str                # link to the markdown article anchor
    official_source: str    # "D.O. Nº 35, T.178, 20-02-1958"

class Finding(BaseModel):
    severity: Severity
    title: str
    explanation: str
    evidence: Optional[str] = None
    legal_basis: list[LegalCitation] = []   # NEW

class VerdictBase(BaseModel):
    verdict: Severity
    findings: list[Finding]
    recommendation: str
    legal_summary: Optional[str] = None     # NEW: 2-3 sentence framing
    disclaimer: str = "Esto no es asesoría legal."
```

`legal_summary` is a synthesized sentence like:

> *"Los puntos marcados en amarillo se basan en los Artículos 4 y 24 de la Ley de Inquilinato. La ley exige que el contrato sea por escrito con datos completos del inmueble y limita las causas por las que un arrendador puede terminar."*

Generated by the synthesis LLM using only the citations attached to findings.

## 8. UI changes

Minimal, additive. The existing finding component grows one more expandable row:

```
┌────────────────────────────────────────────────┐
│ ⚠️  Sin mecanismo de fideicomiso               │
│ El contrato no menciona que tu prima quede     │
│ en garantía hasta la entrega.                  │
│                                                │
│ ▸ Evidencia                                    │
│ ▾ Base legal                            [NEW]  │
│   ┌──────────────────────────────────────┐     │
│   │ Ley de Inquilinato — Art. 4         │     │
│   │ "Todo contrato de arrendamiento      │     │
│   │ debe constar por escrito con datos  │     │
│   │ del inmueble..."                    │     │
│   │ → Leer la ley                       │     │
│   └──────────────────────────────────────┘     │
└────────────────────────────────────────────────┘
```

Result screen also gets an above-findings legal summary card:

```
┌────────────────────────────────────────────────┐
│ ⚖️  Base legal de este resultado               │
│ Tus alertas se basan en la Ley de Inquilinato  │
│ (Art. 4, Art. 24) y la Ley del FSV (Art. 55). │
│                                                │
│ ▾ Ver leyes referenciadas                      │
└────────────────────────────────────────────────┘
```

For WhatsApp, citations are appended after the bullet list (max 3 to stay readable):

```
⚠️ Hay algo que revisar

Encontramos esto:
• Sin mecanismo de fideicomiso
• Fecha de entrega vaga
• El vendedor no coincide con el desarrollador

Base legal: Ley de Inquilinato Art. 4, Ley del
FSV Art. 55, Código Civil Art. 1308.

Si tienes el contrato, mándamelo en PDF.

Esto no es asesoría legal.
```

## 9. Pattern catalog upgrade

Each pattern in `patterns.yaml` gets two new fields:

```yaml
- id: no_escrow
  title: "Sin mecanismo de fideicomiso"
  severity_if_missing: yellow
  prompt: |
    ¿El contrato menciona que la prima o el dinero del comprador queda
    en fideicomiso (escrow) hasta que se entregue la propiedad? ...
  # NEW
  legal_tags: [escrow, fideicomiso, garantia_compraventa]
  preferred_law: ley-inquilinato
  preferred_articles: [art-4]
```

`legal_tags` boost retrieval — chunks with matching tags get priority over pure semantic similarity.

`preferred_law` / `preferred_articles` are an explicit hint when the pattern was crafted with specific articles in mind. The retriever still searches broadly but elevates the preferred ones if they pass the threshold. Useful when the LLM-detected finding text is ambiguous but the pattern's intent is precise.

## 10. Project-level legal grounding (Flow 1)

Flow 1 isn't just about reputation anymore. The same legal layer applies, and the **Ley de Urbanismo y Construcción (D.L. 232 of 1951, last reformed 2021)** is the central law for everything Flow 1 verifies. It is the law behind every permit number on every Salvadoran billboard.

The patterns the existing flow already targets — extracting `permit` from the photo, doing a regex format check, surfacing it in the verdict — all map cleanly to articles in this law. Concretely:

- **`permit_required`** → cite art. 1, 2, 5. No project can advance without prior approval from Ministerio de Vivienda or the relevant municipality.
- **`permit_authority_unclear`** → cite art. 1. The authority must be recognizable (Ministerio de Vivienda, OPAMSS for AMSS, or municipal).
- **`permit_format_invalid`** → cite art. 1, 2. The regex check the BE already does is the operational form of this.
- **`permit_expired`** → cite art. 6. Approvals last only one year if work hasn't started.
- **`developer_not_licensed_architect`** → cite art. 4, 8. The responsible professional must be inscribed in the Registro Nacional de Arquitectos, Ingenieros, Proyectistas y Constructores. This registry is queryable.
- **`urbanization_park_math_inconsistent`** → cite art. 2(e). 10% of useful area for parks is a hard requirement; if the advertised lot count exceeds what's geometrically possible after the reservation, flag.
- **`industrial_no_safety_clearance`** → cite art. 8 final paragraph. Factories/workshops need Previsión Social clearance.

Other Flow 1 checks already in the architecture stay grounded in their respective laws:

- **`developer_not_in_RUPES`** → cite Ley de Compras Públicas (the developer claims a government project but isn't a registered State provider)
- **`property_under_bien_de_familia`** → cite Ley IVU art. 3 (transfer attempt is null)
- **`fsv_anotacion_preventiva_active`** → cite Ley FSV art. 55 (FSV has retroactive priority on this property)
- **`lotificacion_unregularized`** → cite the lotificaciones law (when corpus is filled in)

Some of these checks (RUPES, Registro de la Propiedad, FSV public records, Registro Nacional de Arquitectos) require external API or scraping integrations. For MVP, they're flagged as "planned checks" in the result screen — visible to the user as future enhancements, citable but not yet automatic. Engineer C's curation work in `patterns.yaml` should add these as `planned: true` patterns so the prompt can mention them without claiming verification.

## 11. New panic buttons

Adding to the existing risk list in `ARCHITECTURE.md` §6:

**R7: Legal corpus retrieval is wrong (cites art. 24 when art. 4 was relevant).**
Trigger: regression test set on 20 fixture findings shows < 70% top-1 article accuracy.
**Panic button:** Skip enrichment for that finding, ship with empty `legal_basis`. The finding still appears, just without citation. Tighten threshold from 0.50 to 0.65 to prefer silence.

**R8: Embedding model too slow at request time (>1s for 5-finding contract).**
Trigger: P95 latency spike past 3s for `/check-contract`.
**Panic button:** Pre-embed all chunks at startup (already the plan), and run finding queries in parallel via `asyncio.gather`. If still slow, switch to keyword-tag-only retrieval (no embedding query) — coarser but constant-time.

**R9: User finds a citation that's wrong (false legal claim).**
Trigger: a single user-reported false citation.
**Panic button:** The citation is rendered with a "Reportar error" link that creates a GitHub issue. The corpus is open. The PR fix is the cure. Within 24 hours of merge + redeploy, the system stops citing that article. Disclaimer ("esto no es asesoría legal") covers Casa Segura's liability while the fix lands.

## 12. Updated team plan delta

Adds to the existing team allocation in `ARCHITECTURE.md` §7:

| Person | Existing | Adds |
|---|---|---|
| **A** (Python/ML) | BE, OpenRouter, pipelines | `legal_index` service, embedding choice, retrieval tuning |
| **B** (FE) | Next.js, v0, web | `LegalCitation` component (expandable card), legal summary card, "Reportar error" UX |
| **C** (Integration/Content) | Zavu, blacklist, patterns, README | Legal corpus curation: filling in articles, marking `relevance_to_casa_segura`, fetching the pendiente files |

Engineer C's curation work is the single most leveraged effort here. Five hours of structuring `patterns.yaml` with `legal_tags` and `preferred_articles` produces dramatically better citations than any retrieval tuning. This is the highest-leverage work in the enhancement.

## 13. Revised timeline (delta only)

| Hours | New milestone | Owner |
|---|---|---|
| 0–6 | Curate 5 law markdown files (this corpus + 2 pendientes) | C |
| 6–18 | `legal_index` service: load, chunk, embed, search; integration tests on 20 fixture queries | A |
| 18–30 | Wire into verdict synthesis; update prompt; add `legal_basis` to schema | A |
| 18–30 | `LegalCitation` UI component + result screen card | B |
| 30–42 | Fill in pendientes + add 5–10 article-level tags to `patterns.yaml` | C |
| 30–42 | WhatsApp formatting includes citations (max 3) | C + A |

If we hit the existing R5 (drop Flow 2) panic button, **Flow 1 keeps the legal layer** — bien-de-familia checks and RUPES verification are pitched as the v1.5 differentiator.

## 14. What this is explicitly NOT

- **Not a legal advice engine.** Casa Segura cites laws; it does not interpret cases or apply jurisprudence. The disclaimer remains on every screen and message.
- **Not a substitute for an abogado.** The output makes the conversation with a lawyer cheaper — the user walks in with citations rather than vibes. That's the point.
- **Not a permit verifier.** OPAMSS / CNR / FSV / RUPES integrations remain out of scope for MVP per the existing §11 — they're called out in flagged findings as "to verify, please check at [...]" but not auto-checked yet.
- **Not jurisprudence-grounded.** Court decisions add a layer of precedent, but for v1, the corpus is statute-only. Adding curated CSJ rulings is a real v2 conversation — the structure already supports it (add a `jurisprudence/` directory parallel to `laws/` and the indexer ingests both).

## 15. Privacy implications (delta)

The legal layer is **read-only and stateless**. It adds nothing to the logged data. The same privacy posture (timestamps, verdict, finding count, never developer name or contract content) holds.

One subtlety: the *finding text* sent to the embedding model is the LLM-derived finding, not the contract text. Even so, the finding can leak details (e.g. "El contrato no menciona el predio en Santa Tecla La Libertad"). The mitigation: **strip identifiers from the query before embedding**. The `legal_index.search` function applies a small regex pass over the query that removes proper nouns matching the extracted developer/project/address from Flow 1 (already in session). The embedding model only sees the legal pattern, never the user's data.

## 16. Open source posture (delta)

The legal corpus is the most contribution-friendly part of the project. PR templates added to `.github/`:

- **New law PR template:** law_id, decreto, source URL, signed-off by reasoning about why it's relevant.
- **Article correction PR template:** law_id, article ID, current paraphrase, proposed paraphrase, link to current Diario Oficial.

A `LEGAL-CONTRIBUTORS.md` lists Salvadoran lawyers and law students who have signed off on each file. This is the actual trust model. The code being open is necessary but not sufficient — the citations need community verification by people with legal training.

## 17. Out-of-scope for this enhancement (explicit)

- Custom-trained Spanish-legal embedding models. (Off-the-shelf multilingual is fine for the MVP corpus size.)
- Article-level versioning (showing how a law changed over reforms). (The frontmatter records `ultima_reforma`, but diffing is v2.)
- Translation to English. (Spanish only; the audience is Salvadoran.)
- Real-time integration with Diario Oficial publication feeds. (Manual updates suffice when a relevant law passes.)
- Multi-jurisdiction (other Central American countries). (El Salvador only, same as the rest of the product.)

## 18. Decision summary

Two questions, two answers, citable now.

The MVP went from:

> "🟡 Hay algo que revisar"

to:

> "🟡 Hay algo que revisar
> Tu contrato no especifica los datos del inmueble, lo que el Art. 4 de la Ley de Inquilinato exige. Esto no es asesoría legal — pero es algo concreto para llevarle a un abogado o exigirle al desarrollador antes de firmar."

The user goes from a vibe to a sentence they can paste into a WhatsApp to their abogada. That's the whole win.
