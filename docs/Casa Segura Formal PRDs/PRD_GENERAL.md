# PRD: Casa Segura — Automated Analysis of Real Estate Contracts

**Version:** 1.0
**Status:** Approved for development
**Author:** Product Team
**Date:** 2026-05-10

---

## 1. Problem Statement

In El Salvador, an ordinary person about to sign a real estate contract — whether a home purchase, a lease, or any variant — faces three questions they cannot answer alone: whether the economic figures (down payment, interest rate, term, monthly payment, total cost) are fair compared to the market, whether the clauses are legal or hide traps, and whether they are exposed to losing money or assets without realizing it. Hiring a lawyer to review the contract is expensive, and even when they do, the buyer typically enters that conversation without knowing what to ask.

The typical outcome is signing blindly and discovering the problem when it is already too late. This matters especially because, under Art. 1686 of the Salvadoran Civil Code, there is no rescission for gross disparity ("lesión enorme"): what the buyer signs today at an excessive price cannot be challenged later on those grounds.

The product objective is to receive a real estate contract in PDF or image format, automatically analyze it against a fixed rubric calibrated with Salvadoran law, and produce a report that scores the contract from 0 to 10, identifies critical findings with verbatim legal citations, calculates the economic overcost versus the market, and gives the user actionable material to negotiate with the seller or consult a lawyer before signing.

---

## 2. Scope

**In scope:**

- Analysis of real estate contracts in El Salvador
- Contract types covered: cash purchase, installment purchase, residential lease, small commercial lease, lease with promise to sell, real estate financial leasing, and institutional contracts from IVU and FSV
- Receiving the contract in PDF or image format (photos of physical documents)
- Text extraction with OCR when the document is scanned or photographed
- Automatic classification of the contract type
- Application of a fixed 38-criterion rubric across six categories (legal and formal validity, economic health, guarantees, property risks, abusive clauses, transparency)
- Detection of "purchase disguised as leasing" reclassification per Art. 2 indicators of the Salvadoran Financial Leasing Law
- Generation of a report with score, breakdown by category, critical findings, economic analysis compared against market benchmarks, and verbatim legal citations from the corpus
- Delivery of the report via email (PDF), WhatsApp (summary + link) through Zavu, or a public web link with configurable expiration
- Persistence of a real estate Project entity with aggregate metrics from associated analyses, without storing contract content or personal user data
- Single language: Spanish, informal "tú" register

**Out of scope:**

- Material verification against public registries (Registro de la Propiedad Raíz e Hipotecas, Registro Nacional de Arquitectos e Ingenieros, FSV, COMPRASAL)
- Reputation search of the developer on the web or social networks
- Blacklist of developers or sellers
- Verification of the real estate project from a photo of the advertising sign
- Identity verification of the user or contract parties
- User accounts, login, or any persistent authentication
- Personalized legal advice or representation
- Prediction of the future behavior of the seller or developer
- Personalization of the analysis based on the user's financial situation (income, debts, net worth)
- Analysis of contracts outside El Salvador
- Analysis of large commercial contracts, investments, complex condominium structures, or trusts
- Contracts in languages other than Spanish
- Permanent storage of the contract or the analyzed clauses
- Disputes, mediation, or any action after the report

---

## 3. User Stories

### US-01: User uploads a contract for analysis

**As a** Salvadoran buyer or tenant with a real estate contract in hand,
**I want to** upload the contract as PDF or image and receive an analysis,
**So that** I can know whether it is worth signing before I do.

**Acceptance criteria:**

- The user can upload the contract in PDF, JPG, PNG, HEIC, or WEBP format
- For images, the system accepts multiple files representing different pages of the same contract
- The maximum size per file and per analysis is defined in configuration
- Before processing, the system shows the user the disclaimer "Esto no es asesoría legal"
- The user must accept the disclaimer for the analysis to proceed
- The system validates that the file is readable and that the content is text in Spanish
- If the file is not readable, the system responds with status `not_analyzable` and explains how to resubmit
- The user receives a short identifier for the analysis (e.g. `CS-2026-A1B2C3`) that serves as the reference
- The analysis is completed and delivered in under 90 seconds at P95 from submission

