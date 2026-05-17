"""
ARIA v2 — Agent 6: Synthesis Agent
Produces the master research brief — maintaining the ideal outcome throughout.

Provider: NVIDIA NIM (llama-3.1-405b) → SambaNova fallback

Key feature: Ideal outcome injection — every section prompt contains the
ideal outcome to prevent context amnesia during long synthesis.
"""

from pathlib import Path
from typing import Any

from tools.groq_client import GroqClient
from tools.nvidia_client import NvidiaClient
from tools.sambanova_client import SambaNovaClient
from tools.zhipu_client import ZhipuClient

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "synthesize_system.txt"


class SynthesizerAgent:
    """
    Agent 6 — Synthesizer.

    Takes all findings (GitHub + web + patterns) and produces the
    master research brief as a structured markdown document.

    The ideal outcome from intake is injected into EVERY section prompt
    to prevent context amnesia.
    """

    def __init__(self):
        self.nvidia = NvidiaClient()
        self.sambanova = SambaNovaClient()
        self.groq = GroqClient()
        self.zhipu = ZhipuClient()

    async def run(
        self,
        intake_result: dict[str, Any],
        decomposition_result: list[dict[str, Any]],
        github_findings: list[dict[str, Any]],
        web_findings: list[dict[str, Any]],
        patterns: dict[str, Any],
    ) -> str:
        """
        Produce the master research brief.

        Args:
            intake_result: From IntakeAgent
            decomposition_result: From DecomposerAgent
            github_findings: From GitHubResearchAgent (one per sub-problem)
            web_findings: From WebResearchAgent (one per sub-problem)
            patterns: From PatternExtractorAgent

        Returns:
            Markdown research brief content
        """
        ideal_outcome = intake_result.get("ideal_outcome", "")

        # Build the brief in sections, each injected with ideal outcome
        sections = []

        # Section 1: Header + Executive Summary
        sections.append(await self._generate_section(
            "header",
            f"Generate the header and executive summary for a research brief.\n\n"
            f"Original idea: {intake_result.get('raw_idea', '')}\n"
            f"Domain: {intake_result.get('domain', [])}\n"
            f"Complexity: {intake_result.get('complexity_estimate', 'medium')}",
            ideal_outcome,
        ))

        # Section 2: Problem Decomposition
        sp_summaries = "\n".join(
            f"- **{sp.get('title', '')}**: {sp.get('description', '')}"
            for sp in decomposition_result
        )
        sections.append(await self._generate_section(
            "decomposition",
            f"Summarise the problem decomposition:\n\n{sp_summaries}",
            ideal_outcome,
        ))

        # Section 3: Findings per sub-problem
        for i, gf in enumerate(github_findings):
            sp_id = gf.get("sub_problem_id", f"SP-{i+1}")
            sp_title = gf.get("sub_problem_title", "")

            # Repo table
            repo_lines = []
            for dr in gf.get("deep_dive_results", [])[:3]:
                analysis = dr.get("analysis", {})
                repo_lines.append(
                    f"- **{dr.get('full_name', '')}** ({dr.get('stars', 0)}⭐, "
                    f"score: {dr.get('relevance_score', 0)}/10)\n"
                    f"  - Architecture: {analysis.get('architecture', 'N/A')}\n"
                    f"  - Key pattern: {analysis.get('key_pattern', 'N/A')}\n"
                    f"  - Fork worth it: {'✅' if analysis.get('fork_worth_it') else '❌'}"
                )

            web_insights = ""
            if i < len(web_findings):
                wf_analysis = web_findings[i].get("analysis", {})
                insights = wf_analysis.get("key_insights", [])
                if insights:
                    web_insights = "\n".join(f"- {ins}" for ins in insights[:3])

            sections.append(await self._generate_section(
                f"sp_{sp_id}",
                f"Write findings for sub-problem {sp_id}: {sp_title}\n\n"
                f"Top repos:\n{chr(10).join(repo_lines)}\n\n"
                f"Web insights:\n{web_insights}",
                ideal_outcome,
            ))

        # Section 4: Synthesised Architecture
        sections.append(await self._generate_section(
            "architecture",
            f"Write the synthesised architecture decision based on these patterns:\n\n"
            f"Architectural patterns: {patterns.get('architectural_patterns', [])}\n"
            f"Libraries: {[lib.get('name', '') for lib in patterns.get('libraries_to_use', [])]}\n"
            f"Anti-patterns: {patterns.get('anti_patterns', [])}",
            ideal_outcome,
        ))

        # Section 5: Build Order + Risks
        sections.append(await self._generate_section(
            "build_order",
            "Generate the build order (Phase 1/2/3), risks, and unknowns section.\n\n"
            f"Gotchas: {patterns.get('gotchas', [])}\n"
            f"Performance: {patterns.get('performance_considerations', [])}\n"
            f"Security: {patterns.get('security_considerations', [])}",
            ideal_outcome,
        ))

        # Assemble the final brief
        brief = self._assemble_brief(intake_result, sections)
        return brief

    async def _generate_section(
        self,
        section_name: str,
        content: str,
        ideal_outcome: str,
    ) -> str:
        """Generate a single section of the brief with ideal outcome injection."""
        messages = [
            {
                "role": "system",
                "content": self._load_system_prompt(),
            },
            {
                "role": "user",
                "content": (
                    f"CRITICAL CONTEXT — DO NOT LOSE THIS:\n"
                    f"The ideal outcome is: \"{ideal_outcome}\"\n"
                    f"Every recommendation you make MUST serve this outcome.\n\n"
                    f"Section: {section_name}\n\n"
                    f"Content to synthesise:\n{content}\n\n"
                    "Write this section in clear Markdown. Be specific, actionable, "
                    "and tie everything back to the ideal outcome."
                ),
            },
        ]

        clients = [
            ("NVIDIA", self.nvidia),
            ("SambaNova", self.sambanova),
            ("Groq", self.groq),
            ("Zhipu", self.zhipu),
        ]
        for name, client in clients:
            try:
                return await client.generate_text(messages)
            except Exception:
                continue
        return f"*[Synthesis for '{section_name}' failed: all 4 providers exhausted]*"

    def _assemble_brief(
        self,
        intake_result: dict[str, Any],
        sections: list[str],
    ) -> str:
        """Assemble all sections into the final master research brief."""
        from datetime import datetime

        brief = f"""# ARIA Research Brief

**Idea:** {intake_result.get('raw_idea', '')}
**Ideal Outcome:** {intake_result.get('ideal_outcome', '')}
**Research Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Domain:** {', '.join(intake_result.get('domain', []))}
**Complexity:** {intake_result.get('complexity_estimate', 'medium')}

{"─" * 60}

"""

        section_titles = [
            "## Executive Summary",
            "## Problem Decomposition",
            "",
            "## Synthesis",
            "## Build Order & Risks",
        ]

        for i, (title, content) in enumerate(zip(section_titles, sections)):
            if title:
                brief += f"\n{title}\n\n"
            brief += content.strip() + "\n"

        brief += f"""
{"─" * 60}

## Ready to Build

**Feed this file to Claude Code to start Sprint 1.**

*Generated by ARIA v2 — Agentic Research Intelligence Architecture*
*Author: chrisdev1187 — Nagasubramanian Methodology*
"""

        return brief

    def _load_system_prompt(self) -> str:
        if PROMPT_PATH.exists():
            return PROMPT_PATH.read_text(encoding="utf-8")
        return self._default_prompt()

    @staticmethod
    def _default_prompt() -> str:
        return """You are ARIA Synthesis Agent — you produce master research briefs.

Given research findings, you write comprehensive, actionable briefs that:
1. Always reference the ideal outcome (injected at the top of every section)
2. Recommend specific repos, patterns, and architecture decisions
3. Include code snippets from real repos
4. Provide a clear build order
5. Flag risks and unknowns
6. Are written in Markdown

Every section you write must trace back to the ideal outcome.
If a finding doesn't serve the ideal outcome, exclude it.

Write in clear, actionable language. Be opinionated — recommend the best approach, not all approaches."""
