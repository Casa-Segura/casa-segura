---
tags:
  - casa-segura
  - domain-index
domain_index: data
---

# Data

Postgres schema, pgvector storage, catalog entities, benchmarks, corpus/rubric/database seeds, project aggregation, canonical identifiers, and persistence-facing model contracts.

## Ownership Notes

Data owners should check migrations, backfills, seed reproducibility, model shape changes, and downstream consumers. Tickets with AI/RAG or backend secondary domains often need schema-contract review before implementation starts.

## Tickets

```dataview
LIST
FROM "Projects/Casa Segura/Roadmap/tickets"
WHERE domain = "data" OR contains(secondary_domains, "data")
SORT file.name ASC
```

```query
tag:#domain/data path:"Projects/Casa Segura/Roadmap/tickets"
```