**Accepted formats:**

- PDF
- JPG / JPEG
- PNG
- HEIC
- WEBP

**Reasons for analysis rejection (status `not_analyzable`):**

- OCR cannot extract enough text to identify the parties, price, or contract type
- The contract language is not Spanish
- The file is damaged, empty, or protected against extraction
- The contract type does not match any covered by the system

---

### US-02: System classifies the contract type and extracts the project name

**As the** system,
**I want to** identify the contract type and the name of the real estate project it belongs to,
**So that** I can apply the correct rubric criteria and associate the analysis with the Project entity.

**Acceptance criteria:**

- The system assigns one of the valid types based on the indicators present in the document
- If the contract is presented as a purchase but contains the six indicators of Art. 2 of the Financial Leasing Law (mandatory term, purchase option at a predefined price at the end, lessor remaining the owner during the term, all taxes and risks falling on the "buyer", payments named as rent, supplier-lessor-lessee triangle), the system reclassifies it as a financial leasing
- The reclassification is declared explicitly in the report with justification
- The system extracts the project name as it appears in the contract
- The extracted name is normalized (lowercase, no accents, no special characters) and used as the key to look up or create the Project entity
- If the name cannot be extracted, the analysis is associated with a project tagged `unknown_<hash>` and the report warns the user
- The system does NOT verify the project name against any external source
- The report always includes a note: "the project name was extracted from the contract; it was not verified against an external source"

**Contract types (enum):**

- `CVC` — Cash purchase
- `CVP` — Installment purchase
- `ARV` — Residential lease
- `ARC` — Small commercial lease
- `APV` — Lease with promise to sell
- `LEA` — Real estate financial leasing
- `IVU` — IVU institutional contract
- `FSV` — Purchase or loan financed by FSV
- `NOT_CLASSIFIABLE` — Does not fit any covered type

**Reclassification indicators to leasing (Art. 2 LAF):**

- The contract establishes a mandatory term
- A purchase option exists at a predefined price at the end of the term
- The seller declares ownership until the option is exercised
- All taxes, fees, fines, and levies on the property fall on the "buyer"
- All risks (insurable and non-insurable) fall on the "buyer"
- Payments are called "canon" instead of installments of the price

---

### US-03: System applies the rubric and produces the score

**As the** system,
**I want to** evaluate the contract against the 38 rubric criteria and produce a final score with band,
**So that** the user receives an actionable numeric rating.

**Acceptance criteria:**

- The system evaluates every criterion applicable to the detected contract type
- Each criterion produces a value between 0 and 10 according to the ranges defined in the rubric, or is marked `unverifiable`
- If a criterion is unverifiable, it adds the worst case defined in the rubric to the score, not the best
- The weights within each category are renormalized when some criteria do not apply to the contract type
- The category score is the weighted average of its applicable criteria
- The total score is the weighted average of the categories per the global weights
- The score band is assigned automatically: green from 8.0 to 10.0, yellow from 5.0 to 7.9, red from 0 to 4.9
- If a critical override fires, the final score is forced to 0 and the band to red, regardless of the average
- The system records which overrides fired, if any
- Each criterion applied to a contract must be traceable to its legal or market anchor in the corpus

**Global weights per category:**

- A. Legal and formal validity — 20%
- B. Economic health — 30%
- C. Guarantees for the buyer or tenant — 20%
- D. Property risks — 15%
- E. Abusive clauses and practices — 10%
- F. Transparency and clarity — 5%

**Asymmetric penalty rules:**

- A condition that benefits the buyer or tenant relative to the market benchmark never lowers the score
- A down payment lower than the standard benchmark scores equal to or better than the benchmark
- An interest rate lower than the segment benchmark scores better than the benchmark
- A shorter term consistent with the financed amount scores equal to or better

**Critical overrides (any of them forces score to 0 and band to red):**

