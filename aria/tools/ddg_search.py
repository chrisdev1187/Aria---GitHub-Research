"""
ARIA v2 — DuckDuckGo Search Client
Web search for the web research layer (Agent 4).

No API key needed. Rate limited to 1 request per 2 seconds.
Used to find: technical articles, tutorials, pattern documentation, Stack Overflow threads.
"""

import asyncio
from typing import Optional

from config import RATE_LIMITS

DDG_DELAY = RATE_LIMITS["ddg"]["delay_s"]


class DDGSearch:
    """
    DuckDuckGo search client.

    Uses the ddgs package (renamed from duckduckgo_search).
    Rate limited to 2s between requests.
    """

    def __init__(self):
        self._last_request_time = 0.0

    async def search(self, query: str, max_results: int = 10) -> list[dict[str, str]]:
        """
        Search DuckDuckGo and return results.

        Args:
            query: Search query
            max_results: Max results to return (default 10)

        Returns:
            List of dicts with: title, url, snippet, source
        """
        # Rate limiting
        loop = asyncio.get_running_loop()
        now = loop.time()
        elapsed = now - self._last_request_time
        if elapsed < DDG_DELAY:
            await asyncio.sleep(DDG_DELAY - elapsed)

        from ddgs import DDGS

        try:
            # Run synchronous DDGS call in thread pool
            results = await loop.run_in_executor(
                None,
                lambda: list(DDGS().text(query, max_results=max_results)),
            )

            self._last_request_time = loop.time()

            formatted = []
            for r in results:
                formatted.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                    "source": "duckduckgo",
                })
            return formatted

        except Exception as e:
            return [
                {
                    "title": f"Search failed: {e}",
                    "url": "",
                    "snippet": "",
                    "source": "error",
                }
            ]

    async def search_technical(
        self,
        query: str,
        max_results: int = 10,
    ) -> list[dict[str, str]]:
        """
        Search with technical documentation bias.
        Will prefer: GitHub, dev.to, Stack Overflow, official docs.
        """
        return await self.search(query, max_results=max_results)

    async def search_stackoverflow(self, query: str, max_results: int = 5) -> list[dict[str, str]]:
        """Search specifically for Stack Overflow results."""
        return await self.search(f"site:stackoverflow.com {query}", max_results=max_results)
