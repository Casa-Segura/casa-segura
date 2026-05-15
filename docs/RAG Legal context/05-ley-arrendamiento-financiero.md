---
law_id: ley-arrendamiento-financiero
title: Ley de Arrendamiento Financiero
short_title: Arrendamiento Financiero (Leasing)
decreto: D.L. 884
fecha_emision: 2002-06-20
diario_oficial: "Nº 126, Tomo 356, 09-07-2002"
reformas_count: 1
ultima_reforma: "D.L. 647, 17-03-2005 (D.O. 55, T.366, 18-03-2005)"
estado: vigente
materia: Leyes financieras — Arrendamiento financiero
sources:
  - https://www.ssf.gob.sv/descargas/Leyes/Leyes%20Financieras/Ley%20de%20Arrendamiento%20Financiero.pdf
  - https://sv.vlex.com/vid/ley-arrendamiento-financiero-644825869
last_verified: 2026-05-09
relevance_to_casa_segura: medium-high
covers:
  - financial leasing contracts (movable and immovable property)
  - parties (Proveedor, Arrendador, Arrendatario)
  - obligations and prohibitions
  - registration in Registro de Comercio
  - tax treatment
  - special procedural rules (executive force, inembargabilidad)
---

# Ley de Arrendamiento Financiero

## Plain-language summary

Special law regulating **financial leasing (leasing)** contracts in El Salvador — the only Central American country with a dedicated leasing statute. A financial lease is a contract where the **arrendador** (lessor) grants the use of a movable or immovable good to the **arrendatario** (lessee) for a forced-compliance term in exchange for a canon (rent), with three end-of-term options: **buy at predefined price, return, or renew**.