- Sale of real property without a public deed — Art. 1605 Código Civil
- Price left to the arbitrary discretion of one party — Art. 1613 Código Civil
- Bad-faith waiver of warranty against eviction — Art. 1644 Código Civil
- Property under "Bien de Familia" regime with attempt to transfer without cancellation — Art. 3 Ley IVU
- Promise to sell without a term or condition fixing the time of execution — Art. 1425 Código Civil
- Waiver of non-waivable rights of the consumer or tenant — Art. 5 LPC and Art. 2 Ley de Inquilinato
- Late interest calculated on the total balance instead of the overdue principal — Art. 12 LPC
- Unilateral modification of price or conditions by the provider — Art. 13 LPC and Art. 17 lit. b LPC
- Imposition on the consumer to sign blank promissory notes or drafts — Art. 18 lit. b LPC
- Arbitration imposed in an adhesion contract — Art. 17 lit. h LPC
- FSV preventive annotation not disclosed with intent to sell — Art. 58 Ley FSV

---

### US-04: System generates the report with verbatim legal citations

**As the** system,
**I want to** produce a structured report with score, breakdown, findings, economic analysis, legal citations, and suggested actions,
**So that** the user has concrete material to negotiate with the seller or consult a lawyer.

**Acceptance criteria:**

- The report is generated in responsive HTML
- The report is converted to PDF for email delivery or download
- Each finding in the report includes severity (red, yellow, green with observation), short title, description, the cited contract clause when locatable, legal basis with the specific article, brief paraphrase of the article, and an actionable recommendation
- Legal citations are verbatim from the curated corpus; the system does not invent references or generate articles
- If a finding has no legal anchor available in the corpus, the citation is omitted and the finding is labeled `market_based` or `unverifiable`
- The report includes economic analysis with a table of key figures (price, down payment, term, effective annual rate, monthly payment, total cost) and comparison against market benchmarks
- The report calculates the overcost in local currency when applicable
- The report includes a suggested-actions section divided into three blocks: "before signing, ask the seller for", "take this to your lawyer", "documents you should demand"
- The disclaimer "Esto no es asesoría legal" appears in the header and footer of the report
- The report records the rubric version and corpus version used for reproducibility

**Report structure:**

1. Header with logo, analysis identifier, date, detected contract type, project name
2. Overall verdict with score, band, 2- to 3-sentence summary, override box if applicable
3. Economic analysis with figures table and benchmark comparison
4. Breakdown by category with partial score and list of criteria
5. Highlighted findings ordered by severity
6. Referenced legal bases with paraphrase and corpus reference
7. Actionable suggested actions
8. Footer with extended disclaimer, rubric version, corpus version, and how to report errors

**Finding severity:**

- `critical` — active override or absolute nullity
- `red` — serious deviation against the buyer, clear illegality
- `yellow` — negotiable observation or out-of-market condition
- `green` — favorable or compliant
- `unverifiable` — cannot be extracted from the contract

---

### US-05: User receives the report via the chosen channel

**As a** user who received their analysis,
**I want to** receive the report by email, WhatsApp, or web link according to my preference,
**So that** I can consult it wherever it is most convenient.

**Acceptance criteria:**

- The user chooses the delivery channel at upload time
- If email is chosen, the system sends the PDF as an attachment with a descriptive subject and brief body
- If WhatsApp is chosen, the system sends a message via Zavu with the score, summarized critical findings, and a link to the full HTML report
- If a web link is chosen, the system delivers a public URL with configurable expiration
- The web link serves the HTML report while it has not expired
- After expiration, the link shows an explanatory message: "Este análisis ya no está disponible. Casa Segura no almacena reportes de forma permanente para proteger tu privacidad."
- The user's email or phone number is stored only as a hash for delivery retries; the original value is discarded once delivery is confirmed
- The email and WhatsApp message templates include the disclaimer "Esto no es asesoría legal"

**Delivery channels:**

- `email_pdf` — Email with PDF attachment
- `whatsapp_summary` — WhatsApp message with summary and link to the full report
- `web_link` — Public link with TTL

---

