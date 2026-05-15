---
law_id: ley-fsv
title: Ley del Fondo Social para la Vivienda
short_title: FSV
decreto: D.L. 328
fecha_emision: 1973-05-17
diario_oficial: "Nº 104, Tomo 239, 06-06-1973"
reformas_count: 12
ultima_reforma: "D.L. 46, 03-06-2021 (D.O. 107, T.431, 05-06-2021)"
estado: vigente
materia: Vivienda — seguridad social
source_url: https://www.jurisprudencia.gob.sv/DocumentosBoveda/D/2/1970-1979/1973/06/889B6.PDF
last_verified: 2026-05-09
relevance_to_casa_segura: high
covers:
  - creation and structure of the Fondo Social para la Vivienda (FSV)
  - mandatory employer/worker contributions
  - FSV-financed credit operations for worker housing
  - special procedural and registry rules for FSV contracts
  - tax exemptions for FSV-financed purchases
---

# Ley del Fondo Social para la Vivienda

## Plain-language summary

Creates the **Fondo Social para la Vivienda (FSV)** as an autonomous public-law credit institution whose purpose is to help workers obtain comfortable, hygienic, and safe housing. It's funded by mandatory employer (5%) and worker (0.5%) contributions on payroll, plus state subsidies and operations.

The FSV does not build housing directly in the typical case — it **finances** purchases, construction, repair, or refinancing for worker housing, either directly or through intermediary institutions calified by the Ministry of Housing. It also has special powers: certifications by its Director Ejecutivo are executive titles for collection, its credits have first-class privilege, and FSV-financed sales below a threshold are exempt from real estate transfer tax.

## Application to Casa Segura

This law matters for projects that:
- Claim to be FSV-financed or FSV-affiliated
- Offer "FSV-elegible" housing as a sales pitch
- Use the FSV as an intermediary or guarantor

Key fraud-detection angles:

1. **Phantom FSV affiliation.** A developer claims FSV financing they don't actually have. Verifiable: FSV publishes its supported projects.
2. **Tax exemption fraud.** Someone claims their sale is FSV-financed (and thus exempt from transfer tax under art. 68) when it isn't.
3. **Worker contribution fraud.** An employer charges workers but doesn't actually deposit the contributions to FSV.
4. **Mortgage anotación preventiva manipulation.** The FSV's anotación preventiva (art. 55) creates retroactive priority — fraud schemes try to slip transactions in between adjudication and inscription.

Findings the verdict engine should ground here:

- **`fsv_affiliation_claim_unverified`** → arts. 5, 7
- **`fsv_intermediary_required_for_third_party`** → art. 7 final paragraph
- **`fsv_tax_exemption_misapplied`** → art. 68
- **`fsv_first_class_privilege_misrepresented`** → art. 71(b)
- **`fsv_anotacion_preventiva_required`** → arts. 55–57

## Chapter I — Creation, object, nature

### Art. 1 — Creation
The FSV is created as a social-security development program.

### Art. 2 — Legal personality, domicile
FSV is an **autonomous credit institution of public law** with juridical personality, no limitations beyond this law, headquartered in San Salvador, with branches across the country.

### Art. 3 — Object
Contribute to solving workers' housing problems by providing means to acquire comfortable, hygienic, and safe homes.

### Art. 4 — Scope
Applies to all employers and workers regardless of relationship type or remuneration form. Regulations specify the time and form of incorporation. Coverage may extend to workers without an employer.

### Art. 5 — Government relationship
The Fund relates to government via the **Ministerio de Vivienda**.

## Chapter II — Resources and operations

### Art. 6 — Resources
- (a) Initial state subsidy of ¢25,000,000 paid in 5 annual installments;
- (b) Contributions of **5% (employer) and 0.5% (worker)** on payroll, within limits set by regulation;
- (c) Additional state subsidies;
- (d) Net profits from operations;
- (e) Other income.

