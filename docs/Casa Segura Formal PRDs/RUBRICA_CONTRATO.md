# Casa Segura — Real Estate Contract Rating Rubric

**Version:** 0.1 (initial draft)
**Date:** 2026-05-10
**Geographic scope:** El Salvador
**Contract types covered:** Purchase of real property (cash and installments), residential and commercial leases, lease with promise to sell, financial real estate leasing, institutional contracts (IVU/FSV) when identified.

**Legal sources (all verbatim-verified against official sources):**
- Código Civil de El Salvador (Decree of 23-08-1859)
- Ley sobre Contratos del IVU (D.L. 1486 of 1954)
- Ley de Inquilinato (D.L. 2591 of 1958, partial repeal 2008)
- Ley del Fondo Social para la Vivienda (D.L. 328 of 1973)
- Ley de Urbanismo y Construcción (D.L. 232 of 1951, last reform 2021)
- Ley de Arrendamiento Financiero (D.L. 884 of 2002)
- Ley de Protección al Consumidor (D.L. 776 of 2005)

**Corpus pending incorporation (when official source is obtained):**
- Ley Especial para la Regularización de Lotificaciones y Parcelaciones para Uso Habitacional
- Ley de Compras Públicas (D.L. 868 of 2023) — currently only in corpus paraphrase

---

## 1. Rubric philosophy

The rubric looks for the same things an honest advisor would look for in any real estate contract before signing. Each criterion answers a concrete question and is evaluated against a numeric or documentary verifiable rule.

The final score is not a moral verdict on the developer or landlord. It is an answer to the user's question: *"Does this contract, as drafted, suit you for signing?"*

### 1.1 Cross-cutting rules

**Asymmetric penalty.** A condition that benefits the buyer or tenant against the market average never reduces the score. For example: a 5% down payment when the market average is 10% scores the same or better than a 10% down payment. An interest rate of 6% when the average is 9% scores better, not worse.

**Each criterion cites a specific legal article.** If there is no direct legal anchor, the criterion is based on documented market practice and is labeled `market` instead of `legal`. A criterion without any anchor does not enter the rubric.

**Numeric parameters live in configuration**, not hard-coded. Market rates, standard down payments, reference amounts have a configuration file with cited source (BCR, SSF, ABANSA) and last update date.

**Unverifiable adds the worst case, not assumed pass.** If a value cannot be extracted from the contract — because the clause does not exist, because OCR failed, because it is implicit — the criterion is marked `unverifiable` and adds the worst case to the score with visible justification. Better a false negative (over-alarm) than a false positive (over-reassure).

**The report always warns about Art. 1686 CC.** In El Salvador there is no rescission for gross disparity. The buyer cannot challenge later a price they signed today. That is why the rubric emphasizes ex-ante economic analysis.

**The system does not infer user income.** With no user data, criteria requiring income comparison (e.g. monthly payment / income) are evaluated by absolute bands or marked unverifiable. The user is not asked for their salary.

---

## 2. Score structure

| Category | Weight | What it covers |
|---|---|---|
| **A. Legal and formal validity** | 20% | Whether the contract is legally enforceable |
| **B. Economic health** | 30% | Whether the figures suit the buyer or tenant |
| **C. Guarantees for the buyer or tenant** | 20% | Mechanisms protecting whoever pays |
| **D. Property risks** | 15% | Registry status, special regimes, permits |
| **E. Abusive clauses and practices** | 10% | Violations of the Ley de Protección al Consumidor |
| **F. Transparency and clarity** | 5% | Language, exhibits, right of withdrawal |
| **Total** | **100%** | Normalized 0–10 score |

Weights are justifiable and changeable. Economic health receives the largest weight (30%) because, given Art. 1686 CC (no rescission for gross disparity), economic analysis is the largest protection the system can offer ex ante.

### 2.1 Final score bands

| Range | Color | Interpretation |
|---|---|---|
| 8.0 – 10.0 | 🟢 Green | Favorable contract, within market and within the law. Even so, read carefully and consult a lawyer before signing. |
| 5.0 – 7.9 | 🟡 Yellow | There are points to negotiate. Some clauses or figures deviate from the standard or market. Seek professional review before signing. |
| 0.0 – 4.9 | 🔴 Red | Proceed with care. Serious irregularities, abusive clauses, serious risks to property or financial health were detected. Do not sign without legal advice. |

### 2.2 Severity modifiers (overrides)

Some findings are so severe they invalidate the average. If any of these triggers, the final score is forced to the red band and the report is flagged `CRITICAL_OVERRIDE`:

1. **Sale of real property in a simple private document, without public deed** — Art. 1605 CC. The sale has not been perfected.
2. **Price left to the discretion of one of the parties** — Art. 1613 CC. The sale is not valid.
3. **Bad-faith waiver of eviction warranty** — Art. 1644 CC. Void agreement.
4. **Property under Bien de Familia regime and attempt to transfer** — Art. 3 Ley IVU. Absolute nullity.
5. **Clause waiving non-waivable consumer rights** — Art. 5 LPC and Art. 2 Ley de Inquilinato. Void clause.
6. **Late interest computed on total balance and not on overdue principal** — Art. 12 LPC. Prohibited practice.
7. **Unilateral modification of price or conditions by the provider** — Art. 13 LPC and Art. 17 lit. b LPC. Abusive clause.
8. **Imposing the consumer to sign blank promissory notes or drafts** — Art. 18 lit. b LPC. Prohibited practice.
9. **Arbitration imposed in adhesion contract** — Art. 17 lit. h LPC and Art. 44 lit. g LPC. Very serious infraction.
10. **Promise to sell without term or condition fixing the time of execution** — Art. 1425 CC. The promise does not bind the promisor.
11. **Undisclosed preventive FSV annotation** when attempting to sell — Art. 58 Ley FSV. Recording impossible without consent of the Fund.

When an override triggers, the report declares the reason in the header and all other findings go to second plane.

### 2.3 Special band: `not_analyzable`

The contract cannot be analyzed and no score is delivered if:

- OCR does not extract enough text to identify parties, price, or contract type.
- The language is not Spanish (Art. 22 LPC requires Spanish for adhesion contracts).
- The file is illegible, incomplete, or protected against extraction.
- The contract type does not fit any of those covered by the rubric (see §4).

In these cases the report explains what failed and how to resubmit.

---

## 3. Applicability by contract type

Not all criteria apply to all contracts. Applicability is defined with a three-letter code:

| Code | Type |
|---|---|
| `CVC` | Cash purchase |
| `CVP` | Installment purchase |
| `ARV` | Residential lease |
| `ARC` | Commercial-space lease |
| `APV` | Lease with promise to sell |
| `LEA` | Financial real estate leasing |
| `IVU` | IVU institutional contract |
| `FSV` | Purchase or loan financed by FSV |

When a criterion does not apply to the detected type, it does not enter the score computation (it is not averaged with zero, it simply does not participate).

The system classifies the contract type by reading the document. If the document is presented as "compraventa" but contains the six leasing indicators from Art. 2 LAF (mandatory term, purchase option at a predefined price, lessor retaining ownership, all taxes to the "buyer", risks to the "buyer", rent rather than installment), the system reclassifies it as `LEA` and warns the user explicitly. This is the costliest trap in the market and the rubric treats it as a critical finding.

---

## 4. Category A — Legal and formal validity (20%)

Measures whether the contract is legally enforceable. Without this, everything else is theoretical.

