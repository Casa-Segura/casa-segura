---
tags:
  - casa-segura
  - domain-index
domain_index: misc
---

# Misc

True cross-cutting or administrative items that do not fit the other domain lanes. This domain should stay intentionally small.

## Ownership Notes

Misc tickets should be periodically reviewed and reclassified if a clearer owner emerges. Prefer a specific domain whenever a ticket has an obvious implementation or review lane.

## Tickets

```dataview
LIST
FROM "Projects/Casa Segura/Roadmap/tickets"
WHERE domain = "misc" OR contains(secondary_domains, "misc")
SORT file.name ASC
```

```query
tag:#domain/misc path:"Projects/Casa Segura/Roadmap/tickets"
```