### Art. 7 — Use of resources (CRITICAL)
The FSV's resources are destined to:
- (a) Credits to **workers** for: (I) housing acquisition; (II) construction, repair, expansion, improvement; (III) refinancing earlier debts of these types;
- (b) Credits to **employers** to build housing for workers;
- (c) Credits to **cooperatives** for furniture/household goods financing;
- (d) Acquisition of movable/immovable goods needed for FSV's purposes;
- (e) Financing materials-of-construction enterprises;
- (f) Construction or financing of housing complexes;
- (g) Operating expenses.

Credits are granted **directly or through intermediary institutions** calified by the Ministry of Housing.

> **Casa Segura signal:** if a developer claims FSV financing but is neither an FSV-calificada institution nor a worker/employer beneficiary type listed in (a)–(c), that claim is suspect. Cite art. 7.

### Art. 8 — Operations the FSV may conduct
- (a) Buy, hold, and sell credit titles and easily realizable securities;
- (b) Buy and sell shares, easily realizable securities, real estate, and other compatible assets;
- (c) Issue and place bonds and securities per law;
- (d) Trade for third parties securities issued by the State, autonomous bodies, or construction-sector enterprises;
- (e) Grant guarantees;
- (f) Discount documents and obtain financing from BCR and other institutions;
- (g) Obtain internal/external financing;
- (h) Administer (non-profit) funds the State or third parties give it to build replacement housing for tugurios (slums);
- (i) Other compatible operations.

### Art. 8-A — Transfer of credit titles
Credit titles are transferable by delivery + written endorsement signed before notary, registered in the Registro de Hipotecas in margin of the corresponding hipotecaria inscription.

## Chapter III — Organization and administration

### Arts. 9–40 (summary)
**Organs:** Asamblea de Gobernadores, Junta Directiva, Dirección Ejecutiva, Gerencia, Consejo de Vigilancia.

**Asamblea de Gobernadores** (art. 10): Highest authority. Composed of titulares of Vivienda, Obras Públicas/Transporte, Trabajo, Hacienda, Economía, plus 2 employer-sector and 2 labor-sector governors (last reform 2021).

**Junta Directiva** (arts. 17–26): 5 members — 1 nominated by President of the Republic (who is President of Junta and Director Ejecutivo), 4 nominated by the Asamblea (1 employer, 1 labor, 2 public-sector).

**Director Ejecutivo** (arts. 27–30): Executes Junta resolutions, has legal representation, signs operational contracts.

**Consejo de Vigilancia** (arts. 34–40): 4 members — 1 employer, 1 labor, 2 from Executive (Vivienda, Trabajo). Supervises correct application of the law, has full access to documentation.

### Art. 16-A — Removal grounds (added 2021)
Governors may only be removed by their nominating authority, with stated cause, for: (a) violation of nomination requirements; (b) legal incompliance in functions; (c) condemnation for intentional crime; (d) loss of citizenship rights; (e) conduct against morals; (f) conflict of interest; (g) undue influence; (h) loss of sector representativity.

## Chapter IV — Registry, affiliation, contributions

### Art. 41 — Registry obligation
The FSV maintains a registry of contributing employers and workers. The employer must register itself and its workers per regulation.

### Art. 42 — Prohibition on deduction
Employer contributions cannot be deducted from worker wages. Violation: fine per art. 54 and restitution.

> **Casa Segura signal:** if a worker claims their employer is deducting the *employer* portion (5%) from their salary, that's a clear violation. Cite art. 42.

### Art. 43 — Retention and remittance
The employer retains the worker contribution and any FSV credit installment from wages and is **personally responsible** for delivery to FSV. Late payments incur 1% surcharge per month.

### Art. 44 — Inspection
FSV may conduct inspections at workplaces directly or via the Ministry of Labor. Inspector reports and minutes are presumed accurate until proven otherwise.

## Chapter V — Deposits and refunds

### Art. 45 — Deposits and tax exemption
Worker and employer contributions are received by the FSV as **deposits in favor of the worker**, exempt from all taxes.

