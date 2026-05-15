# PRD: F4 — Rubric Engine & Score Computation

**Version:** 1.0
**Status:** Approved for development
**Author:** Product Team
**Date:** 2026-05-10
**Depends on:** F2 (Classification), F3 (Corpus/RAG), F5 (Economic Analysis), F8 (database schema base)
**Blocks:** F6 (Report Generation)

---

## 1. Problem Statement

The rubric engine is the product's functional heart. It takes the classified contract, runs the 38 criteria defined in the rubric (`RUBRICA_CONTRATO.md`), produces a normalized 0–10 score with band (green/yellow/red), generates a finding list prioritized by severity, and detects critical overrides that force the red band regardless of the average.

The feature is functionally dense but structurally simple: execute each applicable criterion against the contract text, assign a score to each, anchor it to the correct legal basis via F3, compute the weighted average with renormalization when some criteria do not apply, and emit the result in a format F6 can consume.

The specific challenges are five. First, each criterion has its own 0–10 scale with specific textual criteria that the LLM must apply consistently. Second, penalty is asymmetric: conditions favorable to the buyer never degrade the score. Third, unverifiable criteria add the worst case, not the best. Fourth, overrides are binary but take priority over the average; the system must run them first and, if any fires, force the result regardless of the rest. Fifth, the system must strictly respect the cite-or-stay-silent discipline: if F3 returns no citation for a finding, the finding is emitted without citation and labeled `market_based` or `unverifiable`, without the LLM inventing it.

---

## 2. Scope

**In scope:**

- Evaluation of the 38 criteria defined in `RUBRICA_CONTRATO.md` (summarized by category in §3)
- Filtering of criteria by the detected contract type (a criterion may not apply to certain types)
- Assignment of 0–10 score per criterion per the scale defined in `Criterion.scoring_scale`
- Detection of unverifiable criteria and assignment of the worst case
- Detection of the 11 critical overrides defined in the rubric
- Generation of findings for each criterion that does not score perfectly, with assigned severity
- Anchoring of findings to the legal corpus via F3 (cite or stay silent)
- Computation of category scores with renormalization when some criteria do not apply
- Computation of the weighted total score and band assignment
- Override of the total score to red when there are active critical overrides
- Generation of actionable per-finding recommendations
- Persistence of the complete analysis in `ContractAnalysis`
- Rubric versioning for reproducibility

**Out of scope:**

- Defining or modifying the 38 criteria (that is product work in `RUBRICA_CONTRATO.md`)
- Curating the legal corpus (that is F3)
- Computing derived economic metrics (that is F5; F4 consumes them)
- Generating the HTML/PDF report (that is F6)
- Redelivering the analysis (that is F7)
- Manual override of scores by user or admin
- Appeals or disputes over findings
- Proactive suggestions to the seller (the report talks to the user, not the seller)
- Comparing the analysis against other external analyzers
- Predictive analysis of seller behavior

---

## 3. User Stories

### US-01: System evaluates each applicable criterion

**As the** system,
**I want to** evaluate each rubric criterion applicable to the detected contract type,
**So that** a substantiated per-criterion score is produced.

**Acceptance criteria:**

- The system reads the active `RubricVersion` and filters `Criterion` rows whose `applicable_types` includes the analysis's `contract_type`
- For each applicable criterion, the system invokes the LLM with the criterion's prompt template (defined in `Criterion.evaluation_prompt`) and the contract text
- The system gives the LLM access to (a) the contract text, (b) the `elements_detected` flags F2 produced, (c) the economic fields F2 and F5 already extracted and computed
- The LLM produces a structured result: `score` (0-10), `unverifiable` (bool), `justification` (text), `evidence_snippet` (cited clause from contract if any)
- If `unverifiable=true`, the score the system uses is `Criterion.worst_case_when_unverifiable`, not the LLM's
- The system persists each evaluation in `ContractAnalysis.criterion_evaluations`
- Evaluations run in parallel respecting a configurable concurrency limit (default 8) to not saturate the LLM
- The per-criterion timeout is 30 seconds
- If an evaluation fails, it is retried once; if it fails again, the criterion is marked `unverifiable` with `worst_case_when_unverifiable`

