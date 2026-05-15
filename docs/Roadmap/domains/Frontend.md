---
tags:
  - casa-segura
  - domain-index
domain_index: frontend
---

# Frontend

Next.js pages, UI components, upload flow, report viewer, user-facing project verification screens, mobile behavior, and client-side interaction states.

## Ownership Notes

Frontend owners should coordinate with backend owners on API contracts and with product-content owners on Spanish copy, disclaimers, and report presentation. Tickets tagged with QA often need browser or mobile validation.

## Tickets

```dataview
LIST
FROM "Projects/Casa Segura/Roadmap/tickets"
WHERE domain = "frontend" OR contains(secondary_domains, "frontend")
SORT file.name ASC
```

```query
tag:#domain/frontend path:"Projects/Casa Segura/Roadmap/tickets"
```