### Art. 46 — Refunds
Refund procedures per regulation, after the actuarial wait period or in cases of jubilation, death, permanent total incapacity.

### Art. 47 — Right to refund
Workers in jubilation or permanent total incapacity have the right to refund. On death, refund goes to beneficiaries or heirs.

### Art. 48 — Compensation
On any refund, prior debt to FSV is settled first (even if not yet due) against the deposit.

## Chapter VI — Conflicts and sanctions

### Art. 49 — Competence
Conflicts between cotizantes/FSV/beneficiaries are heard by the Director Ejecutivo, who appoints a delegate that acts as arbitrador.

### Art. 50 — Recurso de revisión
Within 3 days of notification, parties may request review.

### Art. 51 — Review commission
The Junta Directiva names a 3-member commission of its members to hear reviews.

### Art. 52 — Resolution period
The commission has 15 days to resolve. Its decision is final.

### Art. 53 — Other actions preserved
Notwithstanding the above, parties retain the right to ordinary judicial action.

### Art. 54 — Sanctions
Sanctions are **fines** of ¢50–5,000, set by the Director Ejecutivo per gravity and economic capacity.

## Chapter VII — Credit formalities (added by reform 3)

### Art. 55 — Anotación preventiva (CRITICAL)
Once the Junta authorizes a hipoteca-backed credit, an extract certification is issued. It contains: act date, name of beneficiary, credit amount, term, and references to current Registro de la Propiedad inscriptions of the offered properties — without need for property descriptions.

The certification, signed by the Director Ejecutivo or Gerente, is **anotada preventivamente** in the Registro de la Propiedad Raíz e Hipotecas. **No fee charged for the anotación.**

The hipoteca's effects, once the contract is registered, **retroactively go to the date of the anotación preventiva**.

> **Casa Segura signal:** this retroactive priority is critical. If a sale happens between FSV anotación preventiva and final inscription, the buyer's title is junior to FSV's lien. Verifying the Registro for FSV anotaciones is a key check. Cite art. 55.

### Art. 56 — Subsequent contract
After anotación, the contract is signed in legal form unless an unfavorable circumstance leads the Junta to revoke.

### Art. 57 — Cessation of anotación
The anotación ceases by:
1. Final inscription of the credit;
2. Written notice from FSV to the Registry to cancel;
3. Lapse of 90 days from the presentation per art. 55.

### Art. 58 — Encumbrance restrictions
Without FSV consent, no escritura selling, alienating, or encumbering any FSV-mortgaged property may be inscribed.

### Art. 59 — Inembargabilidad
Once FSV grants the loan, the encumbered goods are not embargable for personal credits prior or posterior to the constitution of the encumbrance. The protection runs from the anotación preventiva date for hipoteca, from inscription date for prenda.

### Art. 60 — Termination of inferior rights on embargo
If FSV embargo follows debt default, embargoes terminate any post-hipoteca arrendamiento, usufructo, anticresis, or other right unless granted with FSV consent.

### Art. 61 — Caducidad (acceleration)
The agreed term lapses (i.e. the credit becomes immediately due) when:
- (a) Debtor doesn't notify within a month deteriorations affecting property value, possession, or title;
- (b) Debtor concealed any cause of resolution, rescission, or hidden encumbrance;
- (c) Debtor misses any installment;
- (d) Debtor alienates the encumbered goods or constitutes hipotecas, usufructos, etc., without FSV consent (refaccionario credit excepted);
- (e) Debtor defaults on any other FSV debt;
- (f) Goods deteriorate so they no longer cover the guarantee (FSV must accept a sufficient alternative guarantee);
- (g) Funds are diverted to purposes other than agreed;
- (h) Other cases per applicable laws or contracts.

## Chapter VIII — General dispositions

### Art. 62 — Prescription of inactive balances
Inactive balances at FSV's expense prescribe per art. 204 of Ley de Instituciones de Crédito y Organizaciones Auxiliares — but on completion, the balance reverts to FSV (not the State).

