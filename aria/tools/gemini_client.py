"""
ARIA v2 — Gemini Flash Client
Large file context reader ONLY (1M token window).

⚠️  IMPORTANT: Gemini Flash is demoted from primary inference in v2.
It is ONLY used for reading large files (>50KB) where the 1M context
window is genuinely unique and useful.

Rate limited to 13 RPM. Do NOT use for general inference.
"""


from config import get_gemini_keys
from provider_pool import RATE_LIMITS, TokenBucketLimiter


class GeminiClient:
    """
    Gemini Flash client — context reader only.

    Used exclusively for reading large source files (>50KB) that exceed
    other providers' context windows. The 1M context is genuinely unique.

    Rate limited to 13 RPM (conservative safety buffer on 15 RPM limit).
    """

    def __init__(self):
        gemini_keys = get_gemini_keys()
        self.api_key = gemini_keys[0] if gemini_keys else None
        self.api_keys = gemini_keys  # Store all keys for potential rotation
        self.model_name = "gemini-2.0-flash"
        self.rate_limiter = TokenBucketLimiter(RATE_LIMITS["gemini_flash"]["rpm"])
        self._client = None

    async def _ensure_client(self):
        """Lazy-load the Google Generative AI client."""
        if self._client is None:
            if not self.api_key:
                raise ValueError(
                    "GEMINI_API_KEY not set. Gemini Flash is only needed for "
                    "large file reads (>50KB). Other providers handle smaller files."
                )
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._client = genai.GenerativeModel(self.model_name)
        return self._client

    async def read_large_file(self, file_url: str, max_chars: int = 500_000) -> str:
        """
        Read a large file using Gemini's 1M context window.

        Only call this for files >50KB that other providers can't handle.

        Args:
            file_url: URL or path to the file content
            max_chars: Max characters to read (default 500K, well within 1M token limit)

        Returns:
            File content as string

        Raises:
            ValueError: If called without a configured key
            RateLimitError: If rate limited
        """
        await self.rate_limiter.wait()
        client = await self._ensure_client()

        # Fetch file content
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as response:
                content = await response.text()
                content = content[:max_chars]

        prompt = f"""Read and summarise the following source code file.
Extract: purpose, key functions/classes, dependencies, important patterns.

FILE CONTENT:
```{content}```"""

        response = await client.generate_content_async(prompt)
        return response.text if hasattr(response, 'text') else str(response)

    async def summarize_content(self, content: str, filename: str = "") -> str:
        """
        Summarize large source code content already in memory.

        Use this when you already have the file content and it exceeds what
        other providers can handle. Returns a structured summary of the file.

        Args:
            content: Raw source file content
            filename: Optional filename for context (e.g. "src/core/engine.py")

        Returns:
            Structured summary: purpose, key functions/classes, dependencies, patterns
        """
        await self.rate_limiter.wait()
        client = await self._ensure_client()

        name_hint = f" ({filename})" if filename else ""
        prompt = (
            f"Summarise this source code file{name_hint}.\n"
            "Extract: purpose, key functions/classes, dependencies, important patterns.\n"
            "Be concise but complete — output ≤ 800 words.\n\n"
            f"```\n{content[:500_000]}\n```"
        )

        response = await client.generate_content_async(prompt)
        return response.text if hasattr(response, 'text') else str(response)

    async def is_available(self) -> bool:
        """Check if Gemini Flash is configured and available."""
        return bool(self.api_key)

    @staticmethod
    def should_use_gemini(file_size_bytes: int) -> bool:
        """
        Decision helper: should we use Gemini Flash for this file?
        Only for files >50KB where the 1M context window matters.
        """
        return file_size_bytes > 50 * 1024  # 50KB threshold
