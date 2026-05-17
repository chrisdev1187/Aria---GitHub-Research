"""
ARIA v2 — SiliconFlow Client
Web researcher provider + general fallback.

2 keys in rotation = ~56 RPM total.
Model: Qwen/Qwen2.5-72B-Instruct
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


class SiliconFlowClient:
    """SiliconFlow API client — web research + general fallback."""

    def __init__(self):
        self.provider = "siliconflow"
        self.model = PROVIDER_MODELS["siliconflow"]

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
            raise ProviderUnavailable("SiliconFlow circuit breaker not initialized")

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
            raise APIError(f"SiliconFlow API error: {e}") from e


__all__ = ["SiliconFlowClient", "RateLimitError", "APIError", "ProviderUnavailable", "SchemaValidationFailed"]
