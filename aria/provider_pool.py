"""
ARIA v2 — Provider Pool Module
Manages multi-provider LLM access with:
- ProviderPool: round-robin key rotation across all providers
- TokenBucketLimiter: per-key rate limiting across parallel tasks
- CircuitBreaker: fail-fast when providers are unhealthy
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional

import httpx
from openai import AsyncOpenAI

from config import (
    PROVIDER_ENDPOINTS,
    PROVIDER_MODELS,
    RATE_LIMITS,
    get_cerebras_key,
    get_deepseek_keys,
    get_gemini_keys,
    get_groq_keys,
    get_nvidia_keys,
    get_sambanova_keys,
    get_siliconflow_keys,
    get_zhipu_key,
)

# ─── Custom Exceptions ─────────────────────────────────────────────────────────

class RateLimitError(Exception):
    """Raised when a provider returns a rate limit error."""
    pass


class APIError(Exception):
    """Raised when a provider returns a non-rate-limit API error."""
    pass


class ProviderUnavailable(Exception):
    """Raised when a provider's circuit breaker is OPEN."""
    pass


class SchemaValidationFailed(Exception):
    """Raised when structured output fails validation after max retries."""
    pass


# ─── Token Bucket Limiter ──────────────────────────────────────────────────────

class TokenBucketLimiter:
    """
    Async token bucket rate limiter — safe across concurrent tasks.

    Maintains a per-key token bucket that refills at rate/60 tokens per second.
    Uses asyncio.Lock for thread safety across parallel agent calls.
    """

    def __init__(self, rpm: int):
        if rpm <= 0:
            raise ValueError("RPM must be positive")
        self.capacity = rpm
        self.tokens = float(rpm)
        self.refill_rate = rpm / 60.0  # tokens per second
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def wait(self) -> None:
        """
        Wait until a token is available. Blocks if the bucket is empty,
        sleeping just long enough for one token to refill.
        """
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now

            if self.tokens < 1:
                wait_time = (1 - self.tokens) / max(self.refill_rate, 0.001)
                await asyncio.sleep(wait_time)
                self.tokens = 0
            else:
                self.tokens -= 1


# ─── Circuit Breaker ───────────────────────────────────────────────────────────