**Structured LLM output per criterion:**

```json
{
    "criterion_id": "B2",
    "score": 2.0,
    "unverifiable": false,
    "justification": "The contracted rate is 18% effective annual, computed on the outstanding total balance (not on outstanding principal). This is 9 percentage points above the market benchmark (9% annual) and violates Art. 12 LPC regarding the computation base.",
    "evidence_snippet": "Cláusula 6.2: Las cuotas mensuales devengarán intereses a la tasa del 1.5% mensual, calculados sobre el saldo total adeudado.",
    "override_triggered": "art_12_lpc",
    "should_emit_finding": true,
    "finding_severity": "critical"
}
```

---

### US-02: System detects critical overrides

**As the** system,
**I want to** detect the 11 override conditions before and during criterion evaluation,
**So that** a contract with a void clause does not come out "fine" by being averaged with met criteria.

**Acceptance criteria:**

- The 11 overrides are defined in the `OverrideCode` enum in DOMAIN_MODEL
- Some overrides are detected during the evaluation of a specific criterion (e.g. `art_1644_cc` in C5)
- Others can be detected independently with a special pass (e.g. `art_5_lpc_non_waivable` may apply to any clause)
- The system maintains a list of active overrides for the analysis
- When a criterion detects an override, the system:
  - Sets the criterion's score to 0
  - Adds the override code to `ContractAnalysis.override_triggered`
  - Generates a finding with severity `critical`
- If at least one override is active at the end of evaluation, the system forces:
  - `score_total = 0.0`
  - `band = 'red'`
  - The override's finding is shown first in the report
  - Other findings still display, but the report states "this contract has an absolute nullity or very serious infraction; the other points are secondary to the override"

**The 11 overrides and their triggers:**

| Code | Contract trigger | Associated criterion |
|---|---|---|
| `art_1605_cc` | Sale of real property in a simple private document without public deed | A1 |
| `art_1613_cc` | Price left to the discretion of one party | A3 |
| `art_1644_cc` | Bad-faith waiver of eviction warranty | C5 |
| `art_1425_cc` | Promise to sell without a term or condition fixing the time | A6 |
| `art_3_ivu_family_homestead` | Attempt to transfer property under Bien de Familia regime without cancellation | D2 |
| `art_5_lpc_non_waivable` | Waiver of non-waivable rights of the consumer or tenant | E1 |
| `art_12_lpc` | Late interest computed on total balance, not on outstanding principal | B7 |
| `art_13_lpc` | Unilateral modification of price or conditions by the provider | B9 |
| `art_18_lpc_blank_signature` | Imposition to sign blank promissory notes or drafts | E6 |
| `art_17h_lpc_arbitration` | Arbitration imposed in adhesion contract | E7 |
| `art_58_fsv` | FSV annotation not disclosed with intent to sell | D3 |

---

### US-03: System anchors each finding to the legal corpus via F3

**As the** system,
**I want to** invoke F3 for each emitted finding and obtain the corresponding legal citation,
**So that** each report finding is defensible with a reference to a specific article.

**Acceptance criteria:**

- Each `Finding` generated by criterion evaluation is processed by F3
- F4 invokes `f3.retrieve_legal_basis()` with: `finding_text=finding.description`, `corpus_version=analysis.corpus_version`, `prefer_anchors=criterion.legal_anchor`
- F3 may return a list (with at least one result) or an empty list
- If F3 returns results, F4 inserts them into `Finding.legal_basis` (max 3 references)
- If F3 returns an empty list, F4 leaves `Finding.legal_basis = []` and adds the tag `unverifiable` or `market_based` depending on the criterion
- F4 never fills `legal_basis` with invented or nearby citations
- The LLM prompt in F4 explicitly forbids generating legal references; it only uses those F3 passes it
- For criteria with explicit `legal_anchor` defined in `Criterion`, F3 prioritizes those anchors

**Tagging of citation-less findings:**

