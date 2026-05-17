"""
ARIA v2 — Jina Reader Client
URL content extraction for READMEs, documentation, articles.

Jina Reader (r.jina.ai/{url}) extracts clean text content from any URL.
No API key required at basic rate (~1 req/s).

Used by: GitHub Researcher (fetch READMEs) + Web Researcher (fetch articles).
"""

import asyncio
from typing import Optional

import aiohttp

from config import get_jina_key, RATE_LIMITS


JINA_BASE = "https://r.jina.ai"
JINA_DELAY = RATE_LIMITS["jina"]["delay_s"]


class JinaReader:
    """
    Jina Reader client for URL content extraction.

    Converts any URL to clean text content. Used to fetch:
    - GitHub READMEs rendered as HTML
    - Technical documentation pages
    - Blog posts and articles for web research

    Has a 1-second delay between requests at the free tier.
    """

    def __init__(self):
        self.api_key = get_jina_key()
        self.headers = {
            "Accept": "text/plain",
            "User-Agent": "ARIA-v2/1.0",
        }
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"
        self._last_request_time = 0.0

    async def read_url(self, url: str, max_chars: int = 50_000) -> Optional[str]:
        """
        Extract clean text content from a URL.

        Args:
            url: The URL to read
            max_chars: Max characters to return (default 50K)

        Returns:
            Clean text content, or None if fetch failed
        """
        # Rate limiting — at least 1 second between requests
        now = asyncio.get_event_loop().time()
        elapsed = now - self._last_request_time
        if elapsed < JINA_DELAY:
            await asyncio.sleep(JINA_DELAY - elapsed)

        jina_url = f"{JINA_BASE}/{url}"

        async with aiohttp.ClientSession(headers=self.headers) as session:
            try:
                async with session.get(jina_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status != 200:
                        return None
                    content = await response.text()
                    self._last_request_time = asyncio.get_event_loop().time()
                    return content[:max_chars]
            except (aiohttp.ClientError, asyncio.TimeoutError):
                return None

    async def read_github_readme(self, full_name: str) -> Optional[str]:
        """Read a GitHub repo's rendered README via Jina."""
        url = f"https://github.com/{full_name}"
        return await self.read_url(url)

    async def read_documentation(self, docs_url: str) -> Optional[str]:
        """Read a documentation page."""
        return await self.read_url(docs_url)
