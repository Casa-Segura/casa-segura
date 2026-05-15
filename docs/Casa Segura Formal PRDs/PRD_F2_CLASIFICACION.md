# PRD: F2 — Contract Classification & Structured Extraction

**Version:** 1.0
**Status:** Approved for development
**Author:** Product Team
**Date:** 2026-05-10
**Depends on:** F1 (extracted text), F8 (database schema base)
**Blocks:** F4 (Rubric Engine), F5 (Economic Analysis)

---

## 1. Problem Statement

F1 delivers the contract's plain text. The next pipeline layer needs to answer four concrete questions before the rubric can be evaluated. First, what type of contract it is exactly: a cash purchase is evaluated with different criteria than a lease or a leasing. Second, which real estate project it belongs to, to associate it with the Project entity and accumulate aggregate intelligence. Third, what basic economic figures (total price, down payment, term, rate, monthly payment) appear explicitly in the contract, so the economic layer can compute overcosts and comparisons. Fourth, whether the contract is being presented as one thing while structurally being another: the most common case is "purchase disguised as leasing", the most expensive real estate fraud pattern in the Salvadoran market under Art. 2 of the Financial Leasing Law.

The feature must execute these four tasks with a single LLM step when possible, to minimize cost and latency. It must produce predictable, validatable, traceable structured output. When a contract does not fit any of the eight covered types, it must reject it cleanly with `NOT_CLASSIFIABLE` so the user receives a clear message instead of a fake analysis.

---

## 2. Scope

**In scope:**

- Classification of the contract type into one of the eight covered types (CVC, CVP, ARV, ARC, APV, LEA, IVU, FSV) or `NOT_CLASSIFIABLE`
- Detection of the six Art. 2 LAF indicators for purchase-to-leasing reclassification
- Extraction of the real estate project name as it appears in the contract
- Normalization of the project name to a slug for matching against `Project`
- Creation of `Project` when it does not exist; association when it does
- Extraction of basic economic fields when present: total price, down payment, term, rate, monthly payment, payment periodicity, currency
- Detection of the presence of certain key legal elements that will help F4: warranty clause, mention of Bien de Familia, mention of FSV, promise to sell, mention of urbanism permit
- Production of a structured `ClassificationResult` object consumed by F4 and F5
- Handling of ambiguous contracts: if classification is not reliable, mark the submission `NOT_CLASSIFIABLE` with explicit reason

**Out of scope:**

