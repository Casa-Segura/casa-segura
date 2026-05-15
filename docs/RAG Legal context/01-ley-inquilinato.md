---
law_id: ley-inquilinato
title: Ley de Inquilinato
short_title: Inquilinato
decreto: D.L. 2591
fecha_emision: 1958-02-18
diario_oficial: "Nº 35, Tomo 178, 20-02-1958"
reformas_count: 10
ultima_reforma: "D.L. 712, 18-09-2008 (D.O. 224, T.381, 27-11-2008)"
estado: vigente
materia: Derecho Civil — Arrendamiento de vivienda
source_url: https://www.jurisprudencia.ues.edu.sv/oajc/leyes/LegislacionCivil/Ley%20de%20Inquilinato.pdf
last_verified: 2026-05-09
relevance_to_casa_segura: high
covers:
  - rental contracts (vivienda, locales comerciales, oficinas)
  - mesones (rooming houses)
  - tenant rights and protections
  - termination causes
---

# Ley de Inquilinato

## Plain-language summary

Salvadoran tenancy law for rentals of housing and small commercial premises (active business value ≤ ¢15,000), schools, and professional offices. Establishes that rental contracts must be in writing, lists tenant rights that cannot be waived, regulates rent increases, requires landlords to issue receipts, and lists the only causes by which a landlord can terminate a rental and evict.

The law is **deeply protective of tenants** as a matter of public policy. Any clause in a contract that tries to waive these protections is null. Many procedural articles (30–54) were repealed in 2008 when the matter passed to civil/family courts under the Código Procesal Civil y Mercantil — substantive rights remain in force.

## Application to Casa Segura

This is the primary law for **Flow 2 (contract check)** when the contract is an `arrendamiento` (rental). Findings the verdict engine should ground here:

- **`written_contract_required`** → art. 4, 18
- **`required_clauses_present`** (names, property ID, price) → art. 4, 18
- **`tenant_rights_unwaivable`** (any clause attempting to waive protections) → art. 2
- **`receipt_obligation`** → art. 9, 20
- **`payment_via_court_when_landlord_refuses`** → art. 10
- **`termination_only_for_listed_causes`** → art. 24
- **`succession_on_tenant_death`** → art. 27
- **`sale_does_not_terminate_lease`** → art. 28

## Scope

### Art. 1 — Scope
The law covers rentals and subleases of houses and premises used for: (a) housing; (b) commercial or industrial establishments where the active business value does not exceed ¢15,000 and the tenant lives in adjacent premises and owns the business; (c) educational centers under the Ministry of Culture or UES; (d) public and professional offices, clinics.

### Art. 2 — Rights are non-waivable
Tenant rights granted by this law are non-waivable. Any clause designed to evade these provisions, expressly or surreptitiously, has no value.

> **Casa Segura signal:** if a contract contains a clause that says the tenant waives any right granted by this law (e.g. "el inquilino renuncia a..."), flag as **red**: such a clause is automatically null under art. 2.

### Art. 3 — Out-of-scope cases
For rentals not covered by this law (subject to common dispositions), if termination is sought due to non-payment, no `desahucio` or `reconvención de pago` is required and common courts apply the procedure in Chapter V Section 2.

## Chapter II — Rentals of houses and premises

### Art. 4 — Written contract required
Every rental or sublease contract under this law, signed after the law's effective date, must be in writing and must state: (i) name and personal details of landlord and tenant, (ii) data sufficient to identify the property, (iii) price, (iv) form of payment.

Contracts with rent under ¢300/month are exempt from stamp tax.

> **Casa Segura signal:** if the contract is verbal, or missing any of the four required elements, flag as **yellow** (or **red** if multiple are missing). Cite art. 4.

### Art. 5 — Penalty for missing written contract
If there is no written contract (in cases requiring it), the fault is the landlord's, who incurs a fine equal to 50% of the monthly rent, or ¢10–50 if rent cannot be established.

### Art. 6 — Term clauses
A term may be set, but it only binds the tenant to pay rent during the term. The landlord cannot demand the property back at term end if the tenant continues paying — except for the causes in art. 24.

