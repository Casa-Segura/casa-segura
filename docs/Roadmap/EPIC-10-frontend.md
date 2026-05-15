---
id: EPIC-10
name: Frontend Web App
phase: cross
status: backlog
depends_on:
  - EPIC-00
  - EPIC-08
prd_refs:
  - PRD_GENERAL US-01, US-04, US-05
  - UI-UX
feature: cross-cutting
owner: tbd
tags:
  - casa-segura
  - epic
  - epic-10
  - stub
---

# EPIC-10 — Frontend Web App

> **Stub.** Epic-level only. Tickets fleshed out in second pass. Intentionally thin until BE contracts in [[EPIC-08-multichannel-delivery]] are stable.

## Goal

Public-facing surface for contract submission and report viewing on web. Mobile-first (target: midrange Android over 4G, 360px width). Spanish, "tú" register.

## Definition of done

- [ ] Landing page with one-sentence value proposition and clear CTA
- [ ] Upload page with disclaimer gate, channel selector (email / WhatsApp / link), drag-drop + file picker
- [ ] Loading state with rotating Spanish copy
- [ ] Result page (when channel = link) embeds the HTML report
- [ ] Expired-link friendly page
- [ ] Deployed to Vercel
- [ ] QA passed on a real Android device

## Tickets (titles only — stubs)

- [[CS-290]] — Landing page
- [[CS-291]] — Upload page with disclaimer gate
- [[CS-292]] — Channel selector component
- [[CS-293]] — Loading state with rotating copy
- [[CS-294]] — Result page (HTML report viewer)
- [[CS-295]] — Expired-link page
- [[CS-296]] — Server actions to call BE
- [[CS-297]] — Disclaimer module (single source for "Esto no es asesoría legal")
- [[CS-298]] — Vercel deploy
- [[CS-299]] — Mobile QA pass at 360px width

## Notes

- [[UI-UX]] is the design reference
- Frontend intentionally lags BE — no point styling against unstable schemas
