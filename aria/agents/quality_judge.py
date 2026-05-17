"""
ARIA v2 — Agent 7: Quality Judge
Scores the master brief, detects gaps, and decides whether to re-research.

Provider: Groq (llama-3.3-70b) — fast, consistent scoring
Fallback chain: Groq → Cerebras → SiliconFlow → Zhipu

Max 2 re-research loops. If still < 7/10, deliver with gap annotations.

Scoring dimensions (0-10):
- Addresses the ideal outcome?
- All sub-problems covered?
- Architecture actionable?
- Specific repos/code provided?
"""

from pathlib import Path
from typing import Any, Optional

from provider_pool import SchemaValidationFailed
from tools.groq_client import GroqClient

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "judge_system.txt"


class QualityJudgeAgent:
    """
    Agent 7 — Quality Judge.

    Evaluates the research brief for quality and completeness, identifies
    gaps, and recommends whether to re-research or ship.

    Built-in fallback: Groq → Cerebras → SiliconFlow → Zhipu
    Max re-research loops: 2 (configurable via research.max_research_loops)
    """

    def __init__(self):
        self.groq = GroqClient()
        self.loops_used = 0
        self.max_loops = 2

    async def run(
        self,
        brief: str,
        intake_result: dict[str, Any],
        previous_judgements: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """
        Judge the quality of the research brief.
        Falls through Groq → Cerebras → SiliconFlow → Zhipu on error.

        Args:
            brief: The full research brief markdown
            intake_result: Original intake (for ideal outcome reference)
            previous_judgements: Previous judgement results for re-research context

        Returns:
            Quality judgement dict with scores and re-research directives
        """
        previous_context = ""
        if previous_judgements:
            prev = previous_judgements[-1]
            gaps = prev.get("gaps", [])
            previous_context = (
                f"Previous score: {prev.get('overall_score', 0)}/10\n"
                f"Gaps to address: {', '.join(gaps[:5])}\n"
                f"Re-research needed: {prev.get('verdict') == 'RE_RESEARCH'}\n"
            )

        messages = [
            {
                "role": "system",
                "content": self._load_system_prompt(),
            },
            {
                "role": "user",
                "content": (
                    f"Ideal outcome: {intake_result.get('ideal_outcome', '')}\n"
                    f"Original idea: {intake_result.get('raw_idea', '')}\n\n"
                    f"{previous_context}"
                    f"Brief to judge:\n\n{brief[:15000]}\n\n"
                    "Score each dimension 0-10 and provide a verdict."
                ),
            },
        ]

        try:
            result = await self.groq.generate(messages)
        except Exception as e:
            raise SchemaValidationFailed(
                f"Quality Judge failed — all providers exhausted: {e}"
            )
        self.loops_used += 1

        # Ensure consistent structure
        return {
            "overall_score": result.get("overall_score", 5),
            "dimensions": {
                "addresses_ideal_outcome": result.get("addresses_ideal_outcome", 5),
                "sub_problems_covered": result.get("sub_problems_covered", 5),
                "architecture_actionable": result.get("architecture_actionable", 5),
                "specific_repos_provided": result.get("specific_repos_provided", 5),
            },
            "gaps": result.get("gaps", []),
            "strengths": result.get("strengths", []),
            "verdict": result.get("verdict", "NEEDS_GAPS_FILLED"),
            "re_research_directives": result.get("re_research_directives", []),
            "loops_used": self.loops_used,
            "max_loops": self.max_loops,
        }

    @property
    def should_continue_research(self) -> bool:
        """Whether we should do another re-research loop."""
        return self.loops_used < self.max_loops

    def _load_system_prompt(self) -> str:
        if PROMPT_PATH.exists():
            return PROMPT_PATH.read_text(encoding="utf-8")
        return self._default_prompt()

    @staticmethod
    def _default_prompt() -> str:
        return """You are ARIA Quality Judge — a strict evaluator of technical research briefs.

Score the brief 0-10 on each dimension:
1. addresses_ideal_outcome: Does every section serve the ideal outcome?
2. sub_problems_covered: Are all decomposed sub-problems addressed?
3. architecture_actionable: Can someone build from this description?
4. specific_repos_provided: Are there real repos with code to start from?

Then provide:
- overall_score: 0-10
- gaps: Specific missing pieces
- strengths: What's done well
- verdict: "SHIP" (≥8), "NEEDS_GAPS_FILLED" (5-7), "RE_RESEARCH" (<5)
- re_research_directives: If RE_RESEARCH, what to research further

Return JSON. Return ONLY valid JSON. No markdown fences."""