> **Casa Segura signal:** if the contract claims the landlord can recover the property at term end without one of the art. 24 causes, that clause is unenforceable.

### Art. 7 — Rent ceiling (legacy from 1973)
Rents on existing rentals cannot exceed those paid as of 31 Dec 1973 if those were ≤ ¢500/month. Does not apply to new properties or those never rented before. Detailed declaration procedure to courts. (Mostly historical relevance now.)

### Art. 8 — Authorized rent increases
The landlord can be authorized to raise rent only if: (a) improvements were made post-rental with tenant or judicial permission representing ≥20% of property value; or (b) the tenant subleased and there's a notable disproportion. Increase capped at 10% annually on improvement cost.

### Art. 9 — Receipt obligation (rental contract)
Landlords are obligated to issue a receipt for any payment, total or partial. Penalty for non-compliance: triple the amount for which no receipt was issued. The tenant is obligated to acknowledge having received the receipt (signature on landlord's stub or fingerprint).

> **Casa Segura signal:** if the contract has a clause saying "no receipts will be issued" or similar, flag as **red**. This violates a non-waivable obligation.

### Art. 10 — Payment via court when landlord refuses
If the landlord refuses to receive payment or to issue a receipt, the tenant may deposit rent in the competent court within 8 days of the due date and is not in default.

### Art. 11 — Harassment by landlord
Any act by the landlord (or those depending on him) that harms the tenant — e.g. cutting off water or electricity — incurs a fine of ¢100, without prejudice to criminal sanctions.

## Chapter III — Mesones (rooming houses)

### Art. 12 — Mesón scope
A "mesón" is a house with at least four rooms rented separately to families or individuals with shared services. Family-type houses ("casas de pupilos") are not mesones.

### Art. 13 — Parties to a mesón rental
The landlord, tenant, mesonero (caretaker), and subtenant.

### Art. 14 — Right to sublet implied
When a mesón is rented as a whole, the right to sublet is implied. Personal grounds to terminate the principal lease do not affect subtenants.

### Art. 16 — Continuation on death/incapacity
The contract continues with the family group living with the tenant in case of death, incapacity, or extended absence. The tenant designates the representative.

### Art. 17 — Rent ceiling for mesón rooms (1973 baseline)
Rent for mesón rooms cannot exceed the last rent paid as of 31 Dec 1973. Detailed declaration procedure follows.

### Art. 18 — Required content of mesón rental contract
Every contract for renting or subleasing a mesón room must be in writing and contain at minimum:
1. Full name, age, profession, domicile of landlord, ID number;
2. Same for tenant;
3. Mesón name (if any) and room number;
4. Rent price;
5. Person authorized to receive rent;
6. Family group representative under art. 16;
7. Place and date of signing.

> **Casa Segura signal:** stronger requirements than art. 4. Missing any of the seven elements = flag.

### Art. 19 — Triplicate
Contract is signed in triplicate: one copy each to landlord, tenant, court (within 5 days).

### Art. 20 — Receipt obligation (mesón)
Landlord must issue receipts for every payment. If not, tenant must not pay directly and must deposit at the court.

### Art. 21 — Penalties for non-compliance
Fine of ¢100 per infraction of arts. 17, 18, 19, 20.

### Art. 22 — Monthly payment terms
Mesón rent is monthly, paid in arrears on the last day of the month.

### Art. 23 — Repeated failure to issue receipts
Four infractions in 12 months → court orders all future payments deposited at court.

## Chapter IV — Termination

### Art. 24 — Causes for termination
The only causes for terminating a lease (other than voluntary expiration) are:

1. Default by tenant (8 days past due);
2. Using the property for purposes other than residential, or for purposes harmful to safety, hygiene, or morality;
3. Storing inflammables/explosives without written landlord consent;
4. Total destruction of the property;
5. Partial destruction making it uninhabitable;
6. Significant damage caused by tenant or his dependents;
7. Tenant making alterations without written landlord consent;
8. Owner intends to build a new construction on the same lot;
9. Owner needs to perform works increasing capacity or essential repairs requiring vacancy;
10. Property threatens ruin (action against tenants of affected portions only);
11. Public-utility taking;
12. Property declared insanitary under the Health Code;
13. Tenant refuses to reimburse excess water consumption (defined per ANDA tariff thresholds);
14. Tenant subleases without written consent;
15. Owner, usufructuary, or holder needs the property for himself, spouse, ancestors, descendants, siblings, first-degree affinity. Need is presumed when the relevant party lives in another's house;
16. Term expiration when owner gave the lease because he was leaving the country/locality;
17. Landlord's title expires for reasons beyond his will (e.g. usufruct expires).

> **Casa Segura signal:** any contract clause listing termination causes outside this list (e.g. "podrá darse por terminado a sola voluntad del arrendador") is unenforceable. Flag **yellow**, cite art. 24.

### Art. 25 — Mesones and apartments — additional cause
In mesones and apartment buildings, the landlord may also seek termination for tenant conduct against public order or internal building order, at judge's prudent judgment.

### Art. 26 — Penalty for fraudulent termination claims
The owner who obtains vacancy under causes 8, 9 (planned construction) or 15 (need for self/family) but fails to act on the stated reason within the deadlines incurs a fine of 10× monthly rent and must indemnify the tenant by 2× monthly rent.

> **Casa Segura signal:** this is a strong tenant protection. Worth surfacing.

### Art. 27 — Death of tenant does not terminate
The contract continues with heirs, or with spouse, life partner, ancestors/descendants who lived there.

### Art. 28 — Sale of property does not terminate the lease
Death or transfer of the property by the landlord does not terminate the lease. Buyers must respect the lease even if not registered. Termination only by causes in art. 24-25.

> **Casa Segura signal:** when verifying a rental contract, if a "new owner" is trying to evict citing the sale alone, that's not a valid cause. Cite art. 28.

### Art. 29 — Cascading effect on subleases
When the principal lease ends, all subleases based on it end — except by non-payment, where any subtenant may pay and become principal tenant. Mesón rule different per art. 14.

## Chapter V — Procedures

### Arts. 30–54
**Almost entirely repealed by D.L. 712 of 2008.** Procedural matters now follow the Código Procesal Civil y Mercantil. Substantive rights in chapters I–IV remain in force.

## Chapter VI — General provisions

### Art. 55 — Establishing business asset value
For purposes of art. 1(b) and art. 24(2), business value is determined from the Matrícula de Comercio file, municipal calification office, or judicial expert.

### Art. 57 — Landlord pays utilities
Landlord pays normal water consumption, sewage, municipal taxes, fees, contributions, and any fiscal charge on the property. Water service cannot be cut to a tenant without first notifying. Mesón water service can never be cut.

> **Casa Segura signal:** any contract clause shifting these to the tenant should be flagged.

### Art. 58 — Distribution of fines
50% of fines go to municipal coffers, 50% to national treasury.

### Art. 59 — 5% surcharge on judicial deposits
When tenants are forced to deposit at court, a 5% surcharge applies to the landlord.

### Art. 60 — Public registry of defaulters
Courts maintain a public registry of tenants condemned to vacate for non-payment. Consultable, not certifiable.

### Art. 60-A — Landlord declaration registry
Courts also keep a registry of landlord declarations (name, address, rent paid 1973).

### Art. 62 — Common law applies for what's not covered
For everything not foreseen in this law, common law applies.

## Cross-references

- For **government-built housing rentals**, the Ley sobre Contratos del IVU (`02-ley-ivu.md`) prevails over this law per art. 13 of that law.
- For **financial leasing** (with purchase option), the Ley de Arrendamiento Financiero (`05-ley-arrendamiento-financiero.md`) applies, not this law.
- Procedural matters: Código Procesal Civil y Mercantil (post-2008).

## Citation format for findings

```json
{
  "law_id": "ley-inquilinato",
  "article": "Art. 4",
  "anchor": "art-4",
  "url": "/laws/01-ley-inquilinato.md#art-4",
  "official_source": "D.O. Nº 35, Tomo 178, 20-02-1958"
}
```
