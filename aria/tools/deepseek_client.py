"""
ARIA v2 — DeepSeek Client
Code analysis provider for GitHub Research and Pattern Extraction agents.

Uses ProviderPool with 2 DeepSeek keys (~116 RPM total).
DeepSeek is code-native — runs deepseek-chat model.

Falls back to SiliconFlow when DeepSeek balance is exhausted (402 error).
"""

from typing import Any, Optional

from openai import AsyncOpenAI

from config import PROVIDER_MODELS
from provider_pool import (
    pool,
    validated_generate,
    ProviderUnavailable,
    SchemaValidationFailed,
    RateLimitError,
    APIError,
)

# Lazy imports to avoid circular dependencies
_groq = None
_zhipu = None

def _get_groq_client():
    global _groq
    if _groq is None:
        from tools.groq_client import GroqClient
        _groq = GroqClient()
    return _groq

def _get_zhipu_client():
    global _zhipu
    if _zhipu is None:
        from tools.zhipu_client import ZhipuClient
        _zhipu = ZhipuClient()
    return _zhipu



class DeepSeekClient:
    """
    DeepSeek API client — deepseek-chat (code-native).

    2 keys in rotation = ~116 RPM effective capacity.
    Used for: GitHub research, pattern extraction.
    """

    def __init__(self):
        self.provider = "deepseek"
        self.model = PROVIDER_MODELS["deepseek"]

    async def generate(
        self,
        messages: list[dict[str, str]],
        response_format: Optional[type] = None,
        temperature: float = 0.3,
        max_tokens: int = 8192,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Generate a response from DeepSeek for code analysis tasks.

        Args:
            messages: Chat messages in OpenAI format
            response_format: Optional Pydantic model for JSON output
            temperature: Sampling temperature (default 0.3)
            max_tokens: Max tokens (higher for code analysis)
            **kwargs: Additional params

        Returns:
            Parsed JSON dict
        """
        client = pool.get_client(self.provider)
        cb = pool.get_circuit_breaker(self.provider)

        if not cb:
            raise ProviderUnavailable("DeepSeek circuit breaker not initialized")

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
            err_str = str(e)
            # DeepSeek insufficient balance (402) — try fallback chain
            if "402" in err_str or "Insufficient Balance" in err_str or "insufficient_balance" in err_str:
                # Try Groq (validated working)
                try:
                    groq = _get_groq_client()
                    return await groq.generate(messages, response_format=response_format, temperature=temperature, max_tokens=max_tokens, **kwargs)
                except Exception:
                    pass
                # Try Zhipu as final fallback
                zhipu = _get_zhipu_client()
                return await zhipu.generate(messages, response_format=response_format, temperature=temperature, max_tokens=max_tokens, **kwargs)
            raise APIError(f"DeepSeek API error: {e}") from e

    async def generate_text(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 8192,
    ) -> str:
        """Generate free-text response for code analysis."""
        client = pool.get_client(self.provider)
        cb = pool.get_circuit_breaker(self.provider)

        if not cb:
            raise ProviderUnavailable("DeepSeek circuit breaker not initialized")

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
            err_str = str(e)
            # DeepSeek insufficient balance (402) — try fallback chain
            if "402" in err_str or "Insufficient Balance" in err_str or "insufficient_balance" in err_str:
                # Try Groq (validated working)
                try:
                    groq = _get_groq_client()
                    return await groq.generate_text(messages, temperature=temperature, max_tokens=max_tokens)
                except Exception:
                    pass
                # Try Zhipu as final fallback
                zhipu = _get_zhipu_client()
                return await zhipu.generate_text(messages, temperature=temperature, max_tokens=max_tokens)
            raise APIError(f"DeepSeek text API error: {e}") from e


__all__ = ["DeepSeekClient", "RateLimitError", "APIError", "ProviderUnavailable", "SchemaValidationFailed"]
