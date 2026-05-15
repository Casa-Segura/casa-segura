---
tags:
  - casa-segura
  - domain-index
domain_index: ai-rag
---

# AI RAG

OCR prompts, classification prompts, embeddings, RAG retrieval, legal corpus processing, rubric evaluator prompts, confidence handling, citation grounding, and eval sets.

## Ownership Notes

AI/RAG owners should validate prompt contracts, retrieval thresholds, legal grounding, evaluation fixtures, and fallback behavior. Tickets with security-privacy secondary domains need extra care around extracted text and citation risk.

## Tickets

```dataview
LIST
FROM "Projects/Casa Segura/Roadmap/tickets"
WHERE domain = "ai-rag" OR contains(secondary_domains, "ai-rag")
SORT file.name ASC
```

```query
tag:#domain/ai-rag path:"Projects/Casa Segura/Roadmap/tickets"
```