- If the criterion has `legal_anchor` defined but F3 returned empty: tag `unverifiable_legal`
- If the criterion does NOT have `legal_anchor` defined (it is market-based, not law-based): tag `market_based`
- These tags are shown in the report and indicate the type of grounding to the user

---

### US-04: System computes category scores with renormalization

**As the** system,
**I want to** compute each category score as the weighted average of applicable criteria,
**So that** categories with criteria that do not apply to the contract type are not distorted.

**Acceptance criteria:**

- For each category (A, B, C, D, E, F), the system computes:
  - `criteria_count_total`: total criteria defined in the category
  - `criteria_count_applicable`: criteria applicable to the current contract type
  - `criteria_count_unverifiable`: criteria marked unverifiable
  - `score_category`: weighted average of the scores of applicable criteria
- Renormalization works as follows:
  - Let `W_i` be the weight of criterion `i` in the category per the rubric
  - Let `S_i` be the score of criterion `i` (0-10), including worst case for unverifiable
  - Let `A` be the set of criteria applicable to the type
  - `score_category = sum(W_i * S_i for i in A) / sum(W_i for i in A)`
- The result is persisted as a `CategoryScore` object inside `ContractAnalysis.scores_by_category`
- If NO criteria of a category apply to the contract type, the category is omitted from the total-score computation (it is not treated as "category = 0")

---

### US-05: System computes the total score with category renormalization

**As the** system,
**I want to** combine the six category scores into a final 0–10 score,
**So that** the user receives a single number that summarizes the contract.

**Acceptance criteria:**

- Global category weights (defined in the rubric):
  - A: 20%, B: 30%, C: 20%, D: 15%, E: 10%, F: 5%
- If all categories have applicable criteria, the computation is direct:
  - `score_total = sum(weight_global_i * score_category_i for i in [A,B,C,D,E,F])`
- If a category has no applicable criteria, weights renormalize:
  - `weight_effective_i = weight_global_i / sum(weight_global_j for j with applicable criteria)`
  - `score_total = sum(weight_effective_i * score_category_i for i with applicable criteria)`
- The score is rounded to one decimal
- If overrides are active, it is overwritten to 0.0 regardless of the prior computation
- The band is assigned per the final `score_total`:
  - 8.0–10.0 → `green`
  - 5.0–7.9 → `yellow`
  - 0.0–4.9 → `red`
- If an override is active, the band is always `red`

---

### US-06: System produces severity-prioritized findings

**As the** system,
**I want to** produce a list of findings ordered by severity,
**So that** the report displays the most important problems first.

**Acceptance criteria:**

- Each criterion with score < 10 produces a finding
- Each finding has assigned severity:
  - `critical`: criterion with active override, or detected absolute nullity
  - `red`: criterion with score 0-3 without override
  - `yellow`: criterion with score 4-6
  - `green`: criterion with score 7-9 (minor observation)
  - `unverifiable`: criterion that could not be evaluated
- Findings sort order: critical, red, yellow, green, unverifiable
- Within each severity, sorted by global criterion weight (higher weight first)
- Each finding contains: id, severity, title, description, evidence_snippet, legal_basis, recommendation, related_criterion_id
- `description` and `recommendation` are LLM-generated during criterion evaluation
- `evidence_snippet` is the cited contract clause (if the LLM identified one)
- Findings are persisted in `ContractAnalysis.findings`

**Recommendations per criterion:**

Each recommendation must be actionable and specific. Examples:

- B2 (rate out of market): "Ask the seller to lower the rate to the market range (8-10% annual) and to express it as effective annual rate, not monthly."
- C1 (no escrow): "Before handing over the down payment, ask the seller to place the amount in a bank escrow or joint account, releasable only against delivery of the deed."
- E1 (rights waiver): "The clause waiving [specific right] is void under Art. 5 LPC. Ask the seller to remove it from the contract before signing."

---

### US-07: System persists the complete analysis

**As the** system,
**I want to** persist the entire analysis result in `ContractAnalysis`,
**So that** F6 can generate the report and F8 can associate it to the Project.