The law explicitly **excludes civil rentals** — those follow the Ley de Inquilinato or common civil law. The lessor is not responsible for choices of supplier or asset (those are the lessee's). The contract must be in writing (public deed or authenticated private document) and **registered in the Registro de Comercio** to be enforceable against third parties.

The law gives lessors strong protection: leased goods are not part of the lessee's bankruptcy estate, the contract has executive force, and the lessor can request seizure as a precautionary measure.

## Application to Casa Segura

This law matters in two scenarios for Casa Segura:

1. **Real estate "sales" that are actually leases.** A common fraud pattern is to present a leasing contract as a "compraventa con financiamiento". The buyer pays canons for years, then discovers ownership requires exercising a purchase option (often at a higher price than represented). Casa Segura should detect when a contract has lease-with-purchase-option mechanics dressed up as a sale.

2. **Real estate leases mislabeled as financial.** Conversely, a regular rental might be dressed up as a "leasing" to escape Ley de Inquilinato protections. The law explicitly says civil rentals are NOT covered (art. 1).

Findings the verdict engine should ground here:

- **`leasing_disguised_as_sale`** → arts. 2, 7
- **`rental_disguised_as_leasing`** → art. 1 (civil rentals excluded)
- **`leasing_contract_unregistered`** → art. 7 (must be in Registro de Comercio for third-party effects)
- **`leasing_excessive_penalty_clause`** → art. 9 (modification damages)
- **`leasing_lessor_obligation_evasion`** → art. 5

## Key articles

### Art. 1 — Scope (CRITICAL)
This law applies to financial leasing contracts and the parties that sign them. **Civil rental operations are NOT subject to this law.**

> **Casa Segura signal:** if a contract says "arrendamiento financiero" but lacks a purchase option, forced term, or supplier-arrendador-arrendatario triangle, it's likely a civil rental — Ley de Inquilinato applies. Conversely, if a contract has all the leasing characteristics but is labeled as a sale, the buyer should know they don't own the property until they exercise the purchase option. Cite art. 1, art. 2.

### Art. 2 — Definition (CRITICAL)
**Financial leasing** is the contract where the lessor grants the use and enjoyment of specified movable or immovable goods, **for a forced-compliance term**, to a lessee who must pay canon and other costs.

**At the end of the term, the lessee has the option** to:
- Buy the asset at a **predefined price**;
- Return it; or
- Extend the term.

The **lessee chooses the supplier and the asset**. The lessor is therefore not responsible for favorable or unfavorable juridical effects of supplier/asset choice — except when the lessor is also the supplier.

> **Casa Segura signal:** if a "sale contract" has these three end-options instead of immediate ownership transfer, it's a financial lease, not a sale. The buyer must understand they don't own the property during the canon period.

### Art. 3 — Parties
The contract has three parties:
- **Proveedor (Supplier)**: who transfers ownership of the asset to the lessor. Can be a habitual seller, an occasional seller, or the lessor itself.
- **Arrendador (Lessor)**: who delivers the asset in financial leasing.
- **Arrendatario (Lessee)**: who obtains the right to use, enjoy, and economically exploit the asset.

### Art. 4 — Supplier obligations
The supplier must:
1. Deliver the asset to the lessee when authorized by the lessor;
2. Ensure assets are free of encumbrances, in working order, without hidden defects;
3. Honor the warranty;
4. Comply with consumer protection law;
5. Other contractual obligations.

### Art. 5 — Lessor obligations
The lessor must:
1. Pay the supplier the agreed price on time;
2. Maintain leased goods free of embargoes during the term, to ensure peaceful possession;
3. Sanitize for evicción;
4. Other contractual obligations.

The lessor may, with party agreement, **assign to the lessee its rights and actions** against the supplier. When the lessor is also the supplier, both sets of obligations apply.

> **Casa Segura signal:** a leasing contract that lets the lessor encumber the property during the term in ways that disturb the lessee's possession violates art. 5(b). Flag.

### Art. 6 — Lessee obligations
During the term, the lessee must:
1. Pay canons in agreed time;
2. Assume risks and benefits of the asset's physical/economic nature;
3. Respond civilly and criminally for use of the leased asset;
4. Respect the lessor's property right and assert it against third parties — therefore in bankruptcy, concurso, or restructuring, **leased assets are NOT part of the lessee's estate** and are excluded for legal effects;
5. Other contractual obligations.

### Art. 7 — Formality and registration (CRITICAL)
The financial leasing contract must be in writing — **public deed or authenticated private document**. To be enforceable against third parties, it must be **inscribed in the Registro de Comercio**. Inscription costs are paid by the lessee unless otherwise agreed. The fee is **$0.23 per thousand**, capped at **$2,300**.

> **Casa Segura signal:** an unregistered leasing contract is risky — third-party purchasers without notice could prevail. Verify Registro de Comercio inscription. Cite art. 7.

### Art. 8 — Prohibitions on lessee
The lessee may NOT:
- Transfer or transmit the leased goods;
- Constitute real guarantees on them for own obligations;
- Include them in insolvency, bankruptcy, dissolution, liquidation, or reorganization estates.

Lessor may seek indemnification + criminal sanctions for violations.

### Art. 9 — Term and unconditionality (CRITICAL)
**The contract term is a right of the lessor**, modifiable only with lessor's acceptance and full compensation for damages. Damages are presumed to equal the sums the lessor would have received during the original term, and may be set contractually.

The lessee's obligation to pay canons is **unconditional**: payable whether or not the lessee is exploiting the asset, since exploitation risks are entirely the lessee's. Exception: when non-use is the lessor's fault.

> **Casa Segura signal:** if a "buyer" in a contract presented as a sale finds an art. 9-style penalty (e.g. early-cancellation = full remaining canons), that's a strong indicator it's a financial lease, not a sale.

### Art. 10 — Insurance
Parties may agree on insurable risks per asset nature. **All risks (insured or not) are the lessee's**. The lessor is the policy beneficiary. The lessee covers any deductible. Excess after lessor's costs is returned to the lessee.

### Art. 11 — Taxes and obligations
**All taxes, fees, fines, and penalties on tenure, possession, exploitation, or circulation of the asset** are paid by the **lessee**.

> **Casa Segura signal:** if a leasing contract presented as a sale shifts all property taxes and fines to the "buyer", that's the lessee allocation under art. 11 — supports the leasing reclassification.

### Art. 12 — Sale and lease-back
Lessors may also do **venta y retroarriendo** (sale and lease-back), which is NOT a financial leasing operation and follows tax legislation.

### Art. 13 — Accounting
Financial leasing accounting follows the dispositions of the Consejo de Vigilancia de la Profesión de Contaduría Pública y Auditoría.

## Tax provisions (Title III)

### Art. 14 — Lessee deductions (Income Tax)
Lessees may deduct canons against income from contracts on assets directly producing taxable income. If income is partly taxable and partly exempt, only the taxable share is deductible.

### Art. 15 — Lessor depreciation
Lessor may deduct depreciation of owned assets. **For real estate (immovable goods), depreciation must be over the contract term** but **never less than 7 years**. Less than 7 years → art. 30 of Ley de Impuesto sobre la Renta applies.

When the lessee exercises the immovable purchase option, they may deduct the last canon under art. 30 ISR. For movable goods, lessee gets the depreciation deduction on subsequent ownership.

### Art. 16 — International leasing
Subject to Código Tributario and tax laws. Special rules for machinery/equipment imports under leasing for State-tendered works (D.L. 647/2005).

### Art. 17 — Real estate leasing tax (CRITICAL)
**Impuesto sobre Transferencia de Bienes Raíces** is owed only **at the lessor's acquisition** of the property — base = real or commercial value at acquisition.

**When the lessee exercises the purchase option, the transfer tax is NOT owed.**

Subsequent transfers after lessee acquisition do owe the tax.

> **Casa Segura signal:** a fraudulent seller may misuse this exemption. Verify it's actually a registered leasing operation — not a fake leasing wrapper to evade transfer tax.

## Special dispositions (Title IV)

### Art. 18 — Executive force
On lessee default, leasing contracts have **executive force** and follow the executive procedure of the Ley de Procedimientos Mercantiles. With the suit, the lessor must attach a contador's certification of the debit balance.

The lessor may request **seizure of the leased asset as precautionary measure** — must be decreed within 3 working days. To dispose of the seized asset, the lessor must post a bond equal to the asset value.

### Art. 19 — Inembargabilidad
Disputes over including leased assets in lessee's bankruptcy estate must resolve **recognizing the lessor's exclusive ownership and excluding leased assets from the estate**. Lessor's bankruptcy: cannot include leased-out assets in own estate.

## Supplementary application (Title V)

### Art. 20 — Supletoriedad
For everything not in this law: mercantile, civil, tax, registry, cadastral, consumer protection, and environmental norms apply if not contrary to this law.

## Final dispositions (Title VI)

### Art. 21 — Preferential application
By special character, this law prevails over any contrary law.

### Art. 22 — Effective date
Decree entered into force 60 days after Diario Oficial publication (effectively September 2002).

## Practical fraud patterns to watch

| Pattern | Article |
|---|---|
| "Sale" contract has forced term + canons + purchase option (financial lease characteristics) | art. 2 |
| "Sale" contract shifts all taxes, fees, risks to "buyer" | arts. 6, 10, 11 |
| "Sale" contract has art. 9-style early-termination penalty | art. 9 |
| Leasing contract not registered in Registro de Comercio | art. 7 |
| Contract claims real estate transfer tax exemption without being a registered leasing | art. 17 |
| Civil rental dressed up as "leasing" to escape Ley de Inquilinato | art. 1 |
| Lessee tries to be made responsible for lessor's encumbrances on the property | art. 5(b) |
| Contract requires lessee to include leased asset as guarantee for other debts | art. 8 |

## Cross-references

- **Civil rentals**: see `01-ley-inquilinato.md` (NOT covered by this law).
- **Real estate transfer tax**: Ley del Impuesto sobre Transferencia de Bienes Raíces.
- **Mercantile registration**: Código de Comercio + Ley de Procedimientos Mercantiles (for executive process).
- **Consumer protection**: Ley de Protección al Consumidor.

## Citation format for findings

```json
{
  "law_id": "ley-arrendamiento-financiero",
  "article": "Art. 2",
  "anchor": "art-2",
  "url": "/laws/05-ley-arrendamiento-financiero.md#art-2",
  "official_source": "D.L. 884 de 20-06-2002, D.O. Nº 126, T.356, 09-07-2002"
}
```
