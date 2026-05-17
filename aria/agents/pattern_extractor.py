"""
ARIA v2 — Agent 5: Pattern Extractor
Across ALL findings, identifies reusable patterns, architectural decisions, gotchas,
and anti-patterns.

Provider: DeepSeek (code reasoning) → Ollama Qwen3B (offline/privacy mode)
Fallback: SiliconFlow

⚠️  Ollama lock: Sequential only (RAM constraint on 8GB system).
"""

from pathlib import Path
from typing import Any

from config import hardware
from provider_pool import SchemaValidationFailed
from tools.deepseek_client import DeepSeekClient

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "pattern_extract.txt"


class PatternExtractorAgent:
    """
    Agent 5 — Pattern Extractor.

    Takes all GitHub and web research findings and extracts:
    - Architectural patterns
    - Libraries to use (with justification)
    - Repos to fork (with what to change)
    - Anti-patterns to avoid
    - Gotchas and performance considerations
    """

    def __init__(self, offline: bool = False):
        self.offline = offline

    async def run(
        self,
        github_findings: list[dict[str, Any]],
        web_findings: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Extract patterns from all research findings.

        Args:
            github_findings: List of GitHubResearchAgent outputs
            web_findings: List of WebResearchAgent outputs

        Returns:
            Structured patterns dict
        """
        # Prepare a condensed summary of all findings
        summary = self._build_findings_summary(github_findings, web_findings)

        if self.offline:
            from tools.ollama_client import OllamaClient
            client = OllamaClient(use_deep=hardware.use_deep_model)
            messages = [
                {
                    "role": "system",
                    "content": self._load_system_prompt(),
                },
                {
                    "role": "user",
                    "content": f"Extract patterns from these research findings:\n\n{summary}",
                },
            ]
            return await client.generate(messages)

        deepseek = DeepSeekClient()
        messages = [
            {
                "role": "system",
                "content": self._load_system_prompt(),
            },
            {
                "role": "user",
                "content": f"Extract patterns from these research findings:\n\n{summary}",
            },
        ]

        try:
            return await deepseek.generate(messages)
        except Exception as e:
            raise SchemaValidationFailed(f"Pattern extraction failed: {e}")

    def _build_findings_summary(
        self,
        github_findings: list[dict[str, Any]],
        web_findings: list[dict[str, Any]],
    ) -> str:
        """Build a condensed summary of all findings for the LLM."""
        lines = ["## GitHub Research Findings\n"]

        for gf in github_findings:
            sp_id = gf.get("sub_problem_id", "")
            sp_title = gf.get("sub_problem_title", "")
            lines.append(f"### {sp_id}: {sp_title}")
            lines.append(f"Repos found: {gf.get('repos_found', 0)}")

            for dr in gf.get("deep_dive_results", []):
                analysis = dr.get("analysis", {})
                lines.append(f"- {dr.get('full_name', '')} (score: {dr.get('relevance_score', 0)})")
                lines.append(f"  Architecture: {analysis.get('architecture', '')[:300]}")
                lines.append(f"  Key pattern: {analysis.get('key_pattern', '')[:200]}")

            patterns = gf.get("patterns", {})
            if patterns.get("architectural_patterns"):
                lines.append(f"  Patterns: {', '.join(patterns['architectural_patterns'][:3])}")
            lines.append("")

        lines.append("## Web Research Findings\n")
        for wf in web_findings:
            sp_title = wf.get("sub_problem_title", "")
            analysis = wf.get("analysis", {})
            lines.append(f"### {sp_title}")
            insights = analysis.get("key_insights", [])
            for insight in insights[:3]:
                lines.append(f"- {insight}")
            lines.append("")

        return "\n".join(lines)

    def _load_system_prompt(self) -> str:
        if PROMPT_PATH.exists():
            return PROMPT_PATH.read_text(encoding="utf-8")
        return self._default_prompt()

    @staticmethod
    def _default_prompt() -> str:
        return """You are ARIA Pattern Extractor — an expert at identifying reusable code patterns.

Given research findings from multiple sub-problems, you extract:

1. architectural_patterns: Overall system architecture approaches
2. libraries_to_use: Specific libraries with reasons and source repos
3. repos_to_fork: Repos worth forking with what to change
4. anti_patterns: Things that look good but cause problems
5. gotchas: Surprising issues worth knowing
6. performance_considerations: Performance implications
7. security_considerations: Security implications

Return JSON. Return ONLY valid JSON. No markdown fences."""