**Acceptance criteria:**

- The system completes all `ContractAnalysis` fields under its scope:
  - `score_total`, `band`, `override_triggered`
  - `scores_by_category` (array of `CategoryScore`)
  - `criterion_evaluations` (array of `CriterionEvaluation`)
  - `findings` (array of `Finding`)
  - `findings_count`, `critical_findings_count`, `unverifiable_count`
  - `rubric_version`, `corpus_version`, `benchmark_version`
  - `processing_completed_at`
- Persistence is atomic: all or nothing
- If persistence fails, the analysis is marked `failed_analysis` with reason

---

### US-08: System produces an executive summary for the report

**As the** system,
**I want to** generate a 2–3 sentence summary of the analysis,
**So that** the report has a user-comprehensible synopsis.

**Acceptance criteria:**

- The summary is generated with a final prompt that receives: score, band, finding count per severity, active overrides, contract type, economic summary
- The summary must be:
  - 2 to 3 sentences max
  - Clear, "tú" register
  - No legal jargon
  - Honest about severity
  - Action-conducive
- Examples (delivered in Spanish):
  - Green: "Este contrato de compraventa luce favorable para tu bolsillo y dentro de la ley. La tasa, el plazo y la prima están en línea con el mercado. Aún así, llévalo a un abogado antes de firmar."
  - Yellow: "Este contrato tiene cifras dentro del mercado pero algunas cláusulas necesitan negociación. La penalidad por mora y el manejo de la prima son los puntos a corregir antes de firmar."
  - Red: "Este contrato te expone a riesgo serio. La tasa está muy por encima del mercado y hay cláusulas que la ley salvadoreña considera nulas. No firmes sin asesoría legal y exigir cambios."
  - Red with override: "Este contrato contiene una cláusula que la ley salvadoreña declara nula (Art. X de la Ley Y). Independientemente de las demás cifras, no firmes hasta corregir esto."

---

## 4. Business Rules

**BR-01:** The engine evaluates only criteria whose `applicable_types` includes the analysis's `contract_type`. Non-applicable criteria do not enter the computation (they are not averaged as zero).

**BR-02:** Penalty is asymmetric. Each criterion's scale explicitly defines that values favorable to the buyer score 10 (no penalty for exceeding the benchmark on the favorable side).

**BR-03:** Unverifiable criteria add the worst case defined in `Criterion.worst_case_when_unverifiable`, not the best. This follows the PRD principle: better a false negative than a false positive.

**BR-04:** Critical overrides force the final score to 0 and the band to red, regardless of the weighted average. This is invariant.

**BR-05:** Findings without legal citation (because F3 returned empty) are labeled `unverifiable_legal` or `market_based` and are included in the report. The LLM does not invent citations.

**BR-06:** The LLM evaluates one criterion at a time, not several in one call. This allows per-criterion prompt tuning, improves reproducibility, and isolates failures.

**BR-07:** Evaluations run with `temperature=0.1` and fixed `seed` when the model supports it. This maximizes reproducibility of repeated evaluations on the same contract.

**BR-08:** Per-criterion evaluation concurrency is capped at 8 simultaneous to avoid saturating the LLM. Configurable.

**BR-09:** The complete analysis (all criteria + score + findings) must finish in under 60 seconds P95. If exceeded, it is canceled and marked `failed_analysis` with reason `TIMEOUT_EXCEEDED`.

**BR-10:** The `rubric_version` persisted in the analysis is the one used. Re-evaluating the same contract with a new rubric version creates a new analysis, it does not update the previous one.

**BR-11:** The rubric engine never asks the user for clarifications. If a criterion cannot be evaluated, it is marked unverifiable. There is no conversational flow.

**BR-12:** Each finding has exactly one associated criterion (`related_criterion_id`). One criterion may generate one or zero findings (0 if score=10). There are no findings disconnected from criteria.

**BR-13:** Recommendations are actionable and specific to the analyzed contract. They are not generic text. The LLM generates them based on contract evidence.

