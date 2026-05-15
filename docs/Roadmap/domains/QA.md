---
tags:
  - casa-segura
  - domain-index
domain_index: qa
---

# QA

BVA suites, smoke tests, evaluation harnesses, regression fixtures, mobile QA, validation gates, and release confidence checks.

## Ownership Notes

QA owners should verify boundary coverage, fixtures, CI integration, and the evidence needed for implementation tickets to move forward. Secondary tags identify the domain experts needed to interpret failures.

## Tickets

```dataview
LIST
FROM "Projects/Casa Segura/Roadmap/tickets"
WHERE domain = "qa" OR contains(secondary_domains, "qa")
SORT file.name ASC
```

```query
tag:#domain/qa path:"Projects/Casa Segura/Roadmap/tickets"
```