### US-06: System maintains aggregate intelligence by Project

**As the** system,
**I want to** associate each analysis with a Project entity and accumulate metrics without storing personal data,
**So that** a second user who analyzes a contract from the same project receives aggregate context.

**Acceptance criteria:**

- Each analysis is associated with a Project identified by the normalized project name extracted from the contract
- If the Project does not exist in the system, it is created automatically with the first analysis
- If the Project exists, the analysis increments the `total_analyses` counter and updates `last_analyzed`
- The system calculates and maintains the `avg_score` across all analyses of the Project
- From the second analysis onward, the report shows: "Casa Segura has analyzed N contracts from this project. Average score: X.X"
- Under no circumstance does the system store the contract content, identified clauses, the names of the parties, or the specific address of the property
- The system stores from each analysis only: the total score, scores by category, count of findings by severity, the economic summary in aggregate figures, the triggered overrides, the rubric version, and the corpus version
- The Project and its aggregate metrics are kept indefinitely

---

### US-07: System applies retention and anonymization to analyses

**As the** system,
**I want to** apply strict retention rules over individual analyses,
**So that** the privacy promise to the user is materially upheld.

**Acceptance criteria:**

- The HTML report and the generated PDF are not persisted to disk
- The report is regenerated on demand from the analysis row whenever the user accesses the link
- Individual analyses are kept in full state for 90 days from creation
- After 90 days, the analysis is anonymized: the `delivery_target_hash` is deleted, the `economic_summary` is reduced to discrete buckets (for example, "rate between 9 and 10%" instead of the exact value), the Project association is kept
- After anonymization, the remaining data contributes to the Project's average but does not allow re-identification of the individual analysis
- The short analysis identifier (`public_short_id`) remains valid but the report can no longer be regenerated after the link TTL
- The user cannot query "my last analysis" without the short identifier; without that identifier, there is no access

---

## 4. Business Rules

**BR-01:** The system does not store the contract content in any form. This includes the original file, the OCR-extracted text, the clauses identified as findings, and any intermediate transcription. The original file is discarded immediately after analysis. Clauses cited in the report are generated at render time and discarded afterward.

**BR-02:** Every report finding asserting a legal violation must have a verbatim citation from the curated corpus. Findings without an available legal anchor in the corpus are labeled `market_based` or `unverifiable`, never as a legal violation without citation.

**BR-03:** The LLM does not generate legal references. It only consumes those handed to it by the retrieval layer from the corpus. If retrieval does not return an article with sufficient relevance, the finding is emitted without citation and labeled accordingly.

**BR-04:** A criterion that cannot be evaluated due to missing information in the contract is marked `unverifiable` and contributes the worst case to the score, not the best. The justification for unverifiability is included in the corresponding report finding.

**BR-05:** If any of the critical overrides defined in US-03 fires, the final score of the analysis is 0 and the band is red, regardless of the weighted average of the criteria.

**BR-06:** The system does not ask the user for their income, salary, net worth, or any characteristic of their personal financial situation. Economic criteria are evaluated against market benchmarks, not against the user's ability to pay.

**BR-07:** Every user-facing interaction (upload page, HTML report, PDF, email message, WhatsApp message) must include the disclaimer "Esto no es asesoría legal". The disclaimer appears in the header and footer of the report at minimum.

**BR-08:** The system operates only in Spanish. If the contract is in another language, the analysis is rejected with status `not_analyzable`.

**BR-09:** The system analyzes only contracts whose object is a property located in El Salvador. If the contract mentions a property in another country, the analysis is rejected with status `not_analyzable`.

**BR-10:** The system covers only the eight contract types listed in US-02. Any contract that does not fit is rejected with status `not_analyzable`.

**BR-11:** The system keeps no blacklist or whitelist of developers, sellers, landlords, or construction companies. Evaluation is based exclusively on the document submitted by the user.

**BR-12:** The system does not materially verify against public registries (Registro de la Propiedad Raíz, Registro Nacional de Arquitectos e Ingenieros, FSV, COMPRASAL, RUPES). Criteria depending on material verification are evaluated from what the contract declares or omits, and warn the user of what they must materially verify on their own or with their lawyer.