**BR-14:** The rubric engine never evaluates criteria about seller or developer behavior outside the contract. It only evaluates the document.

**BR-15:** When F5 detects that an economic value is unverifiable (because F2 did not extract it from the contract), the economic criteria depending on that value are marked unverifiable. F4 passes them with worst case without invoking the LLM.

**BR-16:** The `evidence_clause_snippet` F4 produces inside each `Finding` is a textual fragment of the contract. It is the only way contract content persists, embedded inside the JSONB `findings` of `contract_analysis`. This snippet is fully subject to F8's 90-day anonymization policy: after anonymization, snippets are reduced to a label such as "extract omitted by retention policy" and only the finding metadata (severity, related criterion, score) is preserved. The snippet must never exceed 500 characters per finding; if the relevant clause is longer, F4 truncates with ellipses preserving the critical context.

---

## 5. Data Models

### 5.1 Criterion catalog (defined in F8, populated when installing the rubric version)

```sql
CREATE TABLE criterion (
    id TEXT NOT NULL,
    rubric_version TEXT NOT NULL,

    category CHAR(1) NOT NULL CHECK (category IN ('A','B','C','D','E','F')),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    weight_in_category NUMERIC(4,2) NOT NULL CHECK (weight_in_category > 0 AND weight_in_category <= 100),

    applicable_types TEXT[] NOT NULL,
    legal_anchor TEXT[] NOT NULL DEFAULT '{}',
    override_code TEXT,

    evaluation_prompt TEXT NOT NULL,
    scoring_scale JSONB NOT NULL,
    worst_case_when_unverifiable NUMERIC(3,1) NOT NULL DEFAULT 4.0,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (id, rubric_version)
);

CREATE INDEX idx_criterion_rubric_version ON criterion(rubric_version);
CREATE INDEX idx_criterion_category ON criterion(category);
CREATE INDEX idx_criterion_applicable_types ON criterion USING GIN(applicable_types);
```

### 5.2 RubricVersion catalog (defined in F8)

```sql
CREATE TABLE rubric_version (
    version TEXT PRIMARY KEY,
    released_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    criteria_count INTEGER NOT NULL,
    categories JSONB NOT NULL, -- weights per category
    changelog TEXT,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_rubric_version_active ON rubric_version(is_active) WHERE is_active = TRUE;
```

### 5.3 Updates to `contract_analysis` written by F4

```sql
-- F4 writes these columns in contract_analysis (the table is defined in F8)

ALTER TABLE contract_analysis ADD COLUMN IF NOT EXISTS score_total NUMERIC(3,1) CHECK (score_total >= 0 AND score_total <= 10);
ALTER TABLE contract_analysis ADD COLUMN IF NOT EXISTS band TEXT CHECK (band IN ('green', 'yellow', 'red', 'not_analyzable'));
ALTER TABLE contract_analysis ADD COLUMN IF NOT EXISTS override_triggered TEXT[];
ALTER TABLE contract_analysis ADD COLUMN IF NOT EXISTS scores_by_category JSONB;
ALTER TABLE contract_analysis ADD COLUMN IF NOT EXISTS criterion_evaluations JSONB;
ALTER TABLE contract_analysis ADD COLUMN IF NOT EXISTS findings JSONB;
ALTER TABLE contract_analysis ADD COLUMN IF NOT EXISTS findings_count INTEGER DEFAULT 0;
ALTER TABLE contract_analysis ADD COLUMN IF NOT EXISTS critical_findings_count INTEGER DEFAULT 0;
ALTER TABLE contract_analysis ADD COLUMN IF NOT EXISTS unverifiable_count INTEGER DEFAULT 0;
ALTER TABLE contract_analysis ADD COLUMN IF NOT EXISTS executive_summary TEXT;
ALTER TABLE contract_analysis ADD COLUMN IF NOT EXISTS rubric_version TEXT REFERENCES rubric_version(version);
ALTER TABLE contract_analysis ADD COLUMN IF NOT EXISTS corpus_version TEXT REFERENCES corpus_version(version);
```

### 5.4 JSONB field structure

`scores_by_category`:

```json
[
    {
        "category": "B",
        "category_name": "Economic health",
        "weight_global": 0.30,
        "weight_effective": 0.30,
        "score": 4.2,
        "criteria_count_total": 9,
        "criteria_count_applicable": 7,
        "criteria_count_unverifiable": 1
    }
]
```

`criterion_evaluations`:

```json
[
    {
        "criterion_id": "B2",
        "category": "B",
        "applicable": true,
        "evaluated": true,
        "unverifiable": false,
        "score": 2.0,
        "weight_in_category": 0.20,
        "override_triggered": "art_12_lpc",
        "justification": "The contracted rate is 18% annual...",
        "evidence_snippet": "Cláusula 6.2: Las cuotas mensuales devengarán intereses..."
    }
]
```

`findings`:

```json
[
    {
        "id": "F-001",
        "severity": "critical",
        "title": "Late interest on total balance prohibited by Art. 12 LPC",
        "description": "The contract sets late interest on the outstanding total balance, not on the overdue principal. This contradicts Art. 12 LPC, which orders computing interest on outstanding daily balances based on the calendar year.",
        "evidence_clause_snippet": "Cláusula 6.2: Las cuotas mensuales devengarán intereses a la tasa del 1.5% mensual, calculados sobre el saldo total adeudado.",
        "legal_basis": [
            {
                "law_id": "ley-proteccion-consumidor",
                "law_title": "Ley de Protección al Consumidor",
                "article": "Art. 12",
                "anchor": "art-12",
                "paraphrased_quote": "En contratos de compraventa a plazos, los intereses se calculan sobre los saldos diarios pendientes...",
                "official_source": "D.L. 776 de 2005"
            }
        ],
        "recommendation": "Ask the seller to change clause 6.2 so interest is computed on outstanding principal, not on the total outstanding balance.",
        "related_criterion_id": "B2",
        "anchors_to_override": "art_12_lpc",
        "tags": []
    }
]
```

---

## 6. Integration Points

### 6.1 Input: queue from F2

F4 consumes the message published by F2:

```json
{
    "submission_id": "uuid",
    "analysis_id": "uuid",
    "project_id": "uuid",
    "extracted_text": "string (in memory)",
    "classification": { },
    "economic_fields_raw": { },
    "elements_detected": { }
}
```

### 6.2 Parallel input: F5 result

F4 also waits for F5's result before starting economic criteria:

```json
{
    "analysis_id": "uuid",
    "economic_summary": {
        "price_cash": 80000,
        "annual_rate_pct": 0.18,
        "term_months": 240,
        "monthly_payment": 1083.50,
        "total_cost_paid": 268040,
        "benchmark_comparisons": [ ]
    },
    "benchmark_version": "2026-Q2"
}
```

F4 and F5 run in parallel, but the final scoring phase (when the economic value is needed) waits on F5.

### 6.3 Consumes: F3 (Corpus/RAG)

F4 invokes F3 once per emitted finding:

```python
legal_basis = f3.retrieve_legal_basis(
    finding_text=finding.description,
    corpus_version=analysis.corpus_version,
    top_k=3,
    threshold=0.65,
    prefer_anchors=criterion.legal_anchor
)
```

### 6.4 Output: queue to F6

When finished, F4 publishes:

```json
{
    "analysis_id": "uuid",
    "ready_for_report": true,
    "score_total": 2.5,
    "band": "red",
    "override_active": true
}
```

### 6.5 External service: OpenRouter

F4 makes one LLM call per applicable criterion. For a typical CVP contract with ~32 applicable criteria, that is ~32 calls plus one final call for the executive summary.

Configuration:

- `LLM_RUBRIC_MODEL` env var (default `anthropic/claude-sonnet-4`)
- `LLM_RUBRIC_TIMEOUT_PER_CRITERION_SECONDS` env var (default 30)
- `LLM_RUBRIC_CONCURRENCY` env var (default 8)
- `LLM_RUBRIC_TEMPERATURE` env var (default 0.1)
- `LLM_RUBRIC_MAX_RETRIES_PER_CRITERION` env var (default 1)