class CircuitState(Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Failing, reject fast
    HALF_OPEN = "half_open" # Testing recovery


class CircuitBreaker:
    """
    Circuit breaker per provider.

    After `failure_threshold` consecutive failures, the circuit OPENS and
    all calls fail fast with ProviderUnavailable for `recovery_timeout` seconds.
    After the timeout, transitions to HALF_OPEN — one test call is allowed.
    If it succeeds, the circuit resets to CLOSED. If it fails, back to OPEN.
    """

    def __init__(self, provider: str, failure_threshold: int = 3, recovery_timeout: int = 60):
        self.provider = provider
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.opened_at: Optional[datetime] = None
        self._lock = asyncio.Lock()

    async def call(self, fn: Callable, *args: Any, **kwargs: Any) -> Any:
        """
        Execute a call through the circuit breaker.

        Args:
            fn: Async function to call
            *args, **kwargs: Passed through to fn

        Returns:
            The result of fn(*args, **kwargs)

        Raises:
            ProviderUnavailable: If circuit is OPEN
            RateLimitError: On rate limit (recorded as failure)
            APIError: On other API errors (recorded as failure)
        """
        async with self._lock:
            if self.state == CircuitState.OPEN:
                if self.opened_at and (datetime.now() - self.opened_at) > timedelta(seconds=self.recovery_timeout):
                    self.state = CircuitState.HALF_OPEN
                else:
                    raise ProviderUnavailable(
                        f"⛔ {self.provider} circuit OPEN — failing fast. "
                        f"Retry in ~{self._remaining_seconds()}s"
                    )

        try:
            result = await fn(*args, **kwargs)
            async with self._lock:
                if self.state == CircuitState.HALF_OPEN:
                    self._reset()
            return result
        except (RateLimitError, APIError):
            await self._record_failure()
            raise

    def _remaining_seconds(self) -> int:
        if not self.opened_at:
            return 0
        elapsed = (datetime.now() - self.opened_at).total_seconds()
        return max(0, int(self.recovery_timeout - elapsed))

    async def _record_failure(self) -> None:
        async with self._lock:
            self.failures += 1
            if self.failures >= self.threshold:
                self.state = CircuitState.OPEN
                self.opened_at = datetime.now()

    def _reset(self) -> None:
        self.failures = 0
        self.state = CircuitState.CLOSED
        self.opened_at = None

    @property
    def is_available(self) -> bool:
        """Quick check if the circuit is available (not OPEN)."""
        return self.state != CircuitState.OPEN

    @property
    def status_text(self) -> str:
        """Human-readable status."""
        icons = {CircuitState.CLOSED: "🟢", CircuitState.OPEN: "🔴", CircuitState.HALF_OPEN: "🟡"}
        status = icons.get(self.state, "⚪")
        if self.state == CircuitState.OPEN:
            return f"{status} OPEN (retry in {self._remaining_seconds()}s)"
        return f"{status} {self.state.value.upper()}"


# ─── Provider Pool ─────────────────────────────────────────────────────────────

class ProviderPool:
    """
    Manages all LLM API providers with round-robin key rotation.

    Groq has 4 keys → ~112 RPM total
    DeepSeek has 2 keys → ~116 RPM total
    SambaNova has 2 keys → ~36 RPM total
    SiliconFlow has 2 keys → ~56 RPM total
    NVIDIA has 2 keys → ~36 RPM total
    Cerebras has 1 key → ~28 RPM total
    Zhipu has 1 key → ~20 RPM total

    ProviderPool.get_client(provider) returns an AsyncOpenAI client configured
    for that provider's endpoint with a rotated key.
    """

    def __init__(self):
        self._key_pools: dict[str, list[str]] = {}
        self._key_indices: dict[str, int] = {}
        self._rate_limiters: dict[str, TokenBucketLimiter] = {}
        self._circuit_breakers: dict[str, CircuitBreaker] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._clients: dict[str, AsyncOpenAI] = {}
        # Tracks the last meaningful failure reason per provider (persists across calls)
        self._last_errors: dict[str, dict] = {}  # {provider: {code, msg, type}}

        self._init_pools()

    def _init_pools(self) -> None:
        """Initialise all provider key pools and rate limiters.
        Filters empty/invalid keys to avoid silent auth failures.
        """
        def _filter_keys(keys: list[str]) -> list[str]:
            return [k.strip() for k in keys if k and k.strip()]

        providers = {
            "groq": (_filter_keys(get_groq_keys()), RATE_LIMITS["groq_per_key"]["rpm"]),
            "deepseek": (_filter_keys(get_deepseek_keys()), RATE_LIMITS["deepseek_per_key"]["rpm"]),
            "sambanova": (_filter_keys(get_sambanova_keys()), RATE_LIMITS["sambanova_per_key"]["rpm"]),
            "siliconflow": (_filter_keys(get_siliconflow_keys()), RATE_LIMITS["siliconflow_per_key"]["rpm"]),
            "nvidia": (_filter_keys(get_nvidia_keys()), RATE_LIMITS["nvidia_per_key"]["rpm"]),
        }

        # Single-key providers
        single_key = {
            "cerebras": (get_cerebras_key(), RATE_LIMITS["cerebras"]["rpm"]),
            "zhipu": (get_zhipu_key(), RATE_LIMITS.get("zhipu_per_key", {"rpm": 20})["rpm"]),
            "gemini": (_filter_keys(get_gemini_keys()), RATE_LIMITS["gemini_flash"]["rpm"]),
        }

        for provider, (keys, rpm) in providers.items():
            if keys:
                self._key_pools[provider] = keys
                self._key_indices[provider] = 0
                for idx, key in enumerate(keys):
                    limiter_key = f"{provider}:{idx}"
                    self._rate_limiters[limiter_key] = TokenBucketLimiter(rpm)
                self._circuit_breakers[provider] = CircuitBreaker(provider)
                self._locks[provider] = asyncio.Lock()

        for provider, (key, rpm) in single_key.items():
            is_valid = isinstance(key, str) and len(key.strip()) > 0
            if is_valid:
                key_str = key.strip() if isinstance(key, str) else key
                self._key_pools[provider] = [key_str]
                self._key_indices[provider] = 0
                limiter_key = f"{provider}:0"
                self._rate_limiters[limiter_key] = TokenBucketLimiter(rpm)
                self._circuit_breakers[provider] = CircuitBreaker(provider)
                self._locks[provider] = asyncio.Lock()

    def _get_next_key(self, provider: str) -> Optional[str]:
        """Round-robin key rotation."""
        keys = self._key_pools.get(provider, [])
        if not keys:
            return None
        idx = self._key_indices.get(provider, 0)
        key = keys[idx % len(keys)]
        self._key_indices[provider] = (idx + 1) % len(keys)
        return key

    def get_client(self, provider: str) -> AsyncOpenAI:
        """Get or create an AsyncOpenAI client for the given provider."""
        if provider not in self._clients:
            endpoint = PROVIDER_ENDPOINTS.get(provider)
            if not endpoint:
                raise ValueError(f"Unknown provider: {provider}")
            key = self._get_next_key(provider)
            if not key:
                raise ProviderUnavailable(f"No API keys configured for {provider}")
            self._clients[provider] = AsyncOpenAI(
                api_key=key,
                base_url=endpoint,
                timeout=httpx.Timeout(120.0, connect=10.0),
                max_retries=0,
            )
        return self._clients[provider]

    async def refresh_client(self, provider: str) -> AsyncOpenAI:
        """Force a new client (next key in rotation). Useful after rate limit."""
        if provider in self._clients:
            del self._clients[provider]
        return self.get_client(provider)

    async def wait_for_capacity(self, provider: str) -> None:
        """Wait for rate limit capacity on any key for this provider."""
        keys = self._key_pools.get(provider, [])
        for key in keys:
            limiter_key = f"{provider}:{key[:8]}"
            limiter = self._rate_limiters.get(limiter_key)
            if limiter:
                await limiter.wait()
                return

    def get_circuit_breaker(self, provider: str) -> Optional[CircuitBreaker]:
        return self._circuit_breakers.get(provider)

    def record_error(self, provider: str, http_status: int, message: str) -> None:
        """Record a meaningful API failure so it surfaces in the UI."""
        type_map = {
            401: ("invalid_key", "Invalid API key"),
            402: ("no_credits", "No credits / insufficient balance"),
            403: ("forbidden", "Forbidden / access denied"),
            404: ("model_not_found", "Model not found"),
            410: ("model_deprecated", "Model deprecated"),
            429: ("rate_limited", "Rate limited"),
            500: ("server_error", "Provider server error"),
            503: ("unavailable", "Provider unavailable"),
        }
        err_type, default_msg = type_map.get(http_status, ("api_error", f"HTTP {http_status}"))
        self._last_errors[provider] = {
            "http_status": http_status,
            "type": err_type,
            "msg": message[:120] or default_msg,
        }

    def get_last_error(self, provider: str) -> Optional[dict]:
        return self._last_errors.get(provider)

    def is_available(self, provider: str) -> bool:
        """Check if a provider has keys configured and circuit is not OPEN."""
        cb = self._circuit_breakers.get(provider)
        if cb and not cb.is_available:
            return False
        return bool(self._key_pools.get(provider))

    def get_provider_status(self) -> dict[str, str]:
        """Return status text for all providers (for Rich panel display)."""
        status = {}
        for provider in ["groq", "deepseek", "sambanova", "siliconflow", "nvidia", "cerebras", "zhipu", "gemini"]:
            cb = self._circuit_breakers.get(provider)
            key_count = len(self._key_pools.get(provider, []))
            last_err = self._last_errors.get(provider)
            if key_count == 0:
                status[provider] = "⚪ Not configured"
            elif last_err and last_err["type"] in ("invalid_key", "no_credits", "model_deprecated", "model_not_found"):
                icons = {"invalid_key": "🔑", "no_credits": "💸", "model_deprecated": "⚰", "model_not_found": "❓"}
                icon = icons.get(last_err["type"], "❌")
                status[provider] = f"{icon} {last_err['msg']}"
            elif cb:
                status[provider] = f"{cb.status_text} ({key_count} key{'s' if key_count > 1 else ''})"
            else:
                status[provider] = f"🟢 READY ({key_count} key{'s' if key_count > 1 else ''})"
        return status

    def get_provider_health(self) -> list[dict]:
        """Return structured health info for all providers — used by the UI status endpoint."""
        health = []
        for provider in ["groq", "deepseek", "sambanova", "siliconflow", "nvidia", "cerebras", "zhipu", "gemini"]:
            cb = self._circuit_breakers.get(provider)
            key_count = len(self._key_pools.get(provider, []))
            last_err = self._last_errors.get(provider)

            if key_count == 0:
                ui_status = "unconfigured"
                ui_label = "no keys"
                ui_color = "muted"
            elif last_err:
                err_type = last_err["type"]
                if err_type == "invalid_key":
                    ui_status = "invalid_key"
                    ui_label = "invalid key"
                    ui_color = "err"
                elif err_type == "no_credits":
                    ui_status = "no_credits"
                    ui_label = "no credits"
                    ui_color = "warn"
                elif err_type in ("model_deprecated", "model_not_found"):
                    ui_status = "model_error"
                    ui_label = "model error"
                    ui_color = "warn"
                elif err_type == "rate_limited":
                    ui_status = "rate_limited"
                    ui_label = "rate limited"
                    ui_color = "warn"
                elif cb and not cb.is_available:
                    ui_status = "circuit_open"
                    ui_label = "circuit open"
                    ui_color = "err"
                else:
                    ui_status = "degraded"
                    ui_label = last_err["msg"][:40]
                    ui_color = "warn"
            elif cb and not cb.is_available:
                ui_status = "circuit_open"
                ui_label = "circuit open"
                ui_color = "err"
            else:
                ui_status = "ok"
                ui_label = "ready"
                ui_color = "ok"

            health.append({
                "provider": provider,
                "ui_status": ui_status,
                "ui_label": ui_label,
                "ui_color": ui_color,
                "last_error": last_err,
                "circuit_state": cb.state.value if cb else "no_cb",
                "circuit_failures": cb.failures if cb else 0,
            })
        return health

    def get_model(self, provider: str) -> str:
        """Get the default model for a provider."""
        return PROVIDER_MODELS.get(provider, "unknown")


# ─── Structured Output Validation ─────────────────────────────────────────────

async def validated_generate(
    client: AsyncOpenAI,
    model: str,
    messages: list[dict[str, str]],
    response_format: Optional[type] = None,
    max_retries: int = 3,
    _provider: str = "",
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Generate structured output with automatic retry and schema validation.

    Wraps every LLM call that returns JSON with:
    - Retry loop (up to max_retries attempts)
    - Schema repair prompt injection on failure
    - JSON parsing with error recovery

    Args:
        client: AsyncOpenAI client
        model: Model name string
        messages: Chat messages (will be mutated on retry)
        response_format: Optional Pydantic model class for response_format param
        max_retries: Max retry attempts (default 3)
        **kwargs: Passed to client.chat.completions.create()

    Returns:
        Parsed JSON dict

    Raises:
        SchemaValidationFailed: After max_retries exhausted
    """
    for attempt in range(max_retries):
        try:
            kwargs["model"] = model
            kwargs["messages"] = messages

            try:
                if response_format:
                    response = await client.chat.completions.create(
                        **kwargs,
                        response_format={"type": "json_object"},
                    )
                else:
                    response = await client.chat.completions.create(**kwargs)
            except Exception as api_err:
                # Capture HTTP status errors and record them in the pool
                status_code = getattr(api_err, "status_code", None)
                if status_code and _provider:
                    msg = ""
                    body = getattr(api_err, "body", None) or getattr(api_err, "message", "")
                    if isinstance(body, dict):
                        msg = body.get("error", {}).get("message", "") or str(body)
                    else:
                        msg = str(body)
                    pool.record_error(_provider, status_code, msg)
                raise

            raw = response.choices[0].message.content or ""
            # Strip markdown fences if present
            clean = raw.strip()
            if clean.startswith("```"):
                # Remove ```json or ``` fences
                clean = clean.split("\n", 1)[-1] if "\n" in clean else clean
                clean = clean.rsplit("```", 1)[0] if "```" in clean else clean
            clean = clean.strip()

            parsed = json.loads(clean)

            # Basic structure validation — ensure it's a dict
            if not isinstance(parsed, dict):
                raise ValueError("Response is not a JSON object")

            return parsed

        except (json.JSONDecodeError, ValueError) as e:
            if attempt == max_retries - 1:
                raise SchemaValidationFailed(
                    f"❌ Agent failed {max_retries} attempts. Last error: {e}\n"
                    f"Last raw response: {raw[:500]}"
                )
            # Repair prompt — append to last user message
            error_msg = str(e)
            messages.append({
                "role": "user",
                "content": (
                    f"⚠️ RETRY {attempt + 1}/{max_retries}: Your previous response was not valid JSON.\n"
                    f"Error: {error_msg}\n"
                    f"Return ONLY valid JSON. No markdown fences. No explanation. No code blocks."
                ),
            })

    raise SchemaValidationFailed("Exhausted retries")


# ─── Global Singleton ──────────────────────────────────────────────────────────

pool = ProviderPool()