**BR-13:** The economic benchmarks used by the rubric live in a versioned configuration file. Any change to the benchmarks requires recording the cited source (Banco Central de Reserva, Superintendencia del Sistema Financiero, sector trade associations) and the date of the latest update. Each analysis records the version of the configuration file used for reproducibility.

**BR-14:** Legal citations in the report use the paraphrase from the curated corpus, not the verbatim text of the published law. The corpus paraphrase is subject to human review and must be faithful to the original article.

**BR-15:** Any finding labeled `provisional_pending_corpus` must declare it visibly in the report. This covers criteria whose legal basis is in the process of being added to the corpus (for example, the Special Land Subdivision Law).

**BR-16:** The system versions the rubric. Each analysis records which rubric version it used. Reports regenerated from an old analysis use the rubric originally applied, not the current one.

---

## 5. Non-Functional Requirements

- The time between contract submission and report delivery must be under 90 seconds at P95
- The system must support 100 concurrent analyses without response-time degradation
- Availability must be over 99% during business hours in El Salvador (UTC-6, 6:00 to 22:00)
- All calls to the LLM provider must use idempotency keys to avoid duplicate costs on retries
- The system must be idempotent with respect to the contract upload hash: if the same contract is uploaded twice, the system recognizes it and returns the previous analysis without recalculating
- The LLM token consumption per analysis must be bounded: at most one vision call and two text calls in the nominal flow
- HTML reports must render correctly on mobile devices from 360-pixel width
- The generated PDF report must be legible and preserve the HTML style at a reasonable print density
- The system must record anonymous aggregate metrics for observability: latency per pipeline stage, OCR success rate, leasing reclassification rate, score distribution, override frequency, most-analyzed contract types
- Metrics include no user-identifying or individual-contract data
- Processing must comply with common security practices: TLS for all communications, salted hashing for delivery identifiers, no sensitive information in logs

---

## 6. Open Questions (from Product)

1. What is the sustainability model for LLM provider calls in production? The project is built open source under MIT, but each analysis has a variable cost. Options discussed include donations, freemium (first analysis free and subsequent ones at a symbolic price), institutional sponsorship (banks, trade associations, ombudsman), or B2B institutional subscription (notaries, small law firms). Product must decide before the first deploy to real users.

2. Who is responsible for calibrating and maintaining the economic benchmarks (rates, down payments) against official sources (Banco Central de Reserva, Superintendencia del Sistema Financiero, ABANSA)? Without periodic calibration, the system can give incorrect information to the user. Product must define the review frequency and the responsible person or body.

3. What is the TTL of the public web link to the report? The initial proposal is 30 days. A shorter TTL reduces the risk of link leakage but introduces friction if the user forgets to review the report. A longer TTL is the opposite.

4. Does the system verify the project name against an external source before associating it with the Project entity, or does it simply state explicitly that the name was extracted from the contract without verification? External verification requires a reliable source the system does not yet have. Without verification, a fraudster could use the name of a real project to associate their analysis with the correct entity.

5. Is the Art. 1686 Civil Code warning ("in El Salvador there is no rescission for gross disparity") shown on every report, or only when the score is low? Showing it always informs the user of an important and little-known legal restriction. Showing it only on low scores avoids noise when the contract looks favorable.

6. Can the user request the report to be resent by providing the short analysis identifier and the original email or phone (with hash verification), or is each analysis a one-time delivery without resending? The resend option is convenient for a user who lost the report. The single-delivery option reduces leak surface.

7. What is the policy on repeated analyses of the same contract by the same or different users? If two people upload the same contract (identical by hash), does the system charge twice (if there is a charge), deliver twice, or consolidate? Idempotency is already covered technically by BR; but at the product level there may be implications.

8. Should the system offer the user a channel to report discrepancies or errors in the analysis (for example, a misidentified finding or an incorrect legal citation)? If so, how are those reports processed and who is responsible for the review?

---
