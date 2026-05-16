# CS-299 — Mobile QA checklist (physical Android)

Execute on a **real midrange Android** device using **Staging** or a **Vercel Preview URL** wired to staging backend. Follow [`docs/Roadmap/tickets/CS-299.md`](../../docs/Roadmap/tickets/CS-299.md) for full AC.

**Evidence:** Screenshots/evidence OK; **never** attach real contracts or OCR text — use fixtures or redacted stubs.

Record date, device model, Chrome version, reviewer name, deployment URL below.

---

## Preconditions

| # | Gate |
|---|------|
| 1 | Backend reachable from phone (same network/VPN acceptable) |
| 2 | CASASEGURA env set on Preview for staging API |
| 3 | Zoom / text size: capture default + note if scaled |

## Evidence header (fill before session)

| Field | Value |
|-------|-------|
| Date | |
| Deploy URL | |
| Device | e.g. ~360 CSS px wide |
| Network | Wi‑Fi vs throttled **4G** (run one happy path with 4G profile) |

## Flows — tick when passed

### A. Landing (CS-290)

- [ ] **360 px** viewport: no unintended horizontal scroll on primary column
- [ ] Hero CTA **≥44px** tap height and visible focus/active state

### B. Upload + disclaimer + channels (CS-291 / CS-292)

- [ ] Disclaimer gate clears before submission
- [ ] Email / WhatsApp / link pathways: labels readable; validation errors near fields
- [ ] Submit starts loading state

### C. Loading (CS-293)

- [ ] Reassurance copy rotates; spinner visible; UI not frozen perceptibly on 4G

### D. Report link viewer (CS-294)

- [ ] HTML report renders; inner tables may horizontal-scroll per ticket
- [ ] Disclaimer footer intact

### E. Expired link (CS-295)

Force via backend fixture / known-expired stub / dev toggle so `/r/<id>` or BE returns **404/410**:

- [ ] Land on **`/enlace-expirado`**: PRD headline + privacy sentence + CTA nuevo análisis
- [ ] **No iframe** mounts for expired case

### F. Accessibility — TalkBack (minimum)

- [ ] Disclaimer gate: announced with meaningful labels once
- [ ] One invalid field: error surfaced and reachable

---

## Regression log

List **P0/P1** defects with filed ticket IDs before marking CS-299 `done`:

| Severity | Brief | Ticket |
|----------|-------|--------|
| | | |

---

Sign-off line (typed name + OK):