- Evaluating contract quality or legality (that is F4)
- Computing derived economic figures such as total cost or overcost (that is F5)
- Retrieving articles from the legal corpus (that is F3)
- Verifying the project name against external sources
- Extracting names, DUI, NIT, or addresses of the parties for persistence (they are identified during processing but only the project name is preserved)
- Resolving ambiguities by asking the user (the system decides; if it cannot, it rejects)
- Human reclassification or admin-panel reclassification
- Detection of fraud patterns beyond disguised leasing (others are F4's responsibility)

---

## 3. User Stories

### US-01: System classifies the contract type

**As the** system,
**I want to** assign one of the eight covered contract types to the processed document,
**So that** F4 applies the correct criteria and F5 the correct benchmarks.

**Acceptance criteria:**

- The system invokes an LLM model with the extracted text and the prompts defined in §8.1 and §8.2
- The system expects a structured JSON response with `contract_type`, `confidence`, `indicators_found`, and `reasoning`
- If `confidence` is over 0.85, the classification is accepted as-is
- If `confidence` is between 0.65 and 0.85, the system retries with a validation prompt (§8.3); if the second call agrees with the first, it is accepted
- If `confidence` is below 0.65 or the two calls disagree, the submission is marked `NOT_CLASSIFIABLE`
- The assigned type is stored in `ContractAnalysis.contract_type_declared` (what the document presents itself as)
- If reclassification to leasing applies (see US-03), `ContractAnalysis.contract_type` becomes `LEA` and `contract_type_declared` keeps the original type
- The LLM response is logged in structured logs without including contract text

**Expected LLM structured output:**

```json
{
    "contract_type": "CVP",
    "confidence": 0.92,
    "indicators_found": [
        "The parties are designated 'seller' and 'buyer'",
        "A total price and payment plan are established",
        "The object is a real estate property"
    ],
    "reasoning": "The contract establishes the transfer of a specific property in exchange for a price payable in installments. Matches the Art. 1597 CC definition.",
    "elements_detected": {
        "warranty_clause": true,
        "bien_de_familia_mention": false,
        "fsv_mention": false,
        "urbanism_permit_mention": true,
        "promise_to_sell": false
    }
}
```

---

### US-02: System extracts the real estate project name

**As the** system,
**I want to** extract the real estate project name as it appears in the contract,
**So that** we can associate the analysis with the Project entity and accumulate aggregate intelligence.

**Acceptance criteria:**

- The LLM identifies the project name in the same classification call (§8.2)
- The name is stored as `canonical_name` (as it appears, normalizing whitespace)
- The system produces `normalized_name`: lowercase, no accents, no special characters, no generic words (`proyecto`, `residencial`, `condominio`), no multiple spaces
- The system looks up an existing `Project` with that `normalized_name`
- If it exists, it associates the analysis with the existing `project_id`
- If it does not exist, it creates a new `Project` with the detected `canonical_name` and `normalized_name`
- If the LLM cannot identify a project name, the system generates a placeholder `unknown_<short_hash>` where `short_hash` is the first 8 characters of the `submission_hash`; this Project is marked with `metadata.placeholder=true`
- The system NEVER verifies the name against an external source
- The report always includes the note: "the project name was extracted from the contract; it was not verified against an external source"

**Project name normalization rules:**

- Convert to lowercase
- Remove accents and diacritics (NFD + filter)
- Remove non-alphanumeric characters (except hyphens and spaces)
- Collapse multiple spaces to one
- Remove generic words at start or end positions: `proyecto`, `residencial`, `condominio`, `urbanización`, `lotificación`, `complejo`, `parque`
- Trim leading/trailing spaces
- If the result has fewer than 3 characters, it is considered unextractable and the placeholder is used

**Examples:**

- "Residencial Las Palmeras" → `las palmeras`
- "Proyecto Urbano Cumbres del Volcán" → `urbano cumbres del volcan`
- "CONDOMINIO ARRECIFE 2" → `arrecife 2`
- "Lotificación El Roble" → `el roble`

---

### US-03: System detects purchase-to-leasing reclassification

**As the** system,
**I want to** detect when a contract presented as a purchase contains the structural leasing indicators per Art. 2 LAF,
**So that** the user is warned of the most expensive fraud pattern in the market.

**Acceptance criteria:**

- If the initial classification is CVP, CVC, or APV, the system runs an additional step of leasing indicator detection
- The step uses the prompt defined in §8.4
- The LLM searches for the six Art. 2 LAF indicators in the contract text:
  1. Mandatory term (cannot be cancelled early without penalty equal to the outstanding balance)
  2. Purchase option at a predefined price at the end of the term
  3. The seller declares ownership until the option is exercised (property is retained)
  4. All taxes, fees, fines, and levies on the property fall on the "buyer"
  5. All risks (insurable and non-insurable) fall on the "buyer"
  6. Payments are called "canon" instead of price installments
- If 4 or more of the 6 indicators are detected, the system reclassifies to `LEA`
- On reclassification: `contract_type` becomes `LEA`, `contract_type_declared` keeps the original type, `contract_type_reclassified=true`, `reclassification_reason` contains the verbatim list of found indicators
- If 2 or 3 indicators are detected, no reclassification occurs but it is noted as a warning finding that F4 may turn into a yellow finding
- If 0 or 1 indicators are detected, nothing to report
- Reclassification does NOT apply to contracts originally classified as ARV, ARC, IVU, FSV, or LEA (the latter is already leasing)
- The report always cites the found indicators explicitly: "The contract presents the following Art. 2 LAF indicators that suggest financial leasing instead of purchase: 1. ..., 2. ..., ..."

**Expected LLM structured output for leasing detection:**

```json
{
    "leasing_indicators": {
        "mandatory_term": {"detected": true, "evidence": "Cláusula 8: El contrato no podrá rescindirse antes del plazo de 240 meses sin pago de la totalidad del saldo."},
        "predefined_purchase_option": {"detected": true, "evidence": "Cláusula 12: Al cumplirse el plazo, el comprador podrá ejercer la opción de adquisición por la suma simbólica de $100."},
        "ownership_retained": {"detected": true, "evidence": "Cláusula 3: El comprador no adquirirá la propiedad del inmueble hasta el ejercicio de la opción de compra."},
        "taxes_to_buyer": {"detected": true, "evidence": "Cláusula 9: Todos los impuestos, tasas, multas y contribuciones que graven el inmueble correrán por cuenta del comprador."},
        "risks_to_buyer": {"detected": true, "evidence": "Cláusula 10: Los riesgos asegurables y no asegurables del inmueble son por cuenta exclusiva del comprador."},
        "payments_as_rent": {"detected": false, "evidence": null}
    },
    "indicators_count": 5,
    "should_reclassify": true,
    "reclassification_severity": "high"
}
```

---

### US-04: System extracts basic economic fields

**As the** system,
**I want to** identify and extract the basic economic figures present in the contract,
**So that** F5 can perform derived computations and benchmark comparisons.

**Acceptance criteria:**

- The system invokes the economic extraction prompt (§8.5) on the contract text
- It is only invoked if `contract_type` is CVP, APV, LEA, FSV, or ARV (types with relevant economic figures)
- The system extracts the available fields:
  - `price_cash`: cash price or total declared price
  - `currency`: currency (USD by default in El Salvador, unless colones are indicated)
  - `down_payment`: down payment or advance amount
  - `down_payment_pct`: percentage when expressed that way
  - `financed_amount`: financed amount
  - `term_months`: term in months
  - `annual_rate_pct`: effective annual rate as percentage
  - `monthly_payment`: monthly installment
  - `monthly_rate_pct`: monthly rate when only that one appears
  - `payment_periodicity`: monthly, biweekly, weekly, other
  - `interest_calculation_base`: "outstanding_principal" | "total_balance" | "unspecified"
- Each extracted field includes `confidence` (0 to 1) and `evidence_snippet` (the contract sentence backing it)
- If a field does not appear in the contract, it is marked `null` with `extraction_status='not_present'`
- If a field appears but is ambiguous, it is marked with `extraction_status='ambiguous'` and the system does not use it
- Extracted fields are NOT persisted directly; they are passed in memory to F5, which processes them and produces `EconomicSummary` (which is persisted)
- If the `interest_calculation_base` is `total_balance`, the system notes a potential override (`art_12_lpc`) that F4 will evaluate

**Expected LLM structured output for economic extraction:**

```json
{
    "price_cash": {"value": 80000, "currency": "USD", "confidence": 0.95, "evidence_snippet": "Cláusula 4: El precio total del inmueble es de OCHENTA MIL DÓLARES exactos (USD 80,000.00)."},
    "down_payment": {"value": 8000, "currency": "USD", "confidence": 0.92, "evidence_snippet": "...prima del 10% pagadera al momento de firmar..."},
    "down_payment_pct": {"value": 0.10, "confidence": 0.99, "evidence_snippet": "...prima del diez por ciento (10%)..."},
    "term_months": {"value": 240, "confidence": 0.88, "evidence_snippet": "...plazo de veinte años..."},
    "annual_rate_pct": {"value": 0.18, "confidence": 0.75, "evidence_snippet": "...tasa del 1.5% mensual...", "extraction_note": "converted from monthly to effective annual"},
    "monthly_payment": {"value": 1083.50, "currency": "USD", "confidence": 0.91, "evidence_snippet": "...cuotas mensuales de mil ochenta y tres dólares con cincuenta centavos..."},
    "interest_calculation_base": {"value": "total_balance", "confidence": 0.85, "evidence_snippet": "...intereses calculados sobre el saldo total adeudado..."}
}
```

---

### US-05: System identifies key legal elements (without persisting party data)

**As the** system,
**I want to** detect the presence of certain legal elements in the contract without extracting personal data,
**So that** F4 can prioritize the evaluation of relevant criteria.

**Acceptance criteria:**

- The system produces an `elements_detected` flag map with `true`/`false` for each element
- The elements to detect are:
  - `warranty_clause`: there is an eviction/warranty against defects clause
  - `warranty_exemption_clause`: there is a warranty exemption clause (potential override `art_1644_cc`)
  - `bien_de_familia_mention`: the contract mentions Bien de Familia, IVU adjudication, or historical institutional housing
  - `fsv_mention`: the contract mentions the Fondo Social para la Vivienda
  - `urbanism_permit_mention`: the contract cites an urbanism and construction permit
  - `promise_to_sell`: the contract is a promise to sell or contains a promise
  - `public_deed`: the contract is or is made via public deed before a notary
  - `arbitration_clause`: there is an arbitration clause
  - `blank_signature`: the contract requires signing a promissory note, draft, or other document in blank
  - `rights_waiver`: there is an explicit rights-waiver clause
  - `unilateral_modification`: there is a clause permitting unilateral modification
  - `late_interest_on_total_balance`: late interest is computed on the total balance (not outstanding principal)
- Each flag is accompanied by `evidence_snippet` with the clause that supports it
- These flags are NOT persisted directly; they are passed to F4 as hints to prioritize the evaluation of related criteria
- F4 re-evaluates the contract with its own prompt; flags are acceleration, not decision

---

### US-06: System handles non-classifiable contracts

**As the** system,
**I want to** cleanly reject contracts that do not fit the eight covered types,
**So that** the user receives a clear message instead of an incorrect analysis.

**Acceptance criteria:**

- If the classifier `confidence` is below 0.65 after two attempts, the submission is marked `NOT_CLASSIFIABLE`
- If the LLM responds with `contract_type='NOT_CLASSIFIABLE'`, it is accepted directly
- The system notifies the user with a specific message depending on the channel:
  - Web: "No pudimos clasificar tu documento como un contrato inmobiliario cubierto por Casa Segura. Cubrimos compraventa, arrendamiento, leasing, y contratos institucionales IVU/FSV de inmuebles en El Salvador."
  - WhatsApp: the same message, more concise
- The specific reason is logged: the candidate `contract_type` with lowest confidence, detected elements, and the LLM's textual justification
- The system does NOT return a partial analysis or "try anyway"
- The user can resubmit another document without penalty

**Contract types rejected with `NOT_CLASSIFIABLE`:**

- Permutations (swaps)
- Donations (onerous or gratuitous)
- Assignments of rights
- Mortgages as standalone instrument
- Pre-judicial or procedural documents
- Resolutions, opinions, cancellation deeds
- Offer letters, MOUs, intentions
- Any other document

---

## 4. Business Rules

**BR-01:** Contract classification is strict: only nine possible outcomes (eight types + NOT_CLASSIFIABLE). The system does not produce compound or intermediate types.

**BR-02:** Reclassification detection to leasing only applies when the initial type is CVC, CVP, or APV. For other types, reclassification is not executed.

**BR-03:** Reclassification to leasing requires at least 4 of the 6 Art. 2 LAF indicators. The threshold is strict; 3 indicators are not enough but are noted as a yellow finding in F4.

**BR-04:** Personal data of the parties (names, DUI, NIT, address) is identified during processing if present in the text but is NEVER persisted in the database. Only the real estate project name is preserved.

**BR-05:** The project name is normalized before being used for matching. Two contracts with "Residencial Las Palmeras" and "RESIDENCIAL LAS PALMERAS" are associated with the same Project because both normalize to `las palmeras`.

**BR-06:** If project name extraction fails, the system uses a placeholder `unknown_<short_hash>` and creates a Project specific to that submission. These placeholder Projects are not reused between distinct submissions.

**BR-07:** Economic fields extracted by F2 are raw input; F5 is responsible for validating them, normalizing units, and converting between representations (monthly to annual, fractional percentage to percentage points, etc.).

**BR-08:** If the LLM extracts a monthly rate but not annual, F2 records both: the monthly as `monthly_rate_pct`, and the derived annual as `annual_rate_pct` with explicit note "converted from monthly". The conversion assumes monthly compounding: `annual = (1 + monthly)^12 - 1`.

**BR-09:** Legal-element flags are hints for F4, not decisions. F4 re-evaluates each criterion with its own prompt and may contradict F2's flags if it finds different evidence.

**BR-10:** If classification takes more than 30 seconds at P95, it is considered a feature failure and is retried. If the second attempt also fails, the submission is marked `failed_classification`.

**BR-11:** LLM calls use idempotency keys with format `submission_id:f2:step_name` (classification, leasing_detection, economic_extraction, elements_detection) to avoid duplicate cost on retries.

**BR-12:** The system does not ask for clarifications from the user in any case. If classification is ambiguous, it is rejected with `NOT_CLASSIFIABLE`. There is no conversational dialog.

---

## 5. Data Models

### 5.1 Updates to `contract_analysis` (main table defined in F8)

F2 writes the following columns in the `contract_analysis` row corresponding to the submission:

```sql
-- F2 UPDATES these columns in contract_analysis (table defined in F8)
ALTER TABLE contract_analysis ADD COLUMN IF NOT EXISTS contract_type TEXT;
ALTER TABLE contract_analysis ADD COLUMN IF NOT EXISTS contract_type_declared TEXT;
ALTER TABLE contract_analysis ADD COLUMN IF NOT EXISTS contract_type_reclassified BOOLEAN DEFAULT FALSE;
ALTER TABLE contract_analysis ADD COLUMN IF NOT EXISTS reclassification_reason TEXT;
ALTER TABLE contract_analysis ADD COLUMN IF NOT EXISTS reclassification_indicators JSONB;
ALTER TABLE contract_analysis ADD COLUMN IF NOT EXISTS classification_confidence NUMERIC(3,2);
ALTER TABLE contract_analysis ADD COLUMN IF NOT EXISTS classification_attempts INTEGER DEFAULT 1;
ALTER TABLE contract_analysis ADD COLUMN IF NOT EXISTS elements_detected JSONB;
ALTER TABLE contract_analysis ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES project(id);
```

### 5.2 Extraction jobs

F2 does not use a dedicated table for its jobs because each submission has a single classification pass. If granular observability is desired, an optional table can be added:

```sql
CREATE TABLE IF NOT EXISTS classification_job (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id UUID NOT NULL REFERENCES contract_submission(id) ON DELETE CASCADE,
    analysis_id UUID REFERENCES contract_analysis(id),

    step TEXT NOT NULL CHECK (step IN ('classification', 'leasing_detection', 'economic_extraction', 'elements_detection')),
    attempt_number INTEGER NOT NULL DEFAULT 1,

    model_used TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    status TEXT NOT NULL CHECK (status IN ('running', 'success', 'failed', 'timeout')),

    tokens_consumed INTEGER,
    cost_estimate_cents INTEGER,

    error_code TEXT,
    error_message TEXT,

    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '24 hours')
);

CREATE INDEX idx_classification_job_submission ON classification_job(submission_id);
CREATE INDEX idx_classification_job_expires ON classification_job(expires_at);
```

### 5.3 Project (reference)

F2 reads and writes the `project` table defined in F8. For reference, the operation F2 executes is:

```sql
-- F2 upserts into project
INSERT INTO project (canonical_name, normalized_name, first_seen, last_analyzed, total_analyses)
VALUES ($1, $2, NOW(), NOW(), 1)
ON CONFLICT (normalized_name) DO UPDATE
SET last_analyzed = NOW(),
    total_analyses = project.total_analyses + 1
RETURNING id;
```

---

## 6. Integration Points

### 6.1 Input: queue from F1

F2 consumes the internal queue that F1 feeds. Message received:

```json
{
    "submission_id": "uuid",
    "analysis_id": "uuid",
    "extracted_text": "string (in memory, not persisted)",
    "extraction_metadata": {
        "strategy_used": "vision_llm",
        "pages_processed": 12,
        "language_detected": "es",
        "language_confidence": 0.94
    }
}
```

### 6.2 Output: queues to F4 and F5

After successful classification, F2 publishes to two parallel queues: one for F4 (Rubric Engine) and one for F5 (Economic Analysis). Both receive the same payload:

```json
{
    "submission_id": "uuid",
    "analysis_id": "uuid",
    "project_id": "uuid",
    "extracted_text": "string (in memory)",
    "classification": {
        "contract_type": "CVP",
        "contract_type_declared": "CVP",
        "contract_type_reclassified": false,
        "reclassification_reason": null,
        "confidence": 0.92
    },
    "economic_fields_raw": { "_comment": "output of prompt §8.5" },
    "elements_detected": { "_comment": "output of prompt §8.1 elements section" }
}
```

F4 and F5 run in parallel, and F6 then waits for both to finish (synchronization by `analysis_id`).

### 6.3 External service: OpenRouter

F2 makes one to five LLM calls per submission depending on the flow:

- 1 call: combined classification + extraction (prompt §8.1) — always
- 1 call: validation if the first had low confidence
- 1 call: leasing detection if type is CVC, CVP, or APV
- 1 call: economic extraction if type applies
- 1 call: key legal element detection

Configuration:

- `LLM_PROVIDER` env var (default `openrouter`)
- `LLM_CLASSIFICATION_MODEL` env var (default `anthropic/claude-sonnet-4`)
- `LLM_TIMEOUT_PER_CALL_SECONDS` env var (default 30)
- `LLM_TEMPERATURE` env var (default 0.1 for classification; structured and deterministic)
- `LLM_RESPONSE_FORMAT` always `json_object` when the model supports it

---

## 7. API Surface

F2 does not expose direct HTTP endpoints. Only internal APIs via queue.

For debugging and QA, a protected endpoint is exposed:

### 7.1 `POST /v1/internal/classify` (requires `X-Internal-Auth`)

Allows testing F2 without going through F1.

**Request:**

```json
{
    "text": "...contract text...",
    "force_type": null,
    "skip_leasing_check": false
}
```

**Response 200:**

```json
{
    "contract_type": "CVP",
    "contract_type_declared": "CVP",
    "contract_type_reclassified": false,
    "reclassification_reason": null,
    "confidence": 0.92,
    "project_name_extracted": "Residencial Las Palmeras",
    "project_name_normalized": "las palmeras",
    "economic_fields_raw": { },
    "elements_detected": { },
    "tokens_consumed_total": 4200,
    "cost_estimate_cents": 12
}
```

---

## 8. LLM Prompts

The LLM prompts are kept in Spanish because they instruct the model about Spanish-language Salvadoran contracts and use Salvadoran legal terminology verbatim. Translating the prompts to English would risk subtle drift in legal meaning. The prompts return structured JSON whose keys are in English.

### 8.1 Combined classification + extraction prompt (system)

```
Eres un analista experto en contratos inmobiliarios salvadoreños. Tu tarea es clasificar un contrato en uno de los siguientes ocho tipos exclusivos, y extraer información estructurada.

Tipos válidos:
- CVC: Compraventa de inmueble al contado (precio se paga total al firmar o en muy corto plazo, sin financiamiento estructurado)
- CVP: Compraventa de inmueble a plazos (precio pagadero en cuotas con o sin intereses, directo con vendedor o desarrollador, sin que sea financiamiento bancario regulado)
- ARV: Arrendamiento de vivienda (alquiler de casa, apartamento, mesón, para habitación)
- ARC: Arrendamiento de local comercial pequeño (alquiler para negocio cuyo activo no excede el límite legal, generalmente con habitación adjunta)
- APV: Arrendamiento con promesa de venta (alquila ahora, comprar al final del plazo con cánones que computan a precio)
- LEA: Leasing financiero inmobiliario (entidad financiera o leasing house es dueña, usuario paga canon y al final tiene opción de compra a precio predefinido)
- IVU: Contrato institucional del Instituto de Vivienda Urbana (adjudicación o renta de vivienda con régimen Bien de Familia)
- FSV: Contrato de compraventa financiado por el Fondo Social para la Vivienda
- NOT_CLASSIFIABLE: ninguno de los anteriores aplica claramente

Reglas de clasificación:
1. Una compraventa al contado paga el precio total al momento de firmar la escritura. Si hay cuotas, es CVP.
2. Un arrendamiento de vivienda paga renta mensual sin opción de adquisición. Si hay opción, es APV.
3. Un leasing tiene tres partes: proveedor, arrendador financiero, y arrendatario. El arrendador es dueño hasta el ejercicio de la opción de compra.
4. Si el contrato menciona el Fondo Social para la Vivienda como financiador, es FSV.
5. Si el contrato menciona el Instituto de Vivienda Urbana, IVU, o régimen Bien de Familia institucional, es IVU.

Devuelve UN ÚNICO objeto JSON con la siguiente estructura, sin texto adicional:

{
    "contract_type": "<one of the nine types>",
    "confidence": <number between 0 and 1>,
    "indicators_found": [<list of textual evidence found>],
    "reasoning": "<brief explanation in Spanish>",
    "project_name_canonical": "<project name as it appears, or null>",
    "elements_detected": {
        "warranty_clause": <bool>,
        "warranty_exemption_clause": <bool>,
        "bien_de_familia_mention": <bool>,
        "fsv_mention": <bool>,
        "urbanism_permit_mention": <bool>,
        "promise_to_sell": <bool>,
        "public_deed": <bool>,
        "arbitration_clause": <bool>,
        "blank_signature": <bool>,
        "rights_waiver": <bool>,
        "unilateral_modification": <bool>,
        "late_interest_on_total_balance": <bool>
    }
}
```

### 8.2 Combined classification + extraction prompt (user)

```
Aquí está el texto extraído de un contrato. Clasifícalo según las reglas dadas y extrae los elementos solicitados.

TEXTO DEL CONTRATO:
{{extracted_text}}
```

### 8.3 Validation prompt (when confidence is between 0.65 and 0.85)

```
Vas a re-evaluar la clasificación de un contrato. La clasificación anterior tuvo confianza media. Sé extra riguroso esta vez.

Aplica los mismos criterios. Si discrepas del anterior, explica por qué. Si coincides, refuerza la justificación.

Clasificación anterior:
- contract_type: {{previous_type}}
- reasoning: {{previous_reasoning}}

TEXTO DEL CONTRATO:
{{extracted_text}}
```

### 8.4 Disguised-leasing detection prompt

```
Eres analista legal experto en el Art. 2 de la Ley de Arrendamiento Financiero de El Salvador. Un contrato fue clasificado inicialmente como compraventa. Tu tarea es verificar si en realidad contiene los seis indicadores estructurales de leasing financiero.

Los seis indicadores son:
1. Plazo de cumplimiento forzoso (cancelación anticipada requiere pago equivalente al saldo restante)
2. Opción de compra a precio predefinido al final del plazo
3. La propiedad del bien se mantiene en el vendedor hasta el ejercicio de la opción
4. Todos los tributos, tasas, multas, e impuestos sobre el bien recaen en el "comprador"
5. Todos los riesgos (asegurables y no asegurables) recaen en el "comprador"
6. Los pagos se denominan canon en lugar de cuota de precio

Para cada indicador, devuelve si está presente y la evidencia textual.

Devuelve UN ÚNICO objeto JSON con esta estructura:

{
    "leasing_indicators": {
        "mandatory_term": {"detected": <bool>, "evidence": "<verbatim quote or null>"},
        "predefined_purchase_option": {"detected": <bool>, "evidence": "..."},
        "ownership_retained": {"detected": <bool>, "evidence": "..."},
        "taxes_to_buyer": {"detected": <bool>, "evidence": "..."},
        "risks_to_buyer": {"detected": <bool>, "evidence": "..."},
        "payments_as_rent": {"detected": <bool>, "evidence": "..."}
    },
    "indicators_count": <number of detected:true>,
    "should_reclassify": <bool, true if count >= 4>,
    "reclassification_severity": "<high if count >= 4, medium if count == 3, low if count <= 2>"
}

TEXTO DEL CONTRATO:
{{extracted_text}}
```

### 8.5 Economic extraction prompt

```
Eres analista financiero experto en contratos inmobiliarios salvadoreños. Tu tarea es extraer las cifras económicas declaradas explícitamente en el contrato.

Campos a extraer (cualquier campo que no aparezca explícitamente devuélvelo como null):

- price_cash: precio al contado o precio total declarado (número en la moneda del contrato)
- currency: moneda (USD por defecto en El Salvador; si es SVC o colones, conviértelo a USD usando tipo de cambio fijo histórico ¢8.75 = $1 y nota la conversión)
- down_payment: monto de prima o anticipo
- down_payment_pct: porcentaje cuando se expresa así (como decimal, ej. 0.10 para 10%)
- financed_amount: monto financiado (precio menos prima)
- term_months: plazo en meses
- annual_rate_pct: tasa anual efectiva como decimal (ej. 0.09 para 9%)
- monthly_payment: cuota mensual periódica
- monthly_rate_pct: tasa mensual cuando solo aparece esa
- payment_periodicity: "monthly", "biweekly", "weekly", "other"
- interest_calculation_base: "outstanding_principal", "total_balance", o "unspecified"

Reglas:
1. Si solo hay tasa mensual, también calcula la equivalente anual con capitalización mensual: (1 + monthly)^12 - 1
2. Si la cláusula sobre intereses dice "sobre el saldo total" o "sobre el monto total adeudado", marca interest_calculation_base como "total_balance"
3. Si dice "sobre saldos diarios pendientes" o "sobre capital pendiente", marca "outstanding_principal"
4. Si no se menciona la base de cálculo, marca "unspecified"
5. Cada campo extraído debe tener confidence (0 a 1) y evidence_snippet (cita literal donde aparece)

Devuelve UN ÚNICO objeto JSON con esta estructura:

{
    "price_cash": {"value": <num or null>, "currency": "USD", "confidence": <num>, "evidence_snippet": "..."},
    "down_payment": {"value": <num or null>, "currency": "USD", "confidence": <num>, "evidence_snippet": "..."},
    "down_payment_pct": {"value": <num or null>, "confidence": <num>, "evidence_snippet": "..."},
    "financed_amount": {"value": <num or null>, "currency": "USD", "confidence": <num>, "evidence_snippet": "..."},
    "term_months": {"value": <num or null>, "confidence": <num>, "evidence_snippet": "..."},
    "annual_rate_pct": {"value": <num or null>, "confidence": <num>, "evidence_snippet": "...", "extraction_note": "<if derived>"},
    "monthly_rate_pct": {"value": <num or null>, "confidence": <num>, "evidence_snippet": "..."},
    "monthly_payment": {"value": <num or null>, "currency": "USD", "confidence": <num>, "evidence_snippet": "..."},
    "payment_periodicity": {"value": "<...>", "confidence": <num>, "evidence_snippet": "..."},
    "interest_calculation_base": {"value": "<...>", "confidence": <num>, "evidence_snippet": "..."}
}

TEXTO DEL CONTRATO:
{{extracted_text}}
```

---

## 9. Non-Functional Requirements

- **P50 latency:** under 8 seconds for the full classification (all steps: classification, leasing if applicable, economic, elements).
- **P95 latency:** under 20 seconds.
- **Successful classification rate:** over 95% for contracts that actually belong to the eight covered types.
- **Reclassification false-positive rate:** under 2% (legitimate purchase contracts incorrectly reclassified as leasing).
- **Reclassification false-negative rate:** under 10% (disguised leases that pass as purchases).
- **Target cost:** under $0.05 USD per analysis in LLM for F2 steps.
- **Idempotency:** the same `analysis_id` with the same `rubric_version` is not reclassified.
- **Observability:** Prometheus metrics for distribution of classified types, reclassification rate, NOT_CLASSIFIABLE rate, per-step latency.
- **Logging:** structured JSON, without contract text. Logged values: classified type, found indicators (names, not clauses), confidence, project_normalized_name, costs.
- **LLM failure resilience:** if OpenRouter fails, retries are made against the model configured in `LLM_CLASSIFICATION_FALLBACK_MODEL`.

---

## 10. Open Questions

1. What is the optimal indicator threshold for reclassification to leasing? The PRD uses 4 of 6. It could be 3 of 6 (more sensitive, more false positives) or 5 of 6 (less sensitive, more false negatives). Requires evaluation with a real-contract corpus.

2. Should project-name extraction also normalize plurals and common typos? For example, "Las Palmera" and "Las Palmeras" would currently be two distinct projects. More aggressive normalization (stemming) could conflate genuinely different projects.

3. Should the system detect contracts modified by a word processor between the original upload and a new upload? For example, if a developer changes three words in the contract and resubmits, do we want to detect the structural similarity and warn? Requires full-document embedding and comparison.

4. Is the list of detected elements sufficient, or are additional flags needed for F4? Possible candidates: presence of trust clause, prepayment clause, clause for increase by property improvements. Product must define the definitive set.

5. What if the LLM fails with `confidence > 0.85` but the response is not valid parseable JSON? Proposed policy: retry with the validation prompt. If it fails again, mark `failed_classification` and not use `NOT_CLASSIFIABLE` (which is a verdict, not a technical error).

6. Is classification `confidence` preserved in the final report to the user, or only in internal logs? Showing it (e.g. "we classified this contract as installment purchase with 92% confidence") may be informative but can also confuse.

7. How are bilingual (Spanish + English) contracts handled? F1 already rejects if the primary language is not Spanish, but a Salvadoran contract with standard English clauses (common in leasing with international entities) could pass F1's language check and reach F2. Do we classify it anyway or send it to `NOT_CLASSIFIABLE`?

8. Is it acceptable to extract and process party names from the contract during processing even if not persisted, or do we want a stricter mode where the LLM never sees those fields? Strict mode requires redaction preprocessing that is complex and prone to breaking text coherence.

---

**End of document.**
