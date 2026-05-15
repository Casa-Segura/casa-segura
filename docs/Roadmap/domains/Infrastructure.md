---
tags:
  - casa-segura
  - domain-index
domain_index: infra
---

# Infrastructure

CI, deployments, environment variables, database provisioning, migrations, schedulers, runtime configuration, hosting, DNS, and platform-level observability wiring.

## Ownership Notes

Infrastructure owners should review environment contracts, deployment sequencing, feature flags, health checks, and operational runbooks. Security-sensitive tickets should be reviewed with the security-privacy lane.

## Tickets

```dataview
LIST
FROM "Projects/Casa Segura/Roadmap/tickets"
WHERE domain = "infra" OR contains(secondary_domains, "infra")
SORT file.name ASC
```

```query
tag:#domain/infra path:"Projects/Casa Segura/Roadmap/tickets"
```
