---
law_id: ley-ivu
title: Ley sobre Contratos del Instituto de Vivienda Urbana
short_title: IVU
decreto: D.L. 1486
fecha_emision: 1954-05-25
diario_oficial: "27-05-1954"
reformas_count: 7
ultima_reforma: "D.L. 307, 25-02-1986 (D.O. 52, T.290, 18-03-1986)"
estado: vigente
materia: Vivienda — contratos institucionales
source_url: https://www.jurisprudencia.gob.sv/DocumentosBoveda/D/2/1950-1959/1954/06/88A59.PDF
last_verified: 2026-05-09
relevance_to_casa_segura: medium-high
covers:
  - rental, lease-with-promise-of-sale, and sale contracts by Instituto de Vivienda Urbana (IVU)
  - '"Bien de Familia" regime'
  - special procedural rules for IVU contracts
  - eviction and termination grounds for institutional housing
---

# Ley sobre Contratos del Instituto de Vivienda Urbana

## Plain-language summary

Special law governing contracts (arrendamiento, arrendamiento con promesa de venta, compraventa) signed by the **Instituto de Vivienda Urbana (IVU)**, the historic state housing institute. Sets the maximum contract term (20 years, extendable to 30), caps interest, defines the **Bien de Familia** restriction (adjudicatees cannot sell, encumber, or transfer without permission), enumerates termination grounds, and lays out a special procedural fast-track for IVU evictions.

Although the IVU is no longer the dominant social housing operator (FSV and Ministerio de Vivienda overshadow it), this law remains in force for contracts signed under the IVU regime, and its concepts — particularly **Bien de Familia** — continue to be referenced in current institutional housing.

## Application to Casa Segura

This law matters when:
- The contract is presented as an IVU adjudication or "Bien de Familia" purchase
- A "developer" claims affiliation with IVU or successor institutions
- The buyer is being asked to "transfer" a property that may still be under the Bien de Familia regime (red flag — likely null per art. 3)

Findings the verdict engine should ground here:

- **`bien_de_familia_transfer_attempt`** → art. 3 (absolute nullity)
- **`institutional_contract_term_excessive`** → art. 2 (max 30 years)
- **`institutional_contract_interest_excessive`** → art. 2 (cap on interest)
- **`mismatched_buyer_for_bien_familia`** → art. 7 (nullity if buyer owns property over ¢10,000)
- **`institutional_termination_grounds`** → art. 4, 5

## Key articles

### Art. 1 — Scope
The law regulates the essential conditions and actions arising from contracts of arrendamiento, arrendamiento con promesa de venta, or compraventa of houses, apartments in multifamily buildings, or other properties that the IVU grants — with or without the Bien de Familia regime.

### Art. 2 — Term and interest cap
Contracts under this law follow common legislation, IVU's own regime, and Junta Directiva resolutions. **No property may be delivered without prior Junta adjudication and a formalized contract.**

The term of arrendamiento con promesa de venta and venta a plazo is **20 years**, extendable to **30 years** for socioeconomic reasons.

Interest rate on balances is set by the Junta Directiva, considering how funds were obtained and IVU's financial situation, but cannot exceed **3.5% over the rate IVU pays on the underlying funds**, and that rate cannot be increased afterward for any reason. For sales clearly outside the institutional social purpose, the floor is 12% annual.

> **Casa Segura signal:** if a contract claims IVU origin and shows interest rates dramatically above IVU's regulatory cap, flag as **red** with art. 2 cite.

### Art. 3 — Bien de Familia restrictions (CRITICAL)
Tenants or buyers of IVU-adjudicated housing **under the Bien de Familia regime cannot transfer, encumber, or alienate** the property except per applicable legal dispositions.

**Acts or contracts in violation of this provision are absolutely null**, without prejudice to IVU's rights.

> **Casa Segura signal:** this is the single most important article in this law for fraud detection. If a "seller" is offering a property that is still under the Bien de Familia regime (verifiable in the Registro de la Propiedad Raíz), the sale is null and the buyer would lose money. **Flag as red.** Cite art. 3.

### Art. 4 — Causes for termination of arrendamiento or arrendamiento con promesa de venta
1. Default in three consecutive payments (no prior notice required);
2. Using the property for illegal businesses, alcoholic beverage outlets (except commercial-type housing), factories or workshops causing neighborhood harm;
3. Construction alterations without IVU consent;
4. Adjudicatee (or family) leaving the property uninhabited for more than 6 consecutive months without IVU permission;
5. Transferring rights or subleasing without prior IVU authorization.

The 3-month default can be extended to 6 months for IVU-recognized just cause.

### Art. 4-A — Salary garnishment
IVU may collect overdue installments via salary retention if: (a) property declared vacant for default > 2 months; (b) adjudicatee owes 3+ installments; (c) property declared vacant for default > 2 times in one year.

The retention amount is capped at **20% of monthly salary**.

### Art. 4-B — IVU as credit institution
For purposes of debts owed by workers under IVU contracts, the IVU is treated as a credit institution.

