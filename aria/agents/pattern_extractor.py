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
        intake_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Extract patterns from all research findings.

        Args:
            github_findings: List of GitHubResearchAgent outputs
            web_findings: List of WebResearchAgent outputs
            intake_result: Full intake output for domain context

        Returns:
            Structured patterns dict
        """
        intake_result = intake_result or {}
        summary = self._build_findings_summary(github_findings, web_findings)

        raw_idea = intake_result.get("raw_idea", "")
        ideal_outcome = intake_result.get("ideal_outcome", "")

        user_content = (
            f"IDEA (what the user wants to build):\n{raw_idea}\n\n"
            f"IDEAL OUTCOME:\n{ideal_outcome}\n\n"
            f"RESEARCH FINDINGS:\n{summary}"
        )

        if self.offline:
            from tools.ollama_client import OllamaClient
            client = OllamaClient(use_deep=hardware.use_deep_model)
            messages = [
                {"role": "system", "content": self._load_system_prompt()},
                {"role": "user", "content": user_content},
            ]
            return await client.generate(messages)

        deepseek = DeepSeekClient()
        messages = [
            {"role": "system", "content": self._load_system_prompt()},
            {"role": "user", "content": user_content},
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

            # Deep dive results (full code analysis — highest quality signal)
            deep_dives = gf.get("deep_dive_results", [])
            if deep_dives:
                lines.append("**Deep-dived repos:**")
                for dr in deep_dives:
                    analysis = dr.get("analysis", {})
                    lines.append(f"- {dr.get('full_name', '')} (score: {dr.get('relevance_score', 0)}, stars: {dr.get('stars', 0)})")
                    if analysis.get("architecture"):
                        lines.append(f"  Architecture: {analysis['architecture'][:300]}")
                    if analysis.get("key_pattern"):
                        lines.append(f"  Key pattern: {analysis['key_pattern'][:200]}")
                    if analysis.get("dependencies"):
                        lines.append(f"  Dependencies: {', '.join(analysis['dependencies'][:6])}")
                    if analysis.get("gotchas"):
                        lines.append(f"  Gotchas: {'; '.join(analysis['gotchas'][:3])}")
                    if analysis.get("code_snippet"):
                        lines.append(f"  Code snippet:\n```\n{analysis['code_snippet'][:400]}\n```")

            # Top scored repos (surface-level signal — useful even without deep dive)
            all_repos = gf.get("all_repos", [])
            top_repos = [r for r in all_repos if r.get("relevance_score", 0) >= 6][:5]
            if top_repos:
                lines.append("**Top relevant repos (scored ≥6):**")
                for r in top_repos:
                    lines.append(
                        f"- {r['full_name']} "
                        f"(score: {r.get('relevance_score', 0)}, "
                        f"stars: {r.get('stargazers_count', 0)}, "
                        f"lang: {r.get('language', '?')})"
                    )
                    if r.get("relevance_reason"):
                        lines.append(f"  Why relevant: {r['relevance_reason'][:200]}")
            elif not deep_dives:
                lines.append("(No sufficiently relevant repos found for this sub-problem)")

            lines.append("")

        lines.append("## Web Research Findings\n")
        for wf in web_findings:
            sp_title = wf.get("sub_problem_title", "")
            analysis = wf.get("analysis", {})
            lines.append(f"### {sp_title}")
            insights = analysis.get("key_insights", [])
            for insight in insights[:5]:
                lines.append(f"- {insight}")
            libs = analysis.get("recommended_libraries", [])
            if libs:
                lines.append(f"Recommended libs: {', '.join(libs[:5])}")
            lines.append("")

        return "\n".join(lines)

    def _load_system_prompt(self) -> str:
        if PROMPT_PATH.exists():
            return PROMPT_PATH.read_text(encoding="utf-8")
        return self._default_prompt()

    @staticmethod
    def _default_prompt() -> str:
        return """You are ARIA Pattern Extractor — an expert at identifying reusable code patterns.

Return EXACTLY this JSON structure. Every item must use "name"+"description" keys (NOT "issue", "solution", "performance_considerations", etc.):

{"architectural_patterns":[{"name":"...","description":"..."}],"libraries_to_use":[{"library":"...","version":"...","reason":"...","source_repo":"..."}],"repos_to_fork":[{"repo":"owner/repo","reason":"..."}],"anti_patterns":[{"name":"...","description":"..."}],"gotchas":[{"name":"...","description":"..."}],"performance":[{"name":"...","description":"..."}],"security":[{"name":"...","description":"..."}]}

Return ONLY valid JSON. No markdown fences."""
