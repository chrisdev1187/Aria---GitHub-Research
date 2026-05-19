"""
ARIA v2 — Cerebras Client
Circuit breaker hot path — fastest inference when Groq is unavailable.

Single key = ~28 RPM.
Used as: fallback for Intake, Decomposer, Quality Judge when Groq is down.
Model: llama-3.3-70b
"""

from typing import Any, Optional

from config import PROVIDER_MODELS
from provider_pool import (
    APIError,
    ProviderUnavailable,
    RateLimitError,
    SchemaValidationFailed,
    pool,
    validated_generate,
)


class CerebrasClient:
    """Cerebras API client — ultra-fast inference fallback."""

    def __init__(self):
        self.provider = "cerebras"
        self.model = PROVIDER_MODELS["cerebras"]

    async def generate(
        self,
        messages: list[dict[str, str]],
        response_format: Optional[type] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> dict[str, Any]:
        client = pool.get_client(self.provider)
        cb = pool.get_circuit_breaker(self.provider)

        if not cb:
            raise ProviderUnavailable("Cerebras circuit breaker not initialized")

        async def call():
            await pool.wait_for_capacity(self.provider)
            return await validated_generate(
                client=client,
                model=self.model,
                messages=messages,
                response_format=response_format,
                temperature=temperature,
                max_tokens=max_tokens,
                _provider=self.provider,
                **kwargs,
            )

        try:
            return await cb.call(call)
        except ProviderUnavailable:
            raise
        except Exception as e:
            raise APIError(f"Cerebras API error: {e}") from e


__all__ = ["CerebrasClient", "RateLimitError", "APIError", "ProviderUnavailable", "SchemaValidationFailed"]