---

## 7. API Surface

F4 does not expose public HTTP endpoints. It is a queue processor.

For QA, the following is exposed:

### 7.1 `POST /v1/internal/rubric/evaluate-criterion` (requires `X-Internal-Auth`)

Allows testing a specific criterion against a text.

```json
{
    "criterion_id": "B2",
    "rubric_version": "1.0.0",
    "contract_text": "...",
    "contract_type": "CVP",
    "economic_fields": { },
    "elements_detected": { }
}
```

**Response:**

```json
{
    "score": 2.0,
    "unverifiable": false,
    "override_triggered": "art_12_lpc",
    "justification": "...",
    "evidence_snippet": "...",
    "tokens_consumed": 1820,
    "cost_estimate_cents": 5,
    "elapsed_ms": 4100
}
```

### 7.2 `GET /v1/internal/rubric/version/{version}` (requires `X-Internal-Auth`)

Lists criteria of a rubric version.

---

## 8. LLM Prompts

The LLM prompts in F4 are kept in Spanish for the same reason as F2: they instruct the model to interpret Spanish-language Salvadoran contracts using Salvadoran legal vocabulary. The JSON keys returned by the model are in English.

### 8.1 General template for criterion evaluation

The specific prompt for each criterion is stored in `Criterion.evaluation_prompt` and interpolated with contract data. Here is the generic template:

**System:**

```
Eres analista experto en contratos inmobiliarios salvadoreños. Tu tarea es evaluar un criterio específico de una rúbrica contra el texto de un contrato y devolver un score 0-10 con justificación.

Reglas estrictas:
1. Aplica la escala que se te da; no inventes valores intermedios fuera de la escala.
2. Cita literalmente la cláusula del contrato como evidencia (campo evidence_snippet); si no hay cláusula específica, devuelve null.
3. Si no puedes evaluar el criterio porque la información no está en el contrato, marca unverifiable=true. NO inventes.
4. Si detectas la condición que dispara override_code (lo verás en el prompt del criterio), inclúyelo en la respuesta.
5. NO generes referencias a artículos de ley. Solo describe lo que el contrato dice o no dice.
6. La penalización es asimétrica: condiciones favorables al comprador o arrendatario nunca degradan el score.

Devuelve UN ÚNICO objeto JSON con esta estructura:

{
    "criterion_id": "<id of the criterion>",
    "score": <number between 0 and 10>,
    "unverifiable": <bool>,
    "override_triggered": "<override code if applicable, or null>",
    "justification": "<explanation in Spanish, max 3 sentences>",
    "evidence_snippet": "<verbatim contract clause or null>",
    "should_emit_finding": <bool, true if score < 10>,
    "finding_severity": "<critical | red | yellow | green>",
    "recommendation": "<actionable recommendation to the user, 1-2 sentences, in Spanish>"
}
```

### 8.2 Example specific prompt — Criterion B2 (Effective annual interest rate)

**User:**

```
CRITERIO: B2 — Tasa de interés efectiva anual

PESO EN CATEGORÍA: 20%

QUÉ SE BUSCA: La tasa de interés efectiva anual aplicada al saldo financiado. Se compara contra el benchmark de mercado para el segmento.

BENCHMARK: Crédito hipotecario bancario 9% anual. Crédito directo con desarrollador 8-12% anual.

ESCALA (regla: 2% sobre promedio = malo, 5% sobre promedio = grave):
- 10: Tasa ≤ 9% anual
- 9: Tasa 9-10% anual
- 7: Tasa 10-11% anual
- 5: Tasa 11-14% anual (malo)
- 2: Tasa 14-19% anual (grave)
- 0: Tasa > 19% anual o no expresada como anual efectiva

OVERRIDE: Si los intereses se calculan sobre el saldo total adeudado (no sobre capital pendiente), activa override_triggered = "art_12_lpc" y forza score = 0.

DATOS YA EXTRAÍDOS:
- Tasa anual extraída por F2: {{economic_fields.annual_rate_pct.value}}
- Base de cálculo extraída: {{economic_fields.interest_calculation_base.value}}
- Cláusula citada: {{economic_fields.annual_rate_pct.evidence_snippet}}

TEXTO DEL CONTRATO:
{{contract_text}}

Evalúa el criterio.
```

