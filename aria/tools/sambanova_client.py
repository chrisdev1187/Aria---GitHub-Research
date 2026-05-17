"""
ARIA v2 — SambaNova Client
Synthesis fallback provider. Used when NVIDIA NIM is unavailable.

2 keys in rotation = ~36 RPM total.
Model: Meta-Llama-3.1-8B-Instruct
"""

from typing import Any, Optional

from config import PROVIDER_MODELS
from provider_pool import pool, validated_generate, ProviderUnavailable, RateLimitError, APIError, SchemaValidationFailed


class SambaNovaClient:
    """SambaNova API client — fallback for synthesis."""

    def __init__(self):
        self.provider = "sambanova"
        self.model = PROVIDER_MODELS["sambanova"]

    async def generate(
        self,
        messages: list[dict[str, str]],
        response_format: Optional[type] = None,
        temperature: float = 0.3,
        max_tokens: int = 8192,
        **kwargs: Any,
    ) -> dict[str, Any]:
        client = pool.get_client(self.provider)
        cb = pool.get_circuit_breaker(self.provider)

        if not cb:
            raise ProviderUnavailable("SambaNova circuit breaker not initialized")

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
            raise APIError(f"SambaNova API error: {e}") from e

    async def generate_text(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 8192,
    ) -> str:
        """Generate free-text response (for research briefs)."""
        client = pool.get_client(self.provider)
        cb = pool.get_circuit_breaker(self.provider)

        if not cb:
            raise ProviderUnavailable("SambaNova circuit breaker not initialized")

        async def call():
            await pool.wait_for_capacity(self.provider)
            response = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ""

        try:
            return await cb.call(call)
        except ProviderUnavailable:
            raise
        except Exception as e:
            raise APIError(f"SambaNova text API error: {e}") from e


__all__ = ["SambaNovaClient", "RateLimitError", "APIError", "ProviderUnavailable", "SchemaValidationFailed"]
