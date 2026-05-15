---
tags:
  - casa-segura
  - domain-index
domain_index: product-content
---

# Product Content

Disclaimer copy, report copy, legal-warning text, suggested actions, Spanish tone rules, disclosure text, and user-facing explanation quality.

## Ownership Notes

Product-content owners should review clarity, tone, legal sensitivity, and consistency across report, delivery, frontend, and disclosure surfaces. Secondary tags show where engineering support is required.

## Tickets

```dataview
LIST
FROM "Projects/Casa Segura/Roadmap/tickets"
WHERE domain = "product-content" OR contains(secondary_domains, "product-content")
SORT file.name ASC
```

```query
tag:#domain/product-content path:"Projects/Casa Segura/Roadmap/tickets"
```
