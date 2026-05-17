"""
ARIA v2 — Ollama Client
Local LLM provider with RAM-aware sequential execution.

⚠️  RAM constraint: 8GB total. Ollama calls MUST be sequential (never parallel)
to prevent OOM. All calls use asyncio.Lock() — only one Ollama call at a time.

Default model: qwen2.5:3b-instruct-q4_K_M (~2.2GB RAM)
Deep model: qwen2.5-coder:7b-q4_K_M (~5.5GB RAM, --deep flag only)
"""

import asyncio
import os
from typing import Any

from config import PROVIDER_MODELS, hardware
from provider_pool import SchemaValidationFailed

# Global sequential lock — NEVER run two Ollama calls in parallel
_ollama_lock = asyncio.Lock()


class OllamaClient:
    """
    Ollama client for local inference.

    All calls go through _ollama_lock to ensure sequential execution.
    Cloud providers handle parallel inference; Ollama is fallback/privacy mode.
    """

    def __init__(self, use_deep: bool = False):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = PROVIDER_MODELS["ollama_deep"] if use_deep else PROVIDER_MODELS["ollama_default"]
        self.use_deep = use_deep

    async def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Generate a response from local Ollama model.

        ⚠️  Sequential lock: Only one Ollama call runs at a time.
        This prevents OOM on the 8GB RAM system.

        Args:
            messages: Chat messages in OpenAI format
            temperature: Sampling temperature
            max_tokens: Max tokens
            **kwargs: Additional params

        Returns:
            Parsed JSON dict
        """
        async with _ollama_lock:
            import ollama
            client = ollama.AsyncClient(host=self.base_url)

            response = await client.chat(
                model=self.model,
                messages=messages,
                options={
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            )

            content = response["message"]["content"]
            import json

            # Strip markdown fences
            clean = content.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[-1] if "\n" in clean else clean
                clean = clean.rsplit("```", 1)[0] if "```" in clean else clean
            clean = clean.strip()

            try:
                return json.loads(clean)
            except json.JSONDecodeError as e:
                raise SchemaValidationFailed(
                    f"Ollama response was not valid JSON: {e}\n"
                    f"Raw response: {content[:500]}"
                ) from e

    async def generate_text(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Generate free-text response from local Ollama model."""
        async with _ollama_lock:
            import ollama
            client = ollama.AsyncClient(host=self.base_url)

            response = await client.chat(
                model=self.model,
                messages=messages,
                options={
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            )
            return response["message"]["content"]

    async def is_available(self) -> bool:
        """Check if Ollama is running and the model is available."""
        try:
            async with _ollama_lock:
                import ollama
                client = ollama.AsyncClient(host=self.base_url)
                models = await client.list()
                return any(self.model in m.get("name", "") for m in models.get("models", []))
        except Exception:
            return False

    @property
    def ram_estimate_gb(self) -> float:
        """Estimated RAM usage for the current model."""
        return hardware.ollama_qwen7b_gb if self.use_deep else hardware.ollama_qwen3b_gb
