"""LLM gateway package (CS-006).

Provides a single client surface for upstream LLM/OCR providers (currently
OpenRouter). All outbound HTTP traffic to OpenRouter MUST go through
`shared.llm.openrouter.OpenRouterClient` so retry/backoff, header injection
and response-shape mocking stay consistent across ingestion, classification
and reports.
"""

from shared.llm.openrouter import OpenRouterClient, OpenRouterError

__all__ = ["OpenRouterClient", "OpenRouterError"]
