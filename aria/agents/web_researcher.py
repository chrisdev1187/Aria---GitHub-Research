"""
ARIA v2 — Agent 4: Web Research Agent
Finds technical articles, tutorials, pattern documentation for ONE sub-problem.

Provider: SiliconFlow (Qwen2.5-72B) — general comprehension
Fallback: Zhipu → Groq

Tools: DuckDuckGo search, Jina Reader for content extraction
"""

from pathlib import Path
from typing import Any

from tools.siliconflow_client import SiliconFlowClient
from tools.ddg_search import DDGSearch
from tools.jina_reader import JinaReader
from config import research


PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "web_research.txt"


class WebResearchAgent:
    """
    Agent 4 — Web Researcher.

    For one sub-problem, finds:
    - Technical blog posts and articles
    - Official documentation
    - Stack Overflow discussions
    - Pattern guides and tutorials
    """

    def __init__(self):
        self.search = DDGSearch()
        self.jina = JinaReader()
        self.llm = SiliconFlowClient()

    async def run(self, sub_problem: dict[str, Any]) -> dict[str, Any]:
        """
        Research a single sub-problem on the web.

        Args:
            sub_problem: Single sub-problem from decomposition

        Returns:
            Web findings with articles, tutorials, and key insights
        """
        title = sub_problem.get("title", "")
        tags = sub_problem.get("stackoverflow_tags", [])

        # Search queries
        queries = [
            f"{title} tutorial implementation guide",
            f"{title} best practices architecture",
            f"{title} example code",
        ]
        if tags:
            queries.append(f"{' '.join(tags[:3])} {title}")

        # Search the web
        all_results = []
        for query in queries[:3]:
            results = await self.search.search_technical(query, max_results=5)
            all_results.extend(results)

        # Deduplicate by URL
        seen_urls = set()
        unique_results = []
        for r in all_results:
            url = r.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(r)

        # Filter for technical content
        technical_results = self._filter_technical(unique_results)

        # Fetch content from top results
        enriched_results = []
        for result in technical_results[:5]:
            url = result.get("url", "")
            content = await self.jina.read_url(url, max_chars=10000) if url else None
            enriched_results.append({**result, "content": content or ""})

        # Analyse findings with LLM
        findings = await self._analyse_findings(enriched_results, sub_problem)

        return {
            "sub_problem_id": sub_problem.get("id", ""),
            "sub_problem_title": title,
            "results_count": len(technical_results),
            "results": enriched_results[:5],
            "analysis": findings,
        }

    def _filter_technical(self, results: list[dict[str, str]]) -> list[dict[str, str]]:
        """Filter for technical content with code snippets or architecture."""
        technical_domains = [
            "github.com", "stackoverflow.com", "dev.to",
            "medium.com", "docs.", "official", "tutorial",
            "blog.", "arxiv.org", "paper",
        ]

        filtered = []
        for r in results:
            url = r.get("url", "").lower()
            snippet = r.get("snippet", "").lower()

            # Must be technical or contain code
            is_technical = any(d in url for d in technical_domains)
            has_code = any(m in snippet for m in ["```", "code", "function", "api", "npm", "pip"])

            if is_technical or has_code:
                filtered.append(r)

        return filtered[:10]

    async def _analyse_findings(
        self,
        results: list[dict[str, Any]],
        sub_problem: dict[str, Any],
    ) -> dict[str, Any]:
        """Analyse web findings for patterns and insights."""
        if not results:
            return {"key_insights": [], "recommended_approaches": [], "articles_to_read": []}

        snippets = "\n".join(
            f"- [{r.get('title', '')}]({r.get('url', '')}): {r.get('snippet', '')[:200]}"
            for r in results[:5]
        )

        messages = [
            {
                "role": "system",
                "content": "Analyse these web research findings for a technical sub-problem.",
            },
            {
                "role": "user",
                "content": (
                    f"Sub-problem: {sub_problem.get('title', '')}\n"
                    f"Description: {sub_problem.get('description', '')}\n\n"
                    f"Findings:\n{snippets}\n\n"
                    "Return JSON: {\n"
                    '  "key_insights": ["..."],\n'
                    '  "recommended_approaches": ["..."],\n'
                    '  "articles_to_read": [{"title": "...", "url": "...", "why": "..."}],\n'
                    '  "common_pitfalls": ["..."]\n'
                    "}"
                ),
            },
        ]

        try:
            return await self.llm.generate(messages)
        except Exception:
            return {"key_insights": [], "recommended_approaches": [], "articles_to_read": [], "common_pitfalls": []}
