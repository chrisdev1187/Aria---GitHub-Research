"""
ARIA v2 — Groq Client
Primary fast inference provider for Intake, Decomposer, and Quality Judge agents.

Uses ProviderPool for key rotation across 4 Groq keys (~112 RPM total).
Wraps all LLM calls with validated_generate for structured output.

Fallback chain (when Groq fails): Groq → Cerebras → SiliconFlow → Zhipu
"""

from typing import Any, Optional

from openai import AsyncOpenAI

from config import PROVIDER_MODELS
from provider_pool import pool, validated_generate, ProviderUnavailable, SchemaValidationFailed

# Lazy imports to avoid circular dependencies
_cerebras = None
_siliconflow = None
_zhipu = None


def _get_cerebras_client():
    global _cerebras
    if _cerebras is None:
        from tools.cerebras_client import CerebrasClient
        _cerebras = CerebrasClient()
    return _cerebras


def _get_siliconflow_client():
    global _siliconflow
    if _siliconflow is None:
        from tools.siliconflow_client import SiliconFlowClient
        _siliconflow = SiliconFlowClient()
    return _siliconflow


def _get_zhipu_client():
    global _zhipu
    if _zhipu is None:
        from tools.zhipu_client import ZhipuClient
        _zhipu = ZhipuClient()
    return _zhipu


class GroqClient:
    """
    Groq API client — llama-3.3-70b-versatile.

    4 keys in rotation = ~112 RPM effective capacity.
    Used for: intake, decomposition, quality judging.

    Built-in fallback chain: Groq → Cerebras → SiliconFlow → Zhipu
    Automatically cascades when Groq hits rate limits or balance errors.
    """

    def __init__(self):
        self.provider = "groq"
        self.model = PROVIDER_MODELS["groq"]

    async def _try_fallback_chain(
        self,
        method_name: str,
        messages: list[dict[str, str]],
        response_format: Optional[type] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> Any:
        """
        Try fallback providers in order when Groq fails.
        Chain: Cerebras → SiliconFlow → Zhipu
        """
        errors = []

        # Fallback 1: Cerebras (same model family, fast)
        try:
            cerebras = _get_cerebras_client()
            if method_name == "generate":
                return await cerebras.generate(
                    messages=messages,
                    response_format=response_format,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                )
            else:
                return await cerebras.generate_text(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
        except Exception as e:
            errors.append(f"Cerebras: {e}")

        # Fallback 2: SiliconFlow
        try:
            sf = _get_siliconflow_client()
            if method_name == "generate":
                return await sf.generate(
                    messages=messages,
                    response_format=response_format,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                )
            else:
                return await sf.generate_text(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
        except Exception as e:
            errors.append(f"SiliconFlow: {e}")

        # Fallback 3: Zhipu (last resort)
        try:
            zhipu = _get_zhipu_client()
            if method_name == "generate":
                return await zhipu.generate(
                    messages=messages,
                    response_format=response_format,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                )
            else:
                return await zhipu.generate_text(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
        except Exception as e:
            errors.append(f"Zhipu: {e}")

        raise APIError(
            f"Groq + all fallbacks exhausted. Errors: {'; '.join(errors)}"
        )

    async def generate(
        self,
        messages: list[dict[str, str]],
        response_format: Optional[type] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Generate a response from Groq with structured output validation.
        Falls back to Cerebras → SiliconFlow → Zhipu if Groq fails.

        Args:
            messages: Chat messages in OpenAI format
            response_format: Optional Pydantic model for JSON output
            temperature: Sampling temperature (default 0.3 for structured output)
            max_tokens: Max tokens in response
            **kwargs: Additional params

        Returns:
            Parsed JSON dict (if response_format provided) or raw content dict
        """
        try:
            client = pool.get_client(self.provider)
            cb = pool.get_circuit_breaker(self.provider)

            if not cb:
                raise ProviderUnavailable("Groq circuit breaker not initialized")

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

            return await cb.call(call)
        except ProviderUnavailable:
            # Circuit is open — skip straight to fallback chain
            return await self._try_fallback_chain(
                "generate", messages, response_format, temperature, max_tokens, **kwargs
            )
        except Exception as e:
            err_str = str(e).lower()
            # Rate limit, insufficient balance, or any API error — try fallbacks
            if any(x in err_str for x in ["429", "rate limit", "insufficient", "402", "balance", "timeout", "503", "502"]):
                return await self._try_fallback_chain(
                    "generate", messages, response_format, temperature, max_tokens, **kwargs
                )
            raise APIError(f"Groq API error: {e}") from e

    async def generate_text(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """
        Generate free-text response (non-JSON). Returns raw string content.
        Falls back to Cerebras → SiliconFlow → Zhipu if Groq fails.
        """
        try:
            client = pool.get_client(self.provider)
            cb = pool.get_circuit_breaker(self.provider)

            if not cb:
                raise ProviderUnavailable("Groq circuit breaker not initialized")

            async def call():
                await pool.wait_for_capacity(self.provider)
                response = await client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return response.choices[0].message.content or ""

            return await cb.call(call)
        except ProviderUnavailable:
            return await self._try_fallback_chain(
                "generate_text", messages, temperature=temperature, max_tokens=max_tokens
            )
        except Exception as e:
            err_str = str(e).lower()
            if any(x in err_str for x in ["429", "rate limit", "insufficient", "402", "balance", "timeout", "503", "502"]):
                return await self._try_fallback_chain(
                    "generate_text", messages, temperature=temperature, max_tokens=max_tokens
                )
            raise APIError(f"Groq text API error: {e}") from e


# Re-export for convenience
from provider_pool import RateLimitError, APIError

__all__ = ["GroqClient", "RateLimitError", "APIError", "ProviderUnavailable", "SchemaValidationFailed"]
