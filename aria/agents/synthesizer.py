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
        raw_idea = intake_result.get("raw_idea", "")
        ideal_outcome = intake_result.get("ideal_outcome", "")

        # (title, content) pairs — assembled in order, no fixed-length zip
        named_sections: list[tuple[str, str]] = []

        # Section 1: Executive Summary
        named_sections.append((
            "## Executive Summary",
            await self._generate_section(
                "header",
                f"Original idea: {raw_idea}\n"
                f"Domain: {intake_result.get('domain', [])}\n"
                f"Complexity: {intake_result.get('complexity_estimate', 'medium')}\n\n"
                "Write the executive summary. State the problem, the recommended architecture "
                "approach (inferred from the ideal outcome), and the key tools found in research.",
                raw_idea, ideal_outcome,
            )
        ))

        # Section 2: Problem Decomposition
        sp_summaries = "\n".join(
            f"- **{sp.get('title', '')}**: {sp.get('description', '')}"
            for sp in decomposition_result
        )
        named_sections.append((
            "## Problem Decomposition",
            await self._generate_section(
                "decomposition",
                f"Summarise the problem decomposition:\n\n{sp_summaries}",
                raw_idea, ideal_outcome,
            )
        ))

        # Build web findings lookup by sub_problem_id (index fallback for old checkpoints)
        web_by_id: dict[str, dict] = {}
        for idx, wf in enumerate(web_findings):
            if isinstance(wf, dict):
                key = wf.get("sub_problem_id") or f"SP-{idx+1}"
                web_by_id[key] = wf
                web_by_id[str(idx)] = wf  # keep index key as fallback

        # Section 3: Findings per sub-problem (one section each)
        for i, gf in enumerate(github_findings):
            sp_id = gf.get("sub_problem_id", f"SP-{i+1}")
            sp_title = gf.get("sub_problem_title", "")

            # Deep dive results first (richest signal)
            repo_lines = []
            for dr in gf.get("deep_dive_results", [])[:3]:
                analysis = dr.get("analysis", {})
                repo_lines.append(
                    f"- **{dr.get('full_name', '')}** ({dr.get('stars', 0)}⭐, "
                    f"score: {dr.get('relevance_score', 0)}/10)\n"
                    f"  - Architecture: {analysis.get('architecture', 'N/A')[:200]}\n"
                    f"  - Key pattern: {analysis.get('key_pattern', 'N/A')[:150]}\n"
                    f"  - Dependencies: {', '.join(analysis.get('dependencies', [])[:5])}\n"
                    f"  - Fork worth it: {'✅' if analysis.get('fork_worth_it') else '❌'}"
                )

            # Fall back to top scored repos when no deep dives
            if not repo_lines:
                top_scored = [r for r in gf.get("all_repos", []) if r.get("relevance_score", 0) >= 6][:3]
                for r in top_scored:
                    repo_lines.append(
                        f"- **{r['full_name']}** ({r.get('stargazers_count', 0)}⭐, "
                        f"score: {r.get('relevance_score', 0)}/10)\n"
                        f"  - Why relevant: {r.get('relevance_reason', 'N/A')[:200]}"
                    )

            web_insights = ""
            wf = web_by_id.get(sp_id) or web_by_id.get(str(i))
            if wf:
                wf_analysis = wf.get("analysis", {})
                insights = wf_analysis.get("key_insights", [])
                if insights:
                    web_insights = "\n".join(f"- {ins}" for ins in insights[:4])

            named_sections.append((
                f"### Sub-problem {sp_id}: {sp_title}",
                await self._generate_section(
                    f"sp_{sp_id}",
                    f"Write findings for sub-problem {sp_id}: {sp_title}\n\n"
                    f"Top repos:\n{chr(10).join(repo_lines) if repo_lines else 'None found'}\n\n"
                    f"Web insights:\n{web_insights if web_insights else 'None'}",
                    raw_idea, ideal_outcome,
                )
            ))

        # Section 4: Synthesised Architecture
        # Fix: use correct key 'library' not 'name'
        lib_names = [lib.get("library", "") for lib in patterns.get("libraries_to_use", [])]
        lib_with_reasons = [
            f"{lib.get('library', '')} ({lib.get('reason', '')[:100]}, from {lib.get('source_repo', '?')})"
            for lib in patterns.get("libraries_to_use", [])
        ]
        named_sections.append((
            "## Synthesised Architecture",
            await self._generate_section(
                "architecture",
                f"Write the synthesised architecture decision based on these extracted patterns.\n\n"
                f"Architectural patterns found: {patterns.get('architectural_patterns', [])}\n"
                f"Libraries (with source repos): {lib_with_reasons}\n"
                f"Repos to fork: {patterns.get('repos_to_fork', [])}\n"
                f"Anti-patterns to avoid: {patterns.get('anti_patterns', [])}",
                raw_idea, ideal_outcome,
            )
        ))

        # Section 5: Build Order + Risks
        # Fix: use correct keys 'performance' and 'security' (not *_considerations)
        named_sections.append((
            "## Build Order & Risks",
            await self._generate_section(
                "build_order",
                "Generate the build order (Phase 1/2/3), risks, and unknowns section.\n\n"
                f"Gotchas: {patterns.get('gotchas', [])}\n"
                f"Performance: {patterns.get('performance', [])}\n"
                f"Security: {patterns.get('security', [])}",
                raw_idea, ideal_outcome,
            )
        ))

        return self._assemble_brief(intake_result, named_sections)

    async def _generate_section(
        self,
        section_name: str,
        content: str,
        raw_idea: str,
        ideal_outcome: str,
    ) -> str:
        """Generate a single section of the brief."""
        messages = [
            {
                "role": "system",
                "content": self._load_system_prompt(),
            },
            {
                "role": "user",
                "content": (
                    f"IDEA (what the user wants to build):\n{raw_idea}\n\n"
                    f"IDEAL OUTCOME:\n{ideal_outcome}\n\n"
                    f"Section: {section_name}\n\n"
                    f"Research content to synthesise:\n{content}\n\n"
                    "Write this section in clear Markdown.\n\n"
                    "HARD CONSTRAINT: You may ONLY recommend tools, libraries, repos, and "
                    "architecture patterns that are explicitly named in the research content above. "
                    "Do not add ANY tool from general knowledge that does not appear in the content. "
                    "If a tool is not in the content, do not mention it — not even as an alternative.\n\n"
                    "Specifically: do NOT mention T5, BERT, Neo4j, PostgreSQL, MySQL, MongoDB, "
                    "Docker, Kubernetes, fine-tuning, or model training UNLESS they appear in "
                    "the research content above."
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
        named_sections: list[tuple[str, str]],
    ) -> str:
        """Assemble all (title, content) pairs into the final master research brief."""
        from datetime import datetime

        brief = (
            f"# ARIA Research Brief\n\n"
            f"**Idea:** {intake_result.get('raw_idea', '')}\n"
            f"**Ideal Outcome:** {intake_result.get('ideal_outcome', '')}\n"
            f"**Research Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"**Domain:** {', '.join(intake_result.get('domain', []))}\n"
            f"**Complexity:** {intake_result.get('complexity_estimate', 'medium')}\n\n"
            f"{'─' * 60}\n\n"
        )

        for title, content in named_sections:
            if title:
                brief += f"\n{title}\n\n"
            brief += content.strip() + "\n"

        brief += (
            f"\n{'─' * 60}\n\n"
            "## Ready to Build\n\n"
            "**Feed this file to Claude Code to start Sprint 1.**\n\n"
            "*Generated by ARIA v2 — Agentic Research Intelligence Architecture*\n"
            "*Author: chrisdev1187 — Nagasubramanian Methodology*\n"
        )

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