### 8.3 Executive summary prompt

**System:**

```
Eres redactor del reporte de Casa Segura. Tu tarea es escribir un sumario ejecutivo del análisis de un contrato inmobiliario, en español, "tú", calmado y honesto.

Reglas:
1. Máximo 3 oraciones.
2. Lenguaje claro, sin jerga legal.
3. Si hay override activo, debe mencionarlo explícitamente.
4. Si la banda es verde, no inventes problemas; reconoce que el contrato luce bien y recuerda consultar abogado.
5. Si la banda es roja, sé directo pero no alarmista.
6. Cierra con una recomendación accionable: "no firmes sin abogado", "exígele al vendedor X cambios", "este contrato parece bien pero llévalo a abogado".

NO incluyas:
- Citas de leyes específicas (el reporte ya las muestra)
- Cifras numéricas exactas (van en otra sección)
- Pregunta o invitación a responder (es un reporte, no diálogo)

Devuelve solo el texto del sumario, sin marcadores ni metadata.
```

**User:**

```
Datos del análisis:
- Tipo de contrato: {{contract_type}}
- Score: {{score_total}}
- Banda: {{band}}
- Overrides activos: {{override_triggered}}
- Conteo de findings críticos: {{critical_findings_count}}
- Conteo de findings rojos: {{red_findings_count}}
- Sobrecosto económico vs benchmark: {{economic_summary.overcost_vs_benchmark_usd}}

Escribe el sumario ejecutivo.
```

---

## 9. Non-Functional Requirements

- **Full engine P50 latency:** under 40 seconds for a CVP contract with 32 applicable criteria.
- **P95 latency:** under 60 seconds.
- **Throughput:** 20 concurrent analyses in production.
- **Findings-with-legal-citation rate:** over 70% (depends on corpus quality, not only F4).
- **Reproducibility:** same contract + same rubric + same corpus must produce the same score within ±0.2 points.
- **Target cost per analysis:** under $0.30 USD in LLM for criteria + summary.
- **Idempotency:** the same `analysis_id` is not re-evaluated unless an explicit version change occurs.
- **Observability:** Prometheus metrics per criterion: latency, unverifiable rate, override rate, score distribution.
- **Resilience:** circuit breaker over OpenRouter; on persistent failure, mark analysis `failed_analysis` with a clear reason.

---

## 10. Open Questions

1. Should LLM temperature be 0.0 for maximum reproducibility, or 0.1 to allow some useful variation? 0.0 can cause degenerate responses on modern LLM models; 0.1 is safe but introduces variability.

2. Should the engine allow LLM seed override for reproducible tests, or only in QA? Seed does not guarantee total reproducibility across providers (Claude, GPT, etc.) but helps a lot.

3. How many findings should be shown at most in the report? If a contract has 25 findings (worst case), the report becomes overwhelming. Possible cap: show critical + red + top 5 yellow, summarize the rest.

4. Should economic-criterion evaluation wait for F5 before starting, or can non-economic criteria start in parallel? My proposal is parallel with a barrier before finalizing the total score.

5. Should unverifiable findings be shown to the user or only to internal operator? Argument for showing: transparency. Against: noise that distracts from actionable findings.

6. How is corpus paraphrase fidelity to verbatim validated? F4 trusts the paraphrase F3 returns. If the paraphrase has a curation error, F4 emits findings based on incorrect information. Who reviews?

7. Should the engine learn from previous evaluations? For example, if a similar criterion was evaluated in another contract, use that result as a prior? This could improve consistency but introduces dependencies and possible biases. Recommend no in MVP.

8. How are criteria whose `legal_anchor` cites a repealed article handled? The current strategy is that F3 does not return the repealed chunk (marked `status='repealed'` in the corpus). Policy needs confirmation.

---

**End of document.**
