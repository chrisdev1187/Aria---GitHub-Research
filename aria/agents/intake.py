"""
ARIA v2 — Agent 1: Intake Agent
Understands the raw idea, defines the ideal outcome, classifies the domain,
and identifies core problems.

Provider: Groq (llama-3.3-70b-versatile) — fast, reliable structured output
Fallback: Cerebras

Output Schema (intake.json):
{
    "raw_idea": "...",
    "ideal_outcome": "...",
    "domain": ["web", "cli", "data", "mobile", "ml", "infra"],
    "primary_language": "python|js|rust|etc|unknown",
    "complexity_estimate": "low|medium|high",
    "core_problems": ["...", "..."]
}
"""

from pathlib import Path
from typing import Any

from config import AGENT_FALLBACK_MAP, AGENT_PROVIDER_MAP, hardware
from provider_pool import SchemaValidationFailed
from tools.groq_client import GroqClient

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "intake_system.txt"


class IntakeAgent:
    """
    Agent 1 — Intake.

    Takes a raw natural language idea and produces:
    - A clear ideal outcome statement
    - Domain classification
    - Core problems
    - Complexity estimate
    """

    def __init__(self, offline: bool = False):
        self.offline = offline
        self.primary_provider = AGENT_PROVIDER_MAP["intake"]
        self.fallback_provider = AGENT_FALLBACK_MAP["intake"]

    async def run(self, idea: str) -> dict[str, Any]:
        """
        Process the raw idea through the Intake agent.

        Uses GroqClient with built-in fallback chain:
        Groq → Cerebras → SiliconFlow → Zhipu

        Args:
            idea: Raw natural language idea

        Returns:
            Structured intake.json dict

        Raises:
            SchemaValidationFailed: After all providers exhausted
        """
        system_prompt = self._load_system_prompt()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Analyse this idea:\n\n{idea}"},
        ]

        if self.offline:
            from tools.ollama_client import OllamaClient
            client = OllamaClient(use_deep=hardware.use_deep_model)
            return await client.generate(messages)

        try:
            groq = GroqClient()
            return await groq.generate(messages)
        except Exception as e:
            raise SchemaValidationFailed(
                f"Intake failed — all providers exhausted: {e}"
            )

    def _load_system_prompt(self) -> str:
        """Load the intake system prompt from file."""
        if PROMPT_PATH.exists():
            return PROMPT_PATH.read_text(encoding="utf-8")
        return self._default_prompt()

    @staticmethod
    def _default_prompt() -> str:
        """Fallback system prompt if file is missing."""
        return """You are ARIA Intake Agent — a system that analyses technical ideas.

Your job is to:
1. Understand what the user wants to build
2. Define the ideal outcome (what success looks like)
3. Classify the domain (web, cli, data, mobile, ml, infra)
4. Identify the primary language (python, js, rust, etc.)
5. Estimate complexity (low/medium/high)
6. Identify 2-5 core technical problems to solve

Return your analysis as a JSON object with these fields:
- raw_idea: the original idea
- ideal_outcome: clear success criteria
- domain: array of domain tags
- primary_language: the most likely language
- complexity_estimate: "low", "medium", or "high"
- core_problems: array of specific technical challenges

Return ONLY valid JSON. No markdown fences. No explanation."""