### A1. Written form and complete property data

**Weight within A:** 25%
**Applies to:** all
**Legal anchor:** Art. 4 Ley de Inquilinato (lease), Art. 18 Ley de Inquilinato (tenement houses), Art. 1605 CC (real property sale requires public deed), Art. 22 LPC (adhesion contracts), Art. 27 LPC (complete housing information).

**What is sought:**
- For purchase: public deed before notary.
- For lease: written contract signed by the parties.
- For all: property description including location, registry data (matrícula, inscription number, folio, libro), area in square meters, boundaries.

**Scale:**

| Score | Criterion |
|---|---|
| 10 | For purchase: public deed. Complete registry description. Area and boundaries. |
| 8 | For lease: written contract with complete property data including matrícula. |
| 6 | Written document with description of location and area, without registry matrícula. |
| 4 | Written document with generic address, no registry data or specific area. |
| 2 | Purchase in a simple private document without public deed (critical override — system flags but the computation stays here). |
| 0 | Property not identified, or only "the offered lot", or verbal lease contract. |

**Override:** if type is CVC, CVP, or APV and there is no public deed or notarized private document for leasing, score forced to 0 with override `art_1605_cc`.

### A2. Identification of the parties

**Weight within A:** 15%
**Applies to:** all
**Legal anchor:** Art. 18 Ley de Inquilinato, Art. 12-B lit. a LPC.

**What is sought:** full name, DUI or NIT, domicile, profession, legal capacity of each party. In institutional contracts: appointment or legal representation of the entity.

**Scale:**

| Score | Criterion |
|---|---|
| 10 | Both parties with name, DUI or NIT, domicile, profession. |
| 7 | Missing DUI or domicile of one party. |
| 4 | Missing two or more data of one party. |
| 0 | One party unidentified, or representative without accredited powers. |

### A3. Determined price and payment form

**Weight within A:** 20%
**Applies to:** all
**Legal anchor:** Art. 1612 CC (determined price), Art. 1613 CC (not at the discretion of one), Art. 4 Ley de Inquilinato, Art. 12-B lit. d, e, f LPC.

**What is sought:**
- Total price stated as a concrete figure.
- For installment purchase: down payment, term, installment periodicity, interest rate, number of installments, amount of each installment.
- For lease: monthly rent, periodicity, place of payment.
- Concrete payment form (bank account, receipt, deposit).

**Scale:**

| Score | Criterion |
|---|---|
| 10 | Total price and all numeric elements. Clear payment form. |
| 7 | Price mentioned but missing some element (e.g. rate not expressed as effective annual). |
| 4 | Price present but payment form ambiguous. |
| 0 | Variable, undetermined price, or "at the seller's discretion" or "per company policy". |

**Override:** if the price is left at one party's discretion, score forced to 0 with override `art_1613_cc`.

### A4. Term and validity

**Weight within A:** 15%
**Applies to:** all
**Legal anchor:** Art. 6 Ley de Inquilinato (lease term), Art. 2 Ley IVU (IVU maximum 30 years), Art. 9 LAF (lessor mandatory term in leasing), Art. 1611 CC (pure, conditional, or term sale).

**What is sought:** start date, term, form of termination or renewal.

**Scale:**

| Score | Criterion |
|---|---|
| 10 | Certain term, within the applicable legal maximum. |
| 6 | Term present but no termination form specified. |
| 3 | Term exceeds legal maximum or is ambiguous. |
| 0 | No term, or term is undetermined. |

### A5. Signature, date, and place

**Weight within A:** 10%
**Applies to:** all
**Legal anchor:** Art. 18 Ley de Inquilinato (seven elements), Art. 12-B lit. j, k LPC.

**Scale:**

| Score | Criterion |
|---|---|
| 10 | Signatures of all parties, signing date, signing place. |
| 6 | Missing one of the three elements. |
| 0 | No signature or no date. |

### A6. Valid promise to sell (when applicable)

**Weight within A:** 15% (only if type is APV or a promise prior to the definitive contract is detected)
**Applies to:** APV, CVP when a prior promise exists
**Legal anchor:** Art. 1425 CC.

**What is sought:** the four circumstances of Art. 1425 CC without which the promise produces no obligation.

**Scale:**

| Score | Criterion |
|---|---|
| 10 | Promise in writing, lawful contract, term or condition fixing the time of execution, sufficient specification of the promised contract. |
| 7 | One of the four requirements missing. |
| 4 | Two requirements missing. |
| 0 | Promise without term or condition fixing the time. The promise does not bind the promisor and the "buyer" has no enforceable right. |

**Override:** if requirement 3 (term or condition) is missing, score forced to 0 with override `art_1425_cc`. It is a classic fraud pattern.

---

## 5. Category B — Economic health (30%)

The analysis core. This category answers the user's question: "is it financially convenient for me to sign this?"

All numeric benchmarks come from the `economic_benchmarks.yaml` configuration file (see §15) with cited source and last update date. The values in this document are illustrative; the real ones are kept in config.

### B1. Reasonable down payment or advance

**Weight within B:** 10%
**Applies to:** CVP, APV, LEA, FSV
**Legal anchor:** Art. 13 LPC (deferred delivery, consumer rights over down payments), Art. 43 lit. d LPC (non-refund of down payments is a serious infraction). For FSV: Art. 7 and Art. 68 Ley FSV.

**What is sought:** percentage of the total price delivered as down payment or advance.

**Benchmarks (config):**
- Purchase with bank or FSV financing: standard 10% down payment.
- Purchase directly with developer: 5–15% down payment.
- Lease with promise to sell: variable down payment.

**Scale (asymmetric penalty — low down payments do not penalize):**

| Score | Criterion |
|---|---|
| 10 | Down payment ≤ standard benchmark (≤ 10%). |
| 8 | Down payment 1–5 percentage points above benchmark (10–15%). |
| 5 | Down payment 5–10 points above benchmark (15–20%) — "high". |
| 2 | Down payment 10–25 points above benchmark (20–35%) — "very high". |
| 0 | Down payment > 35% of price or full delivery before the deed — fraud pattern. |

### B2. Effective annual interest rate

**Weight within B:** 20%
**Applies to:** CVP, APV, LEA, FSV
**Legal anchor:** Art. 12 LPC (interest computation on daily balances and calendar year), Art. 19 lit. f, j LPC (informed effective annual rate), Art. 19 lit. p LPC (approval letter with rate stated as annual percentage).

**What is sought:** effective annual interest rate applied to the financed balance.

**Benchmarks (config, subject to update with BCR/SSF source):**
- Bank mortgage credit in El Salvador: 7–9% annual.
- FSV credit: subsidized rate, typically 5–7%.
- Direct credit with developer: variable, 8–12% is common.
- Any rate > 15% is considered out of market for real estate.

**Scale (user rule: 2% above average = bad, 5% above average = severe):**

| Score | Criterion |
|---|---|
| 10 | Rate ≤ segment median benchmark (≤ 9%). |
| 9 | Rate 0–1 point above median benchmark (9–10%). |
| 7 | Rate 1–2 points above benchmark (10–11%). |
| 5 | Rate 2–5 points above benchmark (11–14%) — "bad". |
| 2 | Rate 5–10 points above benchmark (14–19%) — "severe". |
| 0 | Rate > 10 points above benchmark (> 19%) or not expressed as effective annual. |

