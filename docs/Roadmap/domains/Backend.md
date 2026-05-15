---
tags:
  - casa-segura
  - domain-index
domain_index: backend
---

# Backend

API routes, service orchestration, queues, report generation functions, OCR/classification/rubric service code, and runtime application logic.

## Ownership Notes

Backend owners should watch contracts between **Django/DRF** APIs, **Celery** workers, **Django ORM** models, and downstream report or delivery flows. Stack reference: [ADR-0001 — Django backend stack](../../adr/ADR-0001-django-backend-stack.md). Cross-check secondary tags for security, data, AI/RAG, delivery, and product copy dependencies before implementation.

## Tickets

```dataview
LIST
FROM "Projects/Casa Segura/Roadmap/tickets"
WHERE domain = "backend" OR contains(secondary_domains, "backend")
SORT file.name ASC
```

```query
tag:#domain/backend path:"Projects/Casa Segura/Roadmap/tickets"
```
