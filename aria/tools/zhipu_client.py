"""
ARIA v2 — Zhipu (GLM) Client
Final fallback provider — Chinese/multilingual support.

Single key = ~20 RPM.
Used as: last-resort fallback when all other providers are down.
Model: glm-4-flash
"""

from typing import Any, Optional

from config import PROVIDER_MODELS
from provider_pool import pool, validated_generate, ProviderUnavailable, RateLimitError, APIError, SchemaValidationFailed


class ZhipuClient:
    """Zhipu (GLM) API client — final fallback tier."""

    def __init__(self):
        self.provider = "zhipu"
        self.model = PROVIDER_MODELS["zhipu"]

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
            raise ProviderUnavailable("Zhipu circuit breaker not initialized")

        async def call():
            await pool.wait_for_capacity(self.provider)
            return await validated_generate(
                client=client,
                model=self.model,
                messages=messages,
                response_format=response_format,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )

        try:
            return await cb.call(call)
        except ProviderUnavailable:
            raise
        except Exception as e:
            raise APIError(f"Zhipu API error: {e}") from e


__all__ = ["ZhipuClient", "RateLimitError", "APIError", "ProviderUnavailable", "SchemaValidationFailed"]