**Unverifiable:** if the rate is expressed only as monthly without an annual equivalent, the system computes the equivalent annual rate and applies the scale. If there is no way to compute it, score 4 with justification "annual rate not expressed — Art. 19 lit. j LPC requires effective annual rate".

### B3. Credit term

**Weight within B:** 10%
**Applies to:** CVP, APV, LEA, FSV
**Legal anchor:** Art. 2 Ley IVU (maximum 30 years in institutional contracts).

**Benchmarks (config):**
- Reasonable term: 5–25 years for real estate.
- IVU institutional term: maximum 30 years.

**Scale:**

| Score | Criterion |
|---|---|
| 10 | Term between 5 and 20 years, consistent with the financed amount. |
| 7 | Term between 20 and 25 years. |
| 4 | Term between 25 and 30 years (IVU legal maximum). |
| 0 | Term > 30 years, or term so short the installment is pathological relative to the amount. |

### B4. Computed final total cost

**Weight within B:** 15%
**Applies to:** CVP, APV, LEA, FSV

**Computation:** principal + (monthly installment × number of installments) + commissions + insurance + deed costs + registry costs + any other identified fee.

**Comparison:** total cost / cash price.

**Benchmarks (config):**
- Healthy mortgage credit: total cost between 1.4× and 1.8× cash price for 15–25 year terms.

**Scale (asymmetric penalty — short or subsidized financings score better):**

| Score | Criterion |
|---|---|
| 10 | Total cost ≤ 1.5× cash price. |
| 8 | Total cost between 1.5× and 1.8×. |
| 6 | Total cost between 1.8× and 2.0× — expensive but typical of long terms. |
| 3 | Total cost between 2.0× and 2.5×. |
| 0 | Total cost > 2.5× — excessive or usurious. |

### B5. Reasonable monthly payment (absolute criterion, does not require user income)

**Weight within B:** 10%
**Applies to:** CVP, APV, LEA, FSV, ARV

**What is sought:** the monthly installment relative to the total price, normalized to identify whether it is within the reasonable range for the financed amount and term.

**Computation:** monthly payment ÷ (total price / term in months). A ratio close to 1 indicates the installment is aligned with linear amortization. Very high ratios suggest excessive interest or hidden costs.

**Scale:**

| Score | Criterion |
|---|---|
| 10 | Ratio between 1.0 and 1.2. |
| 7 | Ratio between 1.2 and 1.4. |
| 4 | Ratio between 1.4 and 1.7. |
| 0 | Ratio > 1.7 — the installment implies excessive interest or costs for the term. |

**Unverifiable:** if the term or total price cannot be determined, the criterion is marked unverifiable and adds score 4 (worst intermediate case).

### B6. Itemized additional charges

**Weight within B:** 10%
**Applies to:** all
**Legal anchor:** Art. 12-A LPC (only charge identified and described commissions in the contract), Art. 19 lit. p LPC (approval letter with breakdown of charges, surcharges, rate, commissions), Art. 27 LPC (clear and complete information).

**What is sought:** all charges to the buyer or tenant (deed, registry, commissions, insurance, maintenance, administration) must be listed with amount and reason.

**Scale:**

| Score | Criterion |
|---|---|
| 10 | All charges listed with specific amount and reason. |
| 7 | Charges listed but without specific amount or clear reason. |
| 4 | Generic charges ("administrative commissions", "various expenses"). |
| 0 | Open charges ("commissions per bank policy" or "charges the seller determines"). |

### B7. Reasonable late-payment penalty

**Weight within B:** 10%
**Applies to:** CVP, APV, LEA, ARV, FSV
**Legal anchor:** Art. 12 LPC (late interest on overdue principal, not on total balance), Art. 17 lit. i LPC (penalty must correspond to the damage caused).

**What is sought:** late interest percentage and computation base.

**Scale:**

| Score | Criterion |
|---|---|
| 10 | Late interest computed only on overdue principal, ≤ 1.5× ordinary interest rate. |
| 7 | Late interest ≤ 2× ordinary rate, on overdue principal. |
| 4 | Late interest > 2× ordinary rate, on overdue principal. |
| 0 | Late interest computed on total balance (Art. 12 LPC prohibited), or disproportionate penalty clause. |

**Override:** if late interest is computed on the total balance, score forced to 0 with override `art_12_lpc`.

### B8. Prepayment penalty

**Weight within B:** 8%
**Applies to:** CVP, APV, LEA, FSV
**Legal anchor:** Art. 17 lit. g LPC (prepayment fees generally prohibited), Art. 19 lit. m LPC (prepayment without fee in credit operations, except external funds or fixed rate at short/medium term).

**Scale:**

| Score | Criterion |
|---|---|
| 10 | Prepayment without fee. |
| 7 | Prepayment fee ≤ 1% of balance, justified by external funds or fixed rate. |
| 4 | Prepayment fee between 1% and 3% of balance. |
| 0 | Prepayment fee > 3% or without justification, or prohibition of prepayment. |

### B9. Unilateral modification of price or conditions

**Weight within B:** 7%
**Applies to:** all
**Legal anchor:** Art. 13 LPC (price not unilaterally modifiable), Art. 17 lit. b LPC (abusive clause), Art. 1613 CC (price not at the discretion of one party).

**Scale:**

| Score | Criterion |
|---|---|
| 10 | The contract does not allow unilateral modification of price or conditions. |
| 5 | Allows adjustments with at least 30 days prior notice and the right to withdraw. |
| 0 | Allows the seller or landlord to modify price or conditions without consent. |

**Override:** if it allows unilateral modification, score forced to 0 with override `art_13_lpc`.

---

## 6. Category C — Guarantees for the buyer or tenant (20%)

This category measures the protections of the payer: what happens if things go wrong?

### C1. Escrow or trust mechanism for the down payment

**Weight within C:** 20%
**Applies to:** CVP, APV
**Legal anchor:** Not a direct legal requirement, but its absence reinforces the risk described in Art. 13 LPC (deferred delivery) and Art. 43 lit. d LPC (non-refund of down payments is a serious infraction).

**Scale:**

| Score | Criterion |
|---|---|
| 10 | Down payment deposited in bank escrow or joint account, released only against delivery of the property. |
| 7 | Down payment to the seller's account but with notarial receipt and proof of destination of the money. |
| 4 | Down payment delivered with simple receipt. |
| 0 | Down payment delivered in cash without proof or protection, or unconditional no-refund clause. |

### C2. Certain delivery date

**Weight within C:** 15%
**Applies to:** CVP, APV, LEA, ARV (at start of lease), FSV
**Legal anchor:** Art. 13 LPC (deferred delivery with consequences of non-fulfillment), Art. 1714 CC (lessor delay in delivering).

**Scale:**

| Score | Criterion |
|---|---|
| 10 | Exact delivery date, with quantified penalty for delay. |
| 7 | Date range (specific month and year) with penalty. |
| 4 | "Approximately N months" with generic penalty. |
| 0 | "When construction is finished", "as work progresses", without penalty. |

### C3. Penalty for seller or lessor delay

**Weight within C:** 15%
**Applies to:** CVP, APV, LEA, ARV, FSV
**Legal anchor:** Art. 13 LPC (delay consequences, right to indemnification with legal commercial interest), Art. 1714 CC.

**What is sought:** penalty equal to or higher than the buyer's in the symmetric case.

**Scale:**

