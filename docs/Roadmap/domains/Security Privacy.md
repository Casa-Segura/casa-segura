---
tags:
  - casa-segura
  - domain-index
domain_index: security-privacy
---

# Security Privacy

Retention, anonymization, log scrubbing, TLS, secrets, disclosure flows, no-PII invariants, provider target protection, and privacy-sensitive operational controls.

## Ownership Notes

Security and privacy owners should treat primary tickets as policy-critical and review secondary tickets where privacy or compliance is an invariant rather than the main implementation surface.

## Tickets

```dataview
LIST
FROM "Projects/Casa Segura/Roadmap/tickets"
WHERE domain = "security-privacy" OR contains(secondary_domains, "security-privacy")
SORT file.name ASC
```

```query
tag:#domain/security-privacy path:"Projects/Casa Segura/Roadmap/tickets"
```
