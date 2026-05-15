---
law_id: ley-urbanismo-construccion
title: Ley de Urbanismo y Construcción
short_title: Urbanismo y Construcción
decreto: D.L. 232
fecha_emision: 1951-06-04
diario_oficial: "Nº 107, Tomo 151, 11-06-1951"
reformas_count: 5
reformas:
  - "D.L. 2190, 31-08-1956 (D.O. 170, T.172, 12-09-1956)"
  - "D.L. 142, 10-10-1972 (D.O. 195, T.237, 20-10-1972)"
  - "D.L. 708, 13-02-1991 (D.O. 36, T.310, 21-02-1991)"
  - "D.L. 294, 03-03-2016 (D.O. 60, T.411, 04-04-2016)"
  - "D.L. 98, 13-07-2021 (D.O. 138, T.432, 20-07-2021)"
ultima_reforma: "D.L. 98, 13-07-2021"
disposicion_relacionada: "Ley Especial para la Reestructuración Municipal — D.L. 762, 13-06-2023"
reglamento: "D.E. 69, 14-09-1973 (D.O. 179, T.240, 26-09-1973)"
estado: vigente
materia: Urbanismo y construcción — autorizaciones administrativas
source_url: https://www.asamblea.gob.sv/sites/default/files/documents/decretos/CDCC9678-C96C-4E1F-9F32-A832AF6ED4A7.pdf
last_verified: 2026-05-09
relevance_to_casa_segura: critical
covers:
  - approval authority for urbanizations, parcelaciones, and construction (Ministerio de Vivienda + municipalities)
  - technical requirements for project approval (parks, schools, services, materials)
  - obligation to use registered architects/engineers
  - notice obligation when starting work
  - validity period of approvals (1 year)
  - municipal enforcement powers (suspension, demolition, fines)
  - reconsideration recourse before Ministerio de Vivienda
---

# Ley de Urbanismo y Construcción

## Plain-language summary

This is the **foundational law for any urbanization, parcelación, or construction project in El Salvador**. Originally from 1951, with five reforms (most recent in 2021), it establishes that:

1. The **Ministerio de Vivienda** sets national policy and approves projects when municipalities don't have their own development plans.
2. Every urbanization or construction project must be **approved before execution** — by the Ministerio de Vivienda, the relevant municipality, or both.
3. Projects must be **designed and built by registered architects or civil engineers** inscribed in the Registro Nacional de Arquitectos, Ingenieros, Proyectistas y Constructores.
4. Approvals **last only one year** — old approvals don't carry over.
5. Failure to comply triggers **municipal suspension, forced demolition, and fines** of 25% (Art. 5) or 10% (Art. 9) of the land value.

For Casa Segura, this is the law that *the permit number on the billboard refers to*. Every "OPAMSS-2024-XXXX" or "Aprobación Vivienda XXXX" on a project sign is an instance of an approval under this law (or under the equivalent municipal authority operating under it).

## Application to Casa Segura

This is **the most important Flow 1 law in the entire corpus**. It is the legal grounding for every permit-related check the project legitimacy flow performs.

Findings the verdict engine should ground here:

- **`permit_required`** (project advertising sales without any visible permit) → arts. 1, 2, 5
- **`permit_authority_unclear`** (project shows a "permit" from an unrecognized authority) → art. 1
- **`permit_format_invalid`** (Casa Segura's regex check fails) → art. 1, art. 2 (specific format depends on whether issued by Ministerio de Vivienda or municipality)
- **`permit_expired`** (permit older than 1 year with no construction started) → art. 6
- **`permit_pre_1951`** (impossibly old or pre-law) → art. 7
- **`developer_not_licensed_architect`** (project not designed/built by registered professional) → arts. 4, 8
- **`construction_not_supervised_by_registered_professional`** → art. 8
- **`industrial_construction_no_safety_clearance`** (factory/workshop building without Previsión Social approval) → art. 8 final paragraph
- **`urbanization_without_park_reservation`** (advertised parcelación claims more lots than 90% of useful area would allow) → art. 2(e)
- **`urbanization_without_school_reservation`** → art. 2(g)
- **`urbanization_without_water_drainage_resolution`** → art. 2(h)
- **`developer_did_not_notify_start_of_works`** (no aviso submitted within 8 days) → art. 5
- **`works_inconsistent_with_approved_plans`** (project deviates from the plans approved) → art. 5
- **`accessibility_design_missing`** (no universal-design accessibility per Convention on the Rights of Persons with Disabilities) → art. 1 (added in 2016 reform)

## Key articles

### Art. 1 — Authority and scope (CRITICAL)
The **Ministerio de Vivienda** formulates and directs the national housing and urban-development policy. It also drafts the national and regional plans and the general dispositions that all urbanizations, parcelaciones, and constructions must follow throughout the country.

Local urban and rural development plans correspond to the respective **municipality**, framed within national/regional plans. **When a municipality has no local plan, the Ministerio's general dispositions apply.**

When municipalities lack their own development plans and ordinances, **any private party, official entity, or autonomous body must request approval from the Ministerio de Vivienda before any other office** to execute any project covered by this article. **For projects of general interest contracted or executed by State institutions in the housing system, the Ministerio de Vivienda issues the approval.**

The Ministerio and municipalities, when drafting/approving/executing urban/rural development plans, must **verify strict compliance with universal accessibility design** under Art. 9 of the Convention on the Rights of Persons with Disabilities (added in 2016 reform).

When any urbanization, parcelación, or construction project of general benefit is required by State housing-system institutions, the Ministro de Vivienda may issue a **declaration of social interest** for the benefit of Salvadoran families to be served (added in 2021).

> **Casa Segura signal:** if a project's billboard shows no clear approval authority — neither a municipal permit nor a Ministerio de Vivienda authorization — flag as **red**. No project can legally advance without it. Cite art. 1.

### Art. 2 — Approval requirements (CRITICAL)
For the Ministerio de Vivienda to grant approval, the interested party must comply with:

(a) **Topographic survey** with level curves at maximum 1-meter equidistance;
(b) **Class of urbanization** with respective parcelamiento;
(c) **Streets project** (primary and secondary);
(d) **Resolution of the connection problem** with the rest of the city and surroundings;
(e) **Reserve land for gardens and public parks** equal to **10% minimum of the useful area** when located inside cities; or **12.5 m² minimum per lot** when located outside existing populated centers. The location must be adequate for these purposes.
(f) **Reserve sufficient land for public services** installation, with specifications and location at the Ministerio de Vivienda's judgment;
(g) **Reserve land for schools** equal to **8 m² per lot** to be parceled or urbanized. Regulation establishes exceptions;
(h) **Feasibility resolution** from the corresponding agency for: potable water, complete drainage of rainwater and sewage, electric lighting, telephone service — indicating connections with existing public services;
(i) **Specify materials class** to be used for water, sewage, curbs, gutters, and street surface treatment;
(j) **Plans at minimum scales**: topographic and planimetric ≥ 1:500; "perfiles" plans ≥ 1:50 vertical and 1:500 horizontal; large complexes additionally need a 1:1000 plan.

For lands referenced in (e) and (g), urbanizers are obligated to perform the works — but may **discharge those obligations by irrevocably donating the land to the municipality** if works aren't started and finished within the regulation's timeframe.

The requirements in (e), (f), (g), and (h) are exigible per regulation when the area's extent and projected population warrant.

> **Casa Segura signal:** for a project advertising N lots, you can sanity-check whether the parcelación math leaves enough land for the 10% park reservation. If a project on 10,000 m² advertises lots totaling more than 9,000 m² of saleable area, something is missing. Worth flagging.

### Art. 3 — Materials approval
Materials used in urbanization works require approval from the **Ministerio de Obras Públicas materials-testing laboratory**.

### Art. 4 — Local-only urbanizations rejected; professional requirement (CRITICAL)
**Urbanizations that consider only the local study** and do not include the surface as integrated part of the metropolitan zone **will not be approved**. Same for urbanizations whose project and construction **are not executed by civil engineers or architects legally authorized** to practice in the country.

> **Casa Segura signal:** if a billboard or advertisement does not name the responsible architect or engineer (or names someone not in the Registro Nacional), flag. Cite art. 4. Combined with art. 8, this is one of the strongest verifiable signals.

### Art. 5 — Notice obligation and penalties (CRITICAL)
Persons or institutions that have obtained approval under art. 1 are obligated to give **written notice within 8 working days** to the Ministerio de Vivienda or the relevant municipality, for technical supervision, of the dates work will begin.

Failure to notify: **fine of 25% of the land's value** (including construction value if applicable), exigible by municipalities per laws and regulations.

If works are not being done according to approved plans and specifications, **suspension and correction may be ordered**, and if already done, **demolition at the infractor's cost**.

> **Casa Segura signal:** the 25% fine is a deterrent that exists on paper but is unevenly enforced. The product can flag the obligation, but the user should know enforcement may require pushing the municipality.

### Art. 6 — One-year validity (CRITICAL)
Authorization to execute a parcelación or urbanization based on approved projects has a **validity of one year** from the day after the approval.

If works haven't started in that year, **a new approval of the corresponding plans must be obtained** from the Ministerio de Vivienda or the municipality.

> **Casa Segura signal:** if the permit number on the billboard suggests it was issued more than a year ago and there's no evidence of continuous work, flag as **yellow** with art. 6 cite. The buyer should ask for the renewal.

### Art. 7 — Pre-1951 approvals are caducated
Approvals granted **before this law's effective date** (June 1951) for urbanizations not yet started **are void and have no effect**.

> **Casa Segura signal:** if a billboard cites a pre-1951 approval as legitimacy, that's a red flag. Almost certainly a fabrication or a deeply outdated document.

### Art. 8 — Construction must be by registered professionals (CRITICAL)
Every project of building construction, **whether by private parties or official, edilician, or autonomous entities**, must be:

- **Drafted by a legally authorized architect or civil engineer**, registered in the **Registro Nacional de Arquitectos, Ingenieros, Proyectistas y Constructores**;
- **Signed and sealed** by them on the plans submitted;
- **Executed and supervised** by a legally authorized and registered architect or civil engineer.

**Exceptions** (no professional required):
- Bahareque, adobe constructions
- Brick and mixed-system constructions of single floor with wood-structure roof
- Wooden constructions of single floor

These exceptions can be designed and built by **proyectistas y constructores of recognized capacity**, also inscribed in the Registro, following Ministerio de Vivienda norms.

In all cases, when constructing factories, workshops, or other industrial/commercial installations, **approval will not be granted without prior favorable opinion from the Departamento Nacional de Previsión Social** on safety and hygiene of work.

> **Casa Segura signal:** verifying the responsible architect/engineer is one of the most concrete checks the product can do. The Registro Nacional should be queryable. Cite art. 8.

### Art. 9 — Municipal enforcement and demolition power
**Municipal mayoralties and Ministerio de Obras Públicas authorities are obligated to enforce this law**. They must, as appropriate, **suspend or demolish** works being done in violation of laws and regulations on the matter, **at the infractor's cost** — without prejudice to municipal mayoralties imposing **fines equal to 10% of the land's value** for violations.

When the Ministerio de Vivienda or municipalities request the help of security forces to enforce resolutions or prevent infractions, those forces must provide it immediately. Other governmental, edilician, or autonomous institutions involved in urban development must also collaborate.

> **Casa Segura signal:** these enforcement powers exist. The buyer should know the municipality has authority to demolish unauthorized construction at the developer's cost — a concrete protection if the developer is operating without permits.

### Art. 10 — Reconsideration recourse
If approval of an urbanization, parcelación, or construction project is denied, interested parties may file a **reconsideration recourse** within **10 days** of notification, before the **Ministerio de Vivienda**, which must resolve and notify within **one month** (added in 2021 reform).

### Art. 10 Bis — Regulation
The President of the Republic issues regulations to facilitate this law's application (added in 1991 reform). The current implementing regulation is D.E. 69 of 14 September 1973.

### Art. 11 — Repeal clause
All dispositions opposed to this law are repealed.

### Art. 12 — Effective date
The decree entered into force 8 days after publication in the Diario Oficial (June 1951).

## Reforms timeline

| # | Decree | Date | What changed |
|---|---|---|---|
| 1 | D.L. 2190 | 31-08-1956 | Updated Art. 8 (professional requirements) |
| 2 | D.L. 142 | 10-10-1972 | Updated Art. 9 (enforcement) |
| 3 | D.L. 708 | 13-02-1991 | Major reform: most articles modernized; added Art. 10 Bis (regulations) |
| 4 | D.L. 294 | 03-03-2016 | Added universal accessibility requirement to Art. 1 |
| 5 | D.L. 98 | 13-07-2021 | Updated Art. 1 with social-interest declaration; updated Art. 10 (reconsideration) |

The 1991 reform is the most important — it modernized most of the technical requirements and gave the Ministerio de Vivienda the central role it has today.

## Practical fraud patterns to watch

| Pattern | Article |
|---|---|
| Billboard shows no permit number at all | art. 1, 2 |
| Permit number doesn't match Ministerio de Vivienda or municipal format | art. 1 |
| Project advertises construction but no architect/engineer name visible | art. 4, 8 |
| Architect/engineer named is not in the Registro Nacional | art. 8 |
| Permit dates suggest >1 year old with no work history | art. 6 |
| Parcelación advertises lot count incompatible with the 10% park reservation | art. 2(e) |
| Industrial/commercial project without Previsión Social clearance reference | art. 8 final |
| Project deviates visibly from advertised plans | art. 5 |
| Pre-1951 approval cited | art. 7 |

## What the permit number on a billboard actually is

Permit numbers Casa Segura's vision model extracts from billboards are typically one of:

- **OPAMSS-YYYY-XXXX** — issued by the Oficina de Planificación del Área Metropolitana de San Salvador (the metropolitan planning office), under municipal authority for the AMSS metropolitan zone, operating under this law's framework.
- **Municipal permits** — variable formats by municipality (e.g. Santa Tecla, Antiguo Cuscatlán) for projects in their jurisdictions.
- **Ministerio de Vivienda approvals** — for projects in municipalities without their own plans, or for projects of general interest.

Casa Segura's permit-format regex check is grounded in this article structure. For each known authority, the product can validate format and (when the registry is exposed) cross-reference the issuance.

## Cross-references

- **Lotificaciones**: when filled in, the Ley Especial para la Regularización de Lotificaciones y Parcelaciones para Uso Habitacional (currently the still-pendiente file `06-pendiente-...`) governs the regularization regime for parcelaciones that didn't comply with this law's requirements before September 2012. Most lotificación-related fraud sits at the intersection of this law (was a permit ever issued?) and that one (is the project being regularized?).
- **FSV**: government-financed projects also pass through this law's permit gates.
- **IVU contracts**: see `02-ley-ivu.md`.
- **Public Procurement (LCP)**: when the project is a State-financed urbanization, the procurement process is governed by `04-ley-compras-publicas.md`, but the technical approval still falls under this law.
- **Implementing regulation**: D.E. 69 of 1973 (Reglamento a la Ley de Urbanismo y Construcción) — defines the technical thresholds, exceptions, and procedures referenced abstractly in this law.

## Citation format for findings

```json
{
  "law_id": "ley-urbanismo-construccion",
  "article": "Art. 8",
  "anchor": "art-8",
  "url": "/laws/07-ley-urbanismo-construccion.md#art-8",
  "official_source": "D.L. 232 de 04-06-1951, D.O. Nº 107, T.151, 11-06-1951"
}
```