| Score | Criterion |
|---|---|
| 10 | Quantified penalty (% per month of delay, refund of down payment with legal commercial interest), symmetric or higher than the penalty to the late buyer. |
| 6 | Penalty present but lower than the buyer's symmetric. |
| 3 | Symbolic penalty or lower than legal commercial interest. |
| 0 | No penalty or clause excluding the seller from liability for delay. |

### C4. Treatment of seller or lessor non-compliance

**Weight within C:** 15%
**Applies to:** all
**Legal anchor:** Art. 13 LPC (refund of payments + indemnification if the provider breaches), Art. 43 lit. d LPC (non-refund of down payments is a serious infraction), Art. 1675 CC (rescission for delay with indemnification), Art. 1677 CC (partial restitution to the buyer).

**Scale:**

| Score | Criterion |
|---|---|
| 10 | Clear clause: if the seller breaches, the buyer recovers everything paid plus legal commercial interest. |
| 7 | Refund of payments but with percentage retention under 5%. |
| 4 | Partial refund or subject to onerous conditions. |
| 0 | Payments on account not refunded in case of seller breach — serious infraction Art. 43 lit. d LPC. |

### C5. Warranty against eviction and hidden defects

**Weight within C:** 15%
**Applies to:** CVC, CVP, APV, LEA, FSV
**Legal anchor:** Art. 1639 CC (warranty obligation), Art. 1644 CC (nullity of the bad-faith exemption), Art. 1659–1670 CC (hidden defects), Art. 1668 CC (term: 1 year for property from actual delivery), Art. 4 lit. b LAF (provider in leasing warrants absence of liens and hidden defects).

**Scale:**

| Score | Criterion |
|---|---|
| 10 | Explicit warranty clause, per common law, with defects term ≥ 1 year. |
| 7 | Warranty mentioned but limited to specific aspects. |
| 4 | Limited clause or full silence (Civil Code applies supplementarily). |
| 0 | Clause exempting the seller from eviction warranty — Art. 1644 CC void if bad faith. |

**Override:** if there is an explicit clause exempting from eviction warranty, score forced to 0 with override `art_1644_cc`. The system flags the finding and highlights it: the buyer should know this clause may be void.

### C6. Right to a receipt for each payment

**Weight within C:** 10%
**Applies to:** all with periodic payments
**Legal anchor:** Art. 9 Ley de Inquilinato (mandatory receipt, triple fine for not issuing), Art. 20 Ley de Inquilinato (receipt in tenement houses).

**Scale:**

| Score | Criterion |
|---|---|
| 10 | Explicit clause of the lessor's or seller's obligation to issue a receipt. |
| 6 | Implied but not expressly recorded (law applies supplementarily). |
| 0 | Clause exempting the seller or lessor from issuing receipts (void). |

### C7. Contract continuity on death or transfer

**Weight within C:** 10%
**Applies to:** ARV, ARC, APV, IVU
**Legal anchor:** Art. 27 Ley de Inquilinato (death of tenant does not extinguish, continues with heirs, spouse, companion, ascendants, descendants), Art. 28 Ley de Inquilinato (death of lessor or transfer of property does not extinguish).

**Scale:**

| Score | Criterion |
|---|---|
| 10 | Clause recognizes continuity or the contract is silent (law applies supplementarily). |
| 0 | Clause attempting to extinguish the contract on tenant's death or property transfer — contrary to Art. 27/28 and void per Art. 2 Ley de Inquilinato. |

---

## 7. Category D — Property risks (15%)

Measures legal and registry risks of the property, which can make the transfer void or cause the buyer to acquire an encumbered property unknowingly.

Some of these criteria require verification with public registries (Property and Mortgage Registry, FSV, Ministry of Housing) which are not integrated to the system in MVP. In those cases, the rubric detects what the contract declares or omits, and warns the user that material verification is their or their lawyer's responsibility.

### D1. Declared registry status

**Weight within D:** 20%
**Applies to:** CVC, CVP, APV, LEA, FSV
**Legal anchor:** Art. 1639 CC (warranty obligation to protect buyer in dominion and peaceful possession).

**Scale:**

| Score | Criterion |
|---|---|
| 10 | The contract declares the registry status of the property (matrícula, libro, folio) and shows attached proof. |
| 7 | Declares the property is free of liens but without attached proof. |
| 3 | Superficial mention of the property status. |
| 0 | The contract omits any mention of registry status. |

### D2. Bien de Familia regime (when applicable)

**Weight within D:** 20%
**Applies to:** all when an IVU link or regime reference is detected
**Legal anchor:** Art. 3 Ley IVU (transfers of property under Bien de Familia are absolutely void), Art. 14 Ley IVU (regime coverage), Art. 6-A Ley IVU (regime duration).

**Detection:** the contract mentions "Bien de Familia", "IVU", "adjudicación", or describes a property with historical institutional-program characteristics.

**Scale:**

| Score | Criterion |
|---|---|
| 10 | The property is not under Bien de Familia, or the regime has already lapsed (Art. 6-A: 10 years from the last installment payment), or a public deed cancelling the lien is shown. |
| 0 | The property is under Bien de Familia and a transfer is attempted without prior cancellation — Art. 3 Ley IVU absolute nullity. |

**Override:** triggers `art_3_ivu_family_homestead`. Score forced to 0.

**Unverifiable:** if the contract does not mention the regime but the property has suspicious institutional origin, the criterion is marked unverifiable and the user is advised to verify in the Property Registry.

### D3. Preventive FSV annotation

