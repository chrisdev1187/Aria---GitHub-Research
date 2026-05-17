"""
ARIA v2 — NVIDIA NIM Client
Primary synthesis provider (llama-3.1-8b-instruct).

2 keys in rotation = ~36 RPM total.
Used for: Synthesizer agent — producing the final master research brief.
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


class NvidiaClient:
    """NVIDIA NIM API client — primary synthesizer."""

    def __init__(self):
        self.provider = "nvidia"
        self.model = PROVIDER_MODELS["nvidia"]

    async def generate(
        self,
        messages: list[dict[str, str]],
        response_format: Optional[type] = None,
        temperature: float = 0.3,
        max_tokens: int = 16384,
        **kwargs: Any,
    ) -> dict[str, Any]:
        client = pool.get_client(self.provider)
        cb = pool.get_circuit_breaker(self.provider)

        if not cb:
            raise ProviderUnavailable("NVIDIA circuit breaker not initialized")

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
            raise APIError(f"NVIDIA API error: {e}") from e

    async def generate_text(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 16384,
    ) -> str:
        """Generate free-text response (for markdown briefs)."""
        client = pool.get_client(self.provider)
        cb = pool.get_circuit_breaker(self.provider)

        if not cb:
            raise ProviderUnavailable("NVIDIA circuit breaker not initialized")

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
            raise APIError(f"NVIDIA text API error: {e}") from e


__all__ = ["NvidiaClient", "RateLimitError", "APIError", "ProviderUnavailable", "SchemaValidationFailed"]
