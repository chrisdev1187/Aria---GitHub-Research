"""
ARIA v2 — Agent 2: Decomposition Agent
Breaks the problem into 3-7 specific, searchable technical sub-problems.

Provider: Groq (llama-3.3-70b) — structured JSON output critical
Fallback chain: Groq → Cerebras → SiliconFlow → Zhipu

Output Schema (decomposition.json):
[
    {
        "id": "SP-1",
        "title": "...",
        "description": "...",
        "why_critical": "...",
        "github_search_queries": ["...", "..."],
        "npm_search_terms": ["..."],
        "pypi_search_terms": ["..."],
        "stackoverflow_tags": ["...", "..."],
        "ideal_outcome_relevance": "..."
    }
]
"""

from pathlib import Path
from typing import Any

from config import hardware
from provider_pool import SchemaValidationFailed
from tools.groq_client import GroqClient

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "decompose_system.txt"


class DecomposerAgent:
    """
    Agent 2 — Decomposer.

    Takes the intake analysis and breaks it into 3-7 specific, searchable
    technical sub-problems. Each sub-problem comes with GitHub search queries,
    npm/PyPI search terms, and Stack Overflow tags.

    Built-in fallback: Groq → Cerebras → SiliconFlow → Zhipu
    Automatically cascades when primary provider is exhausted.
    """

    def __init__(self, offline: bool = False):
        self.offline = offline

    async def run(self, intake_result: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Decompose the idea into technical sub-problems.
        Falls through Groq → Cerebras → SiliconFlow → Zhipu on error.

        Args:
            intake_result: Output from IntakeAgent.run()

        Returns:
            List of sub-problem dicts (decomposition.json)
        """
        system_prompt = self._load_system_prompt()

        complexity = intake_result.get("complexity_estimate", "medium")
        lang = intake_result.get("primary_language", "")
        sp_range = {"low": "3-4", "medium": "5-7", "high": "8-12"}.get(complexity, "5-7")
        core_problems = intake_result.get("core_problems", [])
        numbered_cores = "\n".join(f"  {i+1}. {p}" for i, p in enumerate(core_problems))

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"Decompose this idea into sub-problems.\n\n"
                    f"Idea: {intake_result.get('raw_idea', '')}\n"
                    f"Ideal Outcome: {intake_result.get('ideal_outcome', '')}\n"
                    f"Domain: {intake_result.get('domain', [])}\n"
                    f"Primary Language: {lang}\n"
                    f"Complexity: {complexity} → generate {sp_range} sub-problems\n\n"
                    f"Core Problems (USE AS SEEDS — every core problem must map to at least one SP):\n{numbered_cores}\n\n"
                    "BEFORE writing github_search_queries for each SP:\n"
                    "  Ask: 'What Python library or framework would a developer IMPORT to implement this?'\n"
                    "  Put THOSE library/framework names in the queries — not the feature description.\n"
                    "  BAD: 'python idea decomposition tool'  GOOD: 'python asyncio pydantic structured output llm'"
                ),
            },
        ]

        if self.offline:
            from tools.ollama_client import OllamaClient
            client = OllamaClient(use_deep=hardware.use_deep_model)
            result = await client.generate(messages)
        else:
            # GroqClient has built-in fallback chain (Groq → Cerebras → SiliconFlow → Zhipu)
            groq = GroqClient()
            try:
                result = await groq.generate(messages)
            except Exception as e:
                raise SchemaValidationFailed(
                    f"Decomposer failed — all providers exhausted: {e}"
                )

        # The result should be a dict with a "sub_problems" key,
        # or a list directly, or a dict with numeric keys
        sub_problems = result.get("sub_problems", result.get("decomposition", result))

        if isinstance(sub_problems, dict):
            # Convert dict to list
            return list(sub_problems.values())

        if isinstance(sub_problems, list):
            return sub_problems

        raise SchemaValidationFailed(
            f"Decomposer returned unexpected format: {type(sub_problems)}"
        )

    def _load_system_prompt(self) -> str:
        if PROMPT_PATH.exists():
            return PROMPT_PATH.read_text(encoding="utf-8")
        return self._default_prompt()

    @staticmethod
    def _default_prompt() -> str:
        return """You are ARIA Decomposition Agent — a technical problem breakdown specialist.

Your job is to decompose a software idea into 3-7 specific, searchable technical sub-problems.
Each sub-problem must be:
- Concrete enough to search GitHub for
- Small enough to be solved independently
- Critical to the ideal outcome

For each sub-problem, provide:
- id: "SP-1", "SP-2", etc.
- title: Short, descriptive name
- description: 2-3 sentence explanation
- why_critical: Why this matters for the ideal outcome
- github_search_queries: 2-3 search queries to find relevant repos
- npm_search_terms: Related npm packages (empty array if not web/JS)
- pypi_search_terms: Related PyPI packages (empty array if not Python)
- stackoverflow_tags: Relevant Stack Overflow tags
- ideal_outcome_relevance: How this connects back to the ideal outcome

Return as JSON: { "sub_problems": [ ... ] }

Return ONLY valid JSON. No markdown fences."""