**Weight within D:** 15%
**Applies to:** CVC, CVP, APV, LEA, FSV
**Legal anchor:** Art. 55 Ley FSV (preventive annotation with retroactive effect), Art. 58 Ley FSV (without the Fund's consent no sale, lien, or right constitution can be recorded), Art. 59 Ley FSV (non-attachability).

**Scale:**

| Score | Criterion |
|---|---|
| 10 | The contract declares the property has no preventive FSV annotation or shows the Fund's consent letter. |
| 5 | Silence on the matter. Unverifiable; the user must verify with the Registry. |
| 0 | The contract declares FSV exists but does not show the Fund's consent — recording is impossible (Art. 58). |

### D4. Urbanism and construction permit

**Weight within D:** 20%
**Applies to:** CVC, CVP, APV, LEA when the property is in construction or recent project
**Legal anchor:** Art. 1 Ley Urbanismo y Construcción (competent authority: Ministry of Housing or municipality), Art. 2 (technical requirements), Art. 5 (start notice within 8 days, 25% fine of land + construction value), Art. 6 (one-year validity).

**Scale:**

| Score | Criterion |
|---|---|
| 10 | The contract cites permit number, recognized issuing authority, valid date. |
| 6 | Permit cited but with dubious format or no date. |
| 3 | Generic mention of the permit. |
| 0 | No permit mention, or permit > 1 year without evidence of work continuity (Art. 6 lapsed). |

### D5. Registered responsible professional

**Weight within D:** 10%
**Applies to:** CVC, CVP, APV, LEA when the property is in construction project
**Legal anchor:** Art. 4, 8 Ley Urbanismo y Construcción (architect or civil engineer registered with the National Registry).

**Scale:**

| Score | Criterion |
|---|---|
| 10 | Name and registration number of the responsible professional. |
| 6 | Name of the professional without registration number. |
| 3 | Generic mention ("the construction company"). |
| 0 | No responsible identified. |

### D6. Regularized subdivision (when applicable)

**Weight within D:** 15%
**Applies to:** CVC, CVP when the property is a lot in subdivision
**Legal anchor:** Ley Especial para la Regularización de Lotificaciones y Parcelaciones para Uso Habitacional (pending obtaining verbatim source).

**Scale (provisional, subject to confirmation when the law is obtained):**

| Score | Criterion |
|---|---|
| 10 | Subdivision registered with the Registry or in a documented regularization process. |
| 6 | Declaration of regularization but without attached documentation. |
| 3 | Subdivision prior to September 2012 (subject to regularization with constraints). |
| 0 | Lot not registered and not in regularization process. |

**Note:** this criterion is marked as `provisional_pending_corpus` while the law is not incorporated verbatim.

---

## 8. Category E — Abusive clauses and practices (10%)

Detects explicit violations of the Ley de Protección al Consumidor. Any clause that violates a non-waivable right is automatically void.

Each criterion is binary: 10 if absent, 0 if present. There is no intermediate gradation because abusive clauses are by definition void.

### E1. Waiver of non-waivable rights

**Weight within E:** 15%
**Applies to:** all
**Legal anchor:** Art. 5 LPC (non-waivable rights), Art. 17 lit. d LPC (abusive clause), Art. 2 Ley de Inquilinato (tenant's rights are non-waivable).

| Score | Criterion |
|---|---|
| 10 | No clause waives legal consumer rights. |
| 0 | Explicit waiver clause ("the buyer waives..."). Void clause. |

**Override:** triggers `art_5_lpc_non_waivable`. Score forced to 0.

### E2. Warranty waiver

**Weight within E:** 10%
**Applies to:** CVC, CVP, APV, LEA
**Legal anchor:** Art. 1644 CC (void agreement exempting in bad faith), Art. 1661 CC (known defects).

| Score | Criterion |
|---|---|
| 10 | No warranty exemption clause. |
| 0 | Explicit exemption clause. |

### E3. Burden-of-proof reversal

**Weight within E:** 10%
**Applies to:** all
**Legal anchor:** Art. 17 lit. e LPC.

| Score | Criterion |
|---|---|
| 10 | No burden reversal. |
| 0 | Clause placing the burden on the consumer. |

### E4. Automatic renewal without consent

**Weight within E:** 10%
**Applies to:** all with a term
**Legal anchor:** Art. 17 lit. f LPC, Art. 18 lit. k LPC.

| Score | Criterion |
|---|---|
| 10 | No automatic renewal, or it exists but requires express written consent. |
| 0 | Automatic renewal without consent. |

### E5. Notary imposed by the provider

**Weight within E:** 10%
**Applies to:** CVC, CVP, APV, LEA, FSV
**Legal anchor:** Art. 19 lit. d LPC (respect consumer's notary designation), Art. 20 lit. a LPC (prohibition to impose), Art. 44 lit. ñ LPC (very serious infraction).

| Score | Criterion |
|---|---|
| 10 | The buyer chooses the notary, or the contract does not impose a notary. |
| 0 | The seller imposes the notary. |

### E6. Blank signature on obligation documents

**Weight within E:** 10%
**Applies to:** all with financing
**Legal anchor:** Art. 18 lit. b LPC (prohibition to require blank signature, except for negotiable instruments with legal requirements), Art. 44 lit. c LPC (very serious infraction).

| Score | Criterion |
|---|---|
| 10 | Does not require blank signature. |
| 0 | Requires signing blank promissory notes, drafts, or other documents in blank. |

**Override:** triggers `art_18_lpc_blank_signature`. Score forced to 0.

### E7. Arbitration imposed in adhesion contract

**Weight within E:** 10%
**Applies to:** all adhesion contracts
**Legal anchor:** Art. 17 lit. h LPC, Art. 44 lit. g LPC (very serious infraction).

| Score | Criterion |
|---|---|
| 10 | Does not impose arbitration, or arbitration was freely negotiated between the parties. |
| 0 | Arbitration clause in adhesion contract. |

**Override:** triggers `art_17h_lpc_arbitration`. Score forced to 0.

### E8. Limitation of seller or lessor liability

**Weight within E:** 10%
**Applies to:** all
**Legal anchor:** Art. 17 lit. a LPC (abusive clause: exonerate, attenuate, or limit provider's liability for damages).

| Score | Criterion |
|---|---|
| 10 | No limitation or exoneration of liability. |
| 0 | Clause exempting the seller or lessor from damages caused by the good or service. |

### E9. Abusive penalty to the consumer for non-compliance

**Weight within E:** 15%
**Applies to:** all
**Legal anchor:** Art. 17 lit. i LPC (penalty must correspond to the damage caused to the provider).

**What is sought:** penalties for consumer non-compliance that exceed reasonably the damage caused to the provider.

| Score | Criterion |
|---|---|
| 10 | Penalties proportional to the damage, justified. |
| 5 | High but justified penalty by the nature of the contract. |
| 0 | Disproportionate penalty (e.g. losing everything paid for breaching one month), without correspondence to the damage. |

---

## 9. Category F — Transparency and clarity (5%)

Lowest-weight category but essential so the consumer can read and understand what they sign.

### F1. Spanish language and legible characters

**Weight within F:** 30%
**Applies to:** all
**Legal anchor:** Art. 22 LPC (adhesion contracts in Spanish, characters readable to the naked eye).

| Score | Criterion |
|---|---|
| 10 | Clear Spanish, legible typography. |
| 6 | Excessive technicality or fragments in another language. |
| 0 | Illegible characters, foreign language, or critical clauses in microscopic font. |

### F2. Referenced exhibits actually attached

**Weight within F:** 30%
**Applies to:** all
**Legal anchor:** Art. 22 LPC (no references to texts not delivered to the consumer, except laws), Art. 4 lit. n LPC (detailed explanation of obligations and exhibits).

| Score | Criterion |
|---|---|
| 10 | All referenced exhibits are attached. |
| 6 | Some exhibits missing but not critical. |
| 0 | Critical exhibits missing (plans, technical specifications, warranties, general conditions). |

### F3. Right of withdrawal communicated

**Weight within F:** 15%
**Applies to:** all contracts entered outside the provider's establishment or at a distance
**Legal anchor:** Art. 13-A LPC (right of withdrawal: 8 days, without justification, without penalty).

| Score | Criterion |
|---|---|
| 10 | Right communicated clearly with term and exercise form. |
| 5 | Partial mention of the right. |
| 0 | Not communicated, or clause denying or penalizing it. |

### F4. Total cost expressed

**Weight within F:** 15%
**Applies to:** CVP, APV, LEA, FSV
**Legal anchor:** Art. 19 lit. p LPC (approval letter with comparable total cost), Art. 31 lit. b final paragraph LPC (installment-sale advertising must state cash price and installment total price).

| Score | Criterion |
|---|---|
| 10 | Total cost expressed clearly and comparable with the cash price. |
| 5 | Total cost deducible but not expressed. |
| 0 | Total cost not expressed and difficult to compute from the clause. |

### F5. Effective annual rate expressed

**Weight within F:** 10%
**Applies to:** CVP, APV, LEA, FSV
**Legal anchor:** Art. 19 lit. j LPC, Art. 31 LPC final paragraph.

| Score | Criterion |
|---|---|
| 10 | Rate expressed as effective annual, as a percentage. |
| 5 | Monthly rate expressed but not converted to effective annual. |
| 0 | Rate not expressed. |

---

## 10. Score computation algorithm

```python
def compute_score(criteria_evaluated, contract_type):
    """
    criteria_evaluated: list of objects {criterion_id, score, weight_in_category, category, applicable, unverifiable, override_triggered}
    contract_type: enum CVC | CVP | ARV | ARC | APV | LEA | IVU | FSV
    """

    # 1. Check overrides
    overrides = [c for c in criteria_evaluated if c.override_triggered]
    if overrides:
        return {
            "score_total": 0.0,
            "band": "red",
            "override_active": True,
            "override_reasons": [o.override_triggered for o in overrides],
            "category_scores": compute_categories(criteria_evaluated),
        }

    # 2. Filter criteria applicable to the contract type
    applicable = [c for c in criteria_evaluated if contract_type in c.applicable_types]

    # 3. For each category, compute weighted score
    category_scores = {}
    for category in ['A', 'B', 'C', 'D', 'E', 'F']:
        criteria_cat = [c for c in applicable if c.category == category]
        if not criteria_cat:
            continue
        # Renormalize weights if some criteria do not apply
        total_weight = sum(c.weight_in_category for c in criteria_cat)
        score_cat = sum(c.score * (c.weight_in_category / total_weight) for c in criteria_cat)
        category_scores[category] = score_cat

    # 4. Combine categories with global weights
    global_weights = {'A': 0.20, 'B': 0.30, 'C': 0.20, 'D': 0.15, 'E': 0.10, 'F': 0.05}
    # Renormalize if some category has no applicable criteria
    effective_weights = {k: v for k, v in global_weights.items() if k in category_scores}
    weight_sum = sum(effective_weights.values())
    normalized_weights = {k: v / weight_sum for k, v in effective_weights.items()}

    score_total = sum(category_scores[k] * normalized_weights[k] for k in category_scores)

    # 5. Determine band
    if score_total >= 8.0:
        band = "green"
    elif score_total >= 5.0:
        band = "yellow"
    else:
        band = "red"

    return {
        "score_total": round(score_total, 1),
        "band": band,
        "override_active": False,
        "category_scores": category_scores,
    }
```

---

## 11. Result template

The report is generated in responsive HTML and converted to PDF for download, or served via public link with configurable TTL.

### 11.1 Report structure

**Section 1 — Header**
- Casa Segura logo
- Title: "Análisis de Contrato"
- Analysis ID (short UUID, e.g. `CS-2026-A1B2C3`)
- Analysis date
- Detected contract type (with explanation if reclassified, e.g. "Presented as compraventa, reclassified as financial leasing due to presence of the six indicators of Art. 2 Ley de Arrendamiento Financiero")
- Project name (extracted from contract)
- Header disclaimer: "Esto no es asesoría legal. Antes de firmar, consulta a un abogado."

**Section 2 — Overall verdict**
- Score 0–10 (large, band color)
- Band indicator with icon
- 2–3 sentence summary generated by LLM based on findings
- If override: prominent red box "Hallazgo crítico" with description

**Section 3 — Economic analysis**
- Key figures table: cash price, down payment, term, effective annual rate, monthly payment, total cost, overcost vs. benchmark
- Visual comparison against market benchmark (HTML horizontal bar)
- Computation of "how much more you pay relative to the market average in colones / dollars"
- Explicit Art. 1686 CC warning: "En El Salvador no existe la rescisión por lesión enorme. Si firmas este precio, no podrás impugnarlo después por motivo de precio excesivo. Por eso es importante revisar las cifras antes de firmar."

**Section 4 — Breakdown by category**
- Six collapsible blocks
- Each block: category name, weight, partial score with horizontal bar
- List of criteria within: pass, observation, fail, unverifiable
- Short justification for each

**Section 5 — Highlighted findings**
- Prioritized list: critical first, then serious, then observable
- Each finding:
  - Severity (red, yellow, green with observation)
  - Short title
  - Description
  - Cited contract clause (if locatable)
  - Legal basis with article and verbatim paraphrase from the corpus
  - Actionable recommendation

**Section 6 — Referenced legal bases**
- Unique list of articles cited throughout the report
- For each: law, article, brief paraphrase, link to corpus markdown
- Note: "These references come from a curated corpus of Salvadoran laws. If you find an error, report it to `errores@casasegura.sv`."

**Section 7 — Suggested actions**
- Three blocks:
  - "Antes de firmar, pídele al vendedor o arrendador" (actionable list)
  - "Lleva esto a tu abogado" (list of conversation points)
  - "Documentos que debes exigir" (list of documents)

**Section 8 — Footer**
- Extended disclaimer
- Version of the rubric used
- Version of the legal corpus
- Hash of the analysis for verification
- How to report errors
- "Casa Segura es una herramienta de orientación. No reemplaza asesoría legal profesional."

### 11.2 Example of individual finding (format, delivered to user in Spanish)

```
🔴 CRÍTICO — Tasa de interés efectiva anual fuera de mercado

Descripción:
La tasa de interés contratada es de 18% anual, lo cual está 9 puntos
porcentuales por encima del benchmark del mercado salvadoreño para
crédito hipotecario directo con desarrollador (9% anual, fuente BCR
agosto 2025).

Cláusula citada:
"Las cuotas mensuales devengarán intereses a la tasa del 1.5% mensual,
calculados sobre el saldo total adeudado." (Cláusula 6.2 del contrato)

Bases legales:
- Art. 12 LPC: en contratos de compraventa a plazos, los intereses se
  calculan sobre los saldos diarios pendientes de cancelar, con base en
  el año calendario. La cláusula citada calcula sobre el saldo total,
  lo cual viola este artículo.
- Art. 19 lit. j LPC: el proveedor de servicios financieros debe
  informar la tasa anual efectiva.

Recomendación:
Pídele al vendedor que (1) exprese la tasa como anual efectiva,
(2) confirme que el cálculo es sobre saldos diarios pendientes y no
sobre el saldo total, (3) considere reducir la tasa al rango de
mercado (8-10% anual). Sin esos cambios, este contrato te costará
aproximadamente USD 12,400 más que un crédito de mercado por el mismo
monto y plazo.
```

---

## 12. Persisted data model

Maintains the promise "no PII, no contract content". Only the project name and analysis metrics.

### 12.1 `project` table

```sql
CREATE TABLE project (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canonical_name TEXT NOT NULL,
    normalized_name TEXT NOT NULL UNIQUE, -- normalized slug: lowercase, no accents, no special characters
    first_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_analyzed TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    total_analyses INTEGER NOT NULL DEFAULT 0,
    avg_score NUMERIC(3,1), -- average of the scores of all analyses of the project
    metadata JSONB DEFAULT '{}'::jsonb -- extensible: {general_location, project_type, initial_source}
);

CREATE INDEX idx_project_normalized_name ON project (normalized_name);
```

**Justification:** the `project` entity allows aggregating intelligence across multiple contracts of the same project without storing personal data of the signer. The user receiving a report sees "Casa Segura has analyzed 12 contracts of Project X, average score 4.2", which is value without PII leakage.

### 12.2 `contract_analysis` table

```sql
CREATE TABLE contract_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    public_short_id TEXT UNIQUE NOT NULL, -- short ID for user, e.g. CS-2026-A1B2C3
    project_id UUID NOT NULL REFERENCES project(id),

    -- Type and result
    contract_type TEXT NOT NULL CHECK (contract_type IN (
        'CVC', 'CVP', 'ARV', 'ARC', 'APV', 'LEA', 'IVU', 'FSV', 'NOT_CLASSIFIABLE'
    )),
    contract_type_reclassified BOOLEAN NOT NULL DEFAULT FALSE,
    reclassification_reason TEXT, -- e.g. "presented as CVP, reclassified as LEA per Art. 2 LAF"

    score_total NUMERIC(3,1) NOT NULL CHECK (score_total >= 0 AND score_total <= 10),
    band TEXT NOT NULL CHECK (band IN ('green', 'yellow', 'red', 'not_analyzable')),
    override_triggered TEXT[], -- nullable; list of overrides if any

    -- Breakdown by category
    scores_by_category JSONB NOT NULL, -- {"A": 7.5, "B": 4.2, "C": 6.0, "D": 8.0, "E": 10.0, "F": 7.0}

    -- Aggregate counts, no content
    findings_count INTEGER NOT NULL DEFAULT 0,
    critical_findings_count INTEGER NOT NULL DEFAULT 0,
    unverifiable_count INTEGER NOT NULL DEFAULT 0,

    -- Economic summary (aggregate figures, not the original clause)
    economic_summary JSONB, -- {down_payment_pct, annual_rate, term_years, monthly_payment, total_cost, overcost_vs_benchmark}

    -- Versioning
    rubric_version TEXT NOT NULL,
    corpus_version TEXT NOT NULL,

    -- Delivery
    delivery_status TEXT NOT NULL DEFAULT 'pending' CHECK (delivery_status IN (
        'pending', 'sent_email', 'sent_whatsapp', 'available_link', 'expired'
    )),
    delivery_target_hash TEXT, -- hash of the email or phone, not the real data
    link_expires_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_contract_analysis_project ON contract_analysis (project_id);
CREATE INDEX idx_contract_analysis_short_id ON contract_analysis (public_short_id);
```

### 12.3 Retention policy

- `project`: indefinite. It is system-curated metadata.
- `contract_analysis`: 90 days from `created_at`. After that, it is fully anonymized: `delivery_target_hash` is erased, `economic_summary` is reduced to discrete buckets (e.g. "rate between 9-10%" instead of the exact value). This preserves project aggregate intelligence without re-identification risk.
- The report itself (HTML, PDF) is not persisted to disk. It is generated on demand from the `contract_analysis` row and served. If the user returns to the link, it is regenerated.

### 12.4 What is NOT stored, explicitly

- Contract text.
- OCR-extracted text.
- Clauses identified as findings (the report citation is generated at display time and discarded).
- Names of the parties (seller, buyer, lessor, tenant).
- Specific property addresses (beyond the project's general metadata).
- User's email or phone number (only the hash for delivery and retry).

---

## 13. Delivery modes

The report is generated once and served in up to three channels per user preference.

### 13.1 Email (PDF attached)

- The user provides an email.
- The system generates the PDF with WeasyPrint or similar from the HTML.
- The email is sent with the PDF attached and a brief message.
- Subject: "Tu análisis de contrato — Casa Segura — [contract type]"
- Body: one sentence with the score, the short analysis ID, and the disclaimer.
- Attachment: report PDF.
- The user's email is only saved as a hash for retry; discarded after sending.

### 13.2 WhatsApp (via Zavu)

- The user provides a phone number.
- The system sends a message with:
  - Large score
  - 2–3 critical findings in short bullets
  - Link to the full HTML report
  - Disclaimer
- Template (delivered in Spanish):

```
Casa Segura — Análisis listo

[band icon] Score: 4.2/10 — 🔴 Procede con cuidado

Encontramos esto:
• Tasa de 18% anual, 9 puntos sobre el promedio
• Sin mecanismo de fideicomiso para tu prima
• Cláusula que limita la responsabilidad del vendedor

Reporte completo: casasegura.sv/r/CS-2026-A1B2C3
(válido por 30 días)

Esto no es asesoría legal.
```

### 13.3 Public web link with TTL

- The system generates a URL with the analysis's `public_short_id`.
- Serves responsive HTML when accessed.
- Expires in 30 days by default, configurable.
- After expiration, the link shows: "Este análisis ya no está disponible. Casa Segura no almacena reportes de forma permanente para proteger tu privacidad."

### 13.4 On-demand re-delivery

While the analysis has not expired and the user has the `public_short_id`, they can request resend to the same email or number originally registered. The system verifies the hash matches and resends.

There is no way to ask for "your last analysis". Without the ID, no access. This preserves the privacy posture.

---

## 14. Configuration parameters

The `economic_benchmarks.yaml` file holds the values the system uses to compare against the market. Each value cites source and last update date.

```yaml
# economic_benchmarks.yaml
# Last update: 2025-08-XX
# Next review: every quarter

standard_down_payment:
  bank_or_fsv_purchase:
    value: 0.10
    note: "Standard 10% down payment in El Salvador for bank and FSV mortgage credit"
    source: "Banking practice; ABANSA"
  direct_developer_purchase:
    range: [0.05, 0.15]
    note: "Typical range for direct sale with developer"
    source: "Market practice"

interest_rate:
  bank_mortgage:
    range: [0.07, 0.09]
    source: "BCR — Active interest rates, August 2025"
    url: "https://www.bcr.gob.sv/..."
  fsv:
    range: [0.05, 0.07]
    source: "FSV — Current rates"
    note: "Subsidized"
  developer_direct:
    range: [0.08, 0.12]
    source: "Market observation"
  benchmark_reference:
    value: 0.09 # bank midpoint
    note: "Used as base for B2 scale"

credit_term:
  reasonable_range: [5, 25]
  ivu_legal_max: 30
  source: "Art. 2 Ley IVU"

total_cost_multiplier:
  healthy_max: 1.5
  high_max: 2.0
  excessive_min: 2.5
  note: "Total cost / cash price"

monthly_payment:
  ratio_healthy_max: 1.2
  ratio_high_max: 1.4
  ratio_excessive_min: 1.7
  note: "Monthly payment ÷ (total price / term in months)"

late_interest:
  reasonable_multiplier_over_ordinary: 1.5
  high_multiplier_over_ordinary: 2.0

prepayment:
  fee_reasonable_pct_max: 0.01
  fee_high_pct_max: 0.03

legal_references:
  rescission_for_gross_disparity:
    applies_in_el_salvador: false
    source: "Art. 1686 CC — el contrato de venta no podrá rescindirse por causa de lesión enorme"
  deed_costs_default:
    payer: "seller"
    source: "Art. 1610 CC"
    note: "By default; the contract may stipulate otherwise"
```

### 14.1 Benchmark update policy

- Rates: quarterly update with cited sources.
- Down payments: annual update or upon significant regulatory or market change.
- Any config change requires a PR with justification. The rubric versions the config commit hash in each analysis for reproducibility.

---

## 15. Known limitations

This rubric has explicit limitations declared to the user:

1. **Does not replace professional legal advice.** A Salvadoran lawyer may see nuances the rubric does not detect.
2. **Does not verify public registries.** The property's registry status, FSV annotations, professional registration in the National Architects and Engineers Registry, subdivision regularization — all that requires material verification the rubric does not perform in MVP. It is marked `requires_external_verification` and the user is told what to verify and where.
3. **The legal corpus is incomplete.** Ley Especial de Lotificaciones (affects D6) is missing, and Ley de Compras Públicas verbatim (affects "government project" fraud detection) is missing. When a criterion depends on pending corpus, it is marked `provisional_pending_corpus`.
4. **Economic benchmarks may go stale.** They are updated quarterly but the market may move faster in volatile moments.
5. **OCR may fail on scanned contracts.** If scan quality is low or paper is damaged, the system marks it `not_analyzable` and asks for resubmission.
6. **Does not detect fraud outside the contract.** If the developer lies verbally about something not in the contract, the rubric does not see it. It only evaluates the document.
7. **Does not personalize by the user's financial situation.** It does not know the signer's income, debts, or assets. Economic criteria compare against market benchmarks, not against personal payment capacity.
8. **Not predictive.** The score evaluates the contract today. It does not predict the developer's future behavior or macro conditions.

---

## 16. Appendix: Master criteria table

Tabular summary of the 38 defined criteria. For implementation.

| ID | Category | Weight (cat) | Weight (global) | Applicable types | Main anchor | Override |
|---|---|---|---|---|---|---|
| A1 | A | 25% | 5.00% | All | Art. 1605 CC; Art. 4 LI | art_1605_cc |
| A2 | A | 15% | 3.00% | All | Art. 18 LI; Art. 12-B LPC | — |
| A3 | A | 20% | 4.00% | All | Art. 1612, 1613 CC | art_1613_cc |
| A4 | A | 15% | 3.00% | All | Art. 6 LI; Art. 2 IVU; Art. 9 LAF | — |
| A5 | A | 10% | 2.00% | All | Art. 18 LI | — |
| A6 | A | 15% | 3.00% | APV, CVP with promise | Art. 1425 CC | art_1425_cc |
| B1 | B | 10% | 3.00% | CVP, APV, LEA, FSV | Art. 13, 43 LPC | — |
| B2 | B | 20% | 6.00% | CVP, APV, LEA, FSV | Art. 12, 19 LPC | — |
| B3 | B | 10% | 3.00% | CVP, APV, LEA, FSV | Art. 2 IVU | — |
| B4 | B | 15% | 4.50% | CVP, APV, LEA, FSV | Derived computation | — |
| B5 | B | 10% | 3.00% | CVP, APV, LEA, FSV, ARV | Derived computation | — |
| B6 | B | 10% | 3.00% | All | Art. 12-A, 19 LPC | — |
| B7 | B | 10% | 3.00% | CVP, APV, LEA, ARV, FSV | Art. 12, 17 LPC | art_12_lpc |
| B8 | B | 8% | 2.40% | CVP, APV, LEA, FSV | Art. 17, 19 LPC | — |
| B9 | B | 7% | 2.10% | All | Art. 13, 17 LPC; Art. 1613 CC | art_13_lpc |
| C1 | C | 20% | 4.00% | CVP, APV | Art. 13, 43 LPC | — |
| C2 | C | 15% | 3.00% | CVP, APV, LEA, ARV, FSV | Art. 13 LPC; Art. 1714 CC | — |
| C3 | C | 15% | 3.00% | CVP, APV, LEA, ARV, FSV | Art. 13 LPC; Art. 1714 CC | — |
| C4 | C | 15% | 3.00% | All | Art. 13, 43 LPC; Art. 1675, 1677 CC | — |
| C5 | C | 15% | 3.00% | CVC, CVP, APV, LEA, FSV | Art. 1639–1670 CC; Art. 1644 CC | art_1644_cc |
| C6 | C | 10% | 2.00% | All with periodic payments | Art. 9, 20 LI | — |
| C7 | C | 10% | 2.00% | ARV, ARC, APV, IVU | Art. 27, 28 LI | — |
| D1 | D | 20% | 3.00% | CVC, CVP, APV, LEA, FSV | Art. 1639 CC | — |
| D2 | D | 20% | 3.00% | All when IVU applies | Art. 3 IVU | art_3_ivu_family_homestead |
| D3 | D | 15% | 2.25% | CVC, CVP, APV, LEA, FSV | Art. 55, 58 FSV | art_58_fsv |
| D4 | D | 20% | 3.00% | CVC, CVP, APV, LEA when project under construction | Art. 1, 2, 5, 6 LUC | — |
| D5 | D | 10% | 1.50% | CVC, CVP, APV, LEA when project under construction | Art. 4, 8 LUC | — |
| D6 | D | 15% | 2.25% | CVC, CVP when subdivision | Ley Lotificaciones (provisional) | — |
| E1 | E | 15% | 1.50% | All | Art. 5 LPC; Art. 2 LI | art_5_lpc_non_waivable |
| E2 | E | 10% | 1.00% | CVC, CVP, APV, LEA | Art. 1644, 1661 CC | — |
| E3 | E | 10% | 1.00% | All | Art. 17 LPC | — |
| E4 | E | 10% | 1.00% | All with term | Art. 17, 18 LPC | — |
| E5 | E | 10% | 1.00% | CVC, CVP, APV, LEA, FSV | Art. 19, 20, 44 LPC | — |
| E6 | E | 10% | 1.00% | All with financing | Art. 18, 44 LPC | art_18_lpc_blank_signature |
| E7 | E | 10% | 1.00% | All adhesion contracts | Art. 17, 44 LPC | art_17h_lpc_arbitration |
| E8 | E | 10% | 1.00% | All | Art. 17 LPC | — |
| E9 | E | 15% | 1.50% | All | Art. 17 LPC | — |
| F1 | F | 30% | 1.50% | All | Art. 22 LPC | — |
| F2 | F | 30% | 1.50% | All | Art. 22, 4 LPC | — |
| F3 | F | 15% | 0.75% | Contracts off-premises or at distance | Art. 13-A LPC | — |
| F4 | F | 15% | 0.75% | CVP, APV, LEA, FSV | Art. 19, 31 LPC | — |
| F5 | F | 10% | 0.50% | CVP, APV, LEA, FSV | Art. 19, 31 LPC | — |

**Note:** the global weights sum slightly above 100% because some criteria do not apply to certain contract types. The §10 algorithm renormalizes per detected contract type.

---

## 17. Open decisions (require product confirmation)

Before implementing, six decisions need explicit confirmation:

1. **Is Flow 1 (project verification by photo of the sign) kept?** The approach change eliminated the blacklist and weakened reputation search. Without those two pillars, Flow 1 is left with only the permit check. Three options: (a) eliminate it, (b) absorb it into the contract analysis (extracting the permit from the contract itself), (c) keep it limited.

2. **Who pays for OpenRouter calls in production?** The project is hackathon open source but the rubric requires LLM per analysis. Without an explicit sustainability model, the system in production has a financial ceiling.

3. **Do we validate economic benchmarks against official source before production?** The rates and down payments in §14 are illustrative. So the system does not give incorrect information, they must be calibrated against BCR / SSF / ABANSA before any deploy to real users.

4. **Does the report always show the Art. 1686 CC warning?** My recommendation is yes. It is little-known and highly relevant information. But it opens the door to "Casa Segura told me I could not rescind" if the user does not read carefully.

5. **What is the exact public link TTL policy?** I proposed 30 days. Shorter = less leakage risk but more friction. Longer = the opposite.

6. **How is it validated that the contract belongs to the project it says it does?** The system extracts the project name from the contract but does not verify against any external source. A fraudster could use a real project name so their analysis associates with the correct entity. Mitigation: the report always warns "el nombre del proyecto se extrajo del contrato; no se verificó contra fuente externa".

---

**End of document — version 0.1.**
