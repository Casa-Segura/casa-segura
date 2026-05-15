---
tags:
  - casa-segura
  - domain-index
domain_index: delivery
---

# Delivery

Email, WhatsApp/Zavu, public links, resend behavior, delivery queues, provider transports, message lifecycle, and channel-specific delivery constraints.

## Ownership Notes

Delivery owners should coordinate with backend on job orchestration, security-privacy on target handling and link TTLs, and product-content on channel copy. Provider integration tickets may need infra review for secrets and webhooks.

## Tickets

```dataview
LIST
FROM "Projects/Casa Segura/Roadmap/tickets"
WHERE domain = "delivery" OR contains(secondary_domains, "delivery")
SORT file.name ASC
```

```query
tag:#domain/delivery path:"Projects/Casa Segura/Roadmap/tickets"
```