### Art. 5 — Causes for termination of compraventa
Sales contracts may be resolved by:
- Default in 3 consecutive payments;
- The grounds (b), (c), (d) of art. 4;
- Renting the property without IVU permission, when not under Bien de Familia;
- Alienating or encumbering, except under legal exceptions.

### Art. 6 — Validity period of termination grounds
The grounds in arts. 4 and 5, plus the power of attorney in art. 9, are deemed incorporated in contracts whether stated or not, and are valid for **10 years** from contract date for housing under or outside Bien de Familia. Exceptions: default lasts as long as the property is unpaid; Bien de Familia grounds while the regime applies.

### Art. 6-A — Bien de Familia duration
- Cash sale: Bien de Familia regime lasts **10 years**.
- Term sale: regime ends when last payment is received, provided ≥ 10 years from signing.
- Cancellation requires public deed registered.
- Does not apply when paid via bank/financial-institution credit per Decree 588 of 1964.

### Art. 7 — Nullity for ineligible buyers
Sales or arrendamiento con promesa de venta to **persons who own property worth more than ¢10,000** (per IVU appraisal) are **absolutely null**.

> **Casa Segura signal:** this is a screening rule for institutional social housing. Adjudicatees must be in genuine need.

### Art. 8 — Effects of termination on payments and improvements
On termination, resolution, or nullity, IVU is not obligated to refund payments or improvements — they're treated as compensation for use. Exceptions:
- Excess of payments above the use value during tenure;
- Permanent improvements made with IVU consent (with 5% annual depreciation deducted).

### Art. 9 — Procedural representation
All capable beneficiaries (and legal representatives for minors) must appear at the sale deed signing. They must grant special power of attorney to the **Procurador General de Pobres** for representation in the resolution deed if default occurs.

### Art. 10 — Procedural rules
Special procedural rules:
- Competent court for arrendamiento cases: Juzgado Especial de Inquilinato (or Juez de lo Civil/Primera Instancia outside SS).
- Competent court for compraventa cases: Juez de lo Civil de San Salvador.
- IVU enjoys "beneficio de pobreza" for judicial bonds.
- Service may be by direct notification or by single Diario Oficial + 2 newspapers publication.
- Sumario (summary) procedure for termination/resolution/nullity claims regardless of amount.
- Executive process based on a certification by IVU's President + Manager.
- Decree of embargo and final sentence are not appealable; only liability and casación recourses.

### Art. 11 — Eviction (lanzamiento)
Once final judgment is entered, the Alcalde Municipal or Gobernador proceeds with eviction per Decree of 5 January 1884. A simple written request from IVU is sufficient. The Juez de Paz has concurrent jurisdiction.

### Art. 12 — Occupants without contract
People occupying IVU houses without a written contract have **preference** to obtain that contract, provided they meet requirements and have not incurred any art. 4 cause. Their prior payments apply to the price.

### Art. 13 — Ley de Inquilinato does NOT apply
For terminations of IVU arrendamientos, the Ley de Inquilinato does **not** apply.

> **Casa Segura signal:** this means IVU contracts have *fewer* tenant protections than ordinary rentals. Worth flagging during contract verification: don't try to apply Inquilinato art. 24 grounds to an IVU lease.

### Art. 14 — Bien de Familia scope
All single-family housing adjudications by IVU at or under the legal limit are under Bien de Familia. Multifamily apartments are subject to the **Ley de Propiedad Inmobiliaria por Pisos y Apartamentos**, not Bien de Familia.

### Art. 15 — Special character
This law has special character and prevails over general laws on the same matter. For everything not covered, the IVU Organic Law applies.

### Art. 16 — Regulation
The Executive Branch (Justice and Economy) may regulate this law.

## Cross-references

- **Apartments / multifamily**: Ley de Propiedad Inmobiliaria por Pisos y Apartamentos (not in this corpus yet — common reference).
- **FSV-financed purchases**: see `03-ley-fsv.md`.
- **General rentals**: see `01-ley-inquilinato.md` (does NOT apply to IVU lease terminations per art. 13).
- **Special-rules-prevail**: this law per art. 15 prevails over Ley de Inquilinato in case of overlap.

## Practical fraud patterns to watch

| Pattern | Article |
|---|---|
| "Seller" offering an IVU/Bien-de-Familia property without showing IVU release | art. 3 |
| Sale price suggests buyer is well above ¢10,000-net-worth ceiling for Bien de Familia | art. 7 |
| Contract claims an IVU connection but interest exceeds 3.5% over IVU's funding rate | art. 2 |
| Contract tries to apply Ley de Inquilinato protections to an IVU rental | art. 13 |

## Citation format for findings

```json
{
  "law_id": "ley-ivu",
  "article": "Art. 3",
  "anchor": "art-3",
  "url": "/laws/02-ley-ivu.md#art-3",
  "official_source": "D.L. 1486 de 25-05-1954, IVU Special Law"
}
```