### Art. 65 — Inapplicable laws
The Ley de Tesorería, Ley Orgánica de Presupuestos, Ley de Suministros, and other dispositions on public funds and personnel **do not apply** to FSV's gestion. This law prevails over any other.

### Art. 66 — Court of Accounts oversight
The Corte de Cuentas oversees budget execution via a delegado-auditor. The audit is *a posteriori*, focused on legality.

### Art. 68 — Tax exemption on FSV-financed compraventas (CRITICAL)
Real estate compraventas **financed by the FSV** and FSV-granted loans, **when the operation does not exceed ¢100,000**, do not generate any fiscal tax. Public deeds for these acts are issued on plain paper, and registry inscription is exempt from any tax/fee.

The 1976 authentic interpretation (D.L. 180) clarifies: this exemption covers:
- Sales between private parties and contributing workers, FSV-financed;
- Sales between private parties and FSV destined for adjudication to contributing workers;
- Sales between private parties and FSV destined for FSV construction for adjudication to contributing workers.

> **Casa Segura signal:** a fraudulent seller may claim "FSV exemption" applies to bypass real-estate transfer tax (3% on transactions over $28,571.43 per the Ley del Impuesto sobre Transferencia de Bienes Raíces). Verify the FSV financing chain. Cite art. 68.

### Art. 69 — General tax exemption for FSV
FSV is exempt from all fiscal taxes when it owes them, and from succession/donation taxes on receipts to FSV.

### Art. 70 — Bond exemption
FSV-issued bonds and their interest are exempt from all fiscal taxes including renta, vialidad, papel sellado, sucesiones y donaciones.

### Art. 71 — Special executive procedures (CRITICAL)
FSV (or its intermediaries) executive trials follow common law with these modifications:
- (a) Director Ejecutivo's certifications of amounts owed are **executive titles**;
- (b) FSV credits are **first-class** with absolute preference except for worker wage/social claims of the debtor;
- (c) Notifications can be made directly to the debtor or to a power-of-attorney that the debtor must constitute in the foundational deed;
- (d) Probative period: 3 days. Only allowed exceptions: actual payment, error in liquidation;
- (e) **No appeal** of the embargo decree, sale-by-auction sentence, or other rulings;
- (f) Creditor (FSV) is depositor of embargoed goods without bond;
- (g) Tercerías only admissible if based on a title prior to the FSV mortgage;
- (h) No other suit may be cumulated to the execution.

After full payment from auction, other creditors are notified to pursue any surplus.

### Art. 72 — Authentic value of FSV certifications
Transcripciones, extractos, certifications from FSV books and registries, signed by Director Ejecutivo or Gerente with the FSV seal, have the value of authentic documents.

## Practical fraud patterns to watch

| Pattern | Article |
|---|---|
| Developer claims FSV financing without being a calificada institution or having a worker/employer beneficiary | art. 7 |
| Sale claims FSV tax exemption with no verifiable FSV credit chain | art. 68 |
| Property has FSV anotación preventiva but seller doesn't disclose | art. 55, 58 |
| Seller claims "FSV mortgage will be cancelled at signing" without FSV written consent | art. 58, 61(d) |
| Employer charges worker the 5% employer contribution | art. 42 |
| Sale price within FSV-eligible range but seller refuses FSV process | hint to fraud |

## Cross-references

- **Real estate transfer tax**: Ley del Impuesto sobre Transferencia de Bienes Raíces (3% over $28,571.43 unless FSV-exempt).
- **Government-built housing**: Ley sobre Contratos del IVU (`02-ley-ivu.md`) for IVU-specific contracts.
- **Public banking system**: Ley de Bancos and SSF supervision.
- **Mortgage execution**: common procedural law + this special regime.

## Citation format for findings

```json
{
  "law_id": "ley-fsv",
  "article": "Art. 55",
  "anchor": "art-55",
  "url": "/laws/03-ley-fsv.md#art-55",
  "official_source": "D.L. 328 de 17-05-1973, D.O. Nº 104, T.239, 06-06-1973"
}
```
