"""
Test: verify the batch scorer now rejects irrelevant repos when given idea context.
Replays the exact repos from the broken SP-1 run against the fixed scorer.
"""
import asyncio
import json
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from agents.github_researcher import GitHubResearchAgent

INTAKE = {
    "raw_idea": (
        "build an AI tool that analyzes system prompts, gives insights to the user, "
        "and connects to a database of leaked system prompts to guide the user to "
        "write a master system prompt"
    ),
    "ideal_outcome": (
        "A tool that analyzes system prompts, extracts insights from a corpus of "
        "leaked system prompts, and guides users in writing high-quality master system prompts "
        "using RAG retrieval over the leaked corpus."
    ),
}

SP = {
    "id": "SP-1",
    "title": "System Prompt Analysis Engine",
    "description": "Parse and analyze system prompts for structural patterns and insights.",
}

# The exact repos that the broken scorer rated 7-8/10 before
REPOS = [
    {"full_name": "sergioburdisso/pyss3",           "description": "Python library for Interpretable ML in Text Classification", "stargazers_count": 348, "language": "Python"},
    {"full_name": "karolzak/support-tickets-classification", "description": "Text classification for support tickets deployed on Azure", "stargazers_count": 167, "language": "Python"},
    {"full_name": "airbnb/artificial-adversary",    "description": "Tool to generate adversarial text examples for ML models", "stargazers_count": 403, "language": "Python"},
    {"full_name": "abusufyanvu/6S191_MIT_DeepLearning", "description": "MIT Introduction to Deep Learning course materials", "stargazers_count": 247, "language": "Jupyter Notebook"},
    {"full_name": "ducnh279/LLMs-for-Text-Classification", "description": "Fine-tuning LLMs for text classification", "stargazers_count": 35, "language": "Jupyter Notebook"},
]

async def main():
    agent = GitHubResearchAgent()
    scored = await agent._batch_score_repos(REPOS, SP, INTAKE)

    print("SCORED REPOS (idea-aware scorer):")
    print(f"{'Repo':<50} {'Score':>6}  Reason")
    print("-" * 100)
    for r in scored:
        print(f"{r['full_name']:<50} {r.get('relevance_score', '?'):>6}  {r.get('relevance_reason', '')[:70]}")

    print("\nVERDICT:")
    generic = [r for r in scored if r.get("relevance_score", 0) >= 6]
    if generic:
        print(f"  FAIL — {len(generic)} repos still scored ≥6 despite being unrelated:")
        for r in generic:
            print(f"    {r['full_name']}: {r.get('relevance_score')}")
    else:
        print(f"  PASS — all irrelevant repos scored <6")

asyncio.run(main())
