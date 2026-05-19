"""
Seeds a pre-built intake + decomposition checkpoint for the ARIA self-research run.
Run this once: python seed_aria_self_run.py
It prints the run_id to pass as resume_id in the UI.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from state import ResearchState, timestamp

IDEA = (
    "build a multi-agent AI research pipeline called ARIA that takes a software idea, "
    "decomposes it into sub-problems, searches GitHub and the web in parallel for relevant "
    "repos and articles, deep-dives into real source code, extracts architectural patterns "
    "and copy-paste-ready libraries, synthesizes a structured research brief, judges its "
    "quality and re-researches gaps automatically, then packages everything into a knowledge "
    "folder ready to feed to any coding AI"
)

INTAKE = {
    "raw_idea": IDEA,
    "ideal_outcome": (
        "A production-ready Python CLI + web UI that orchestrates 7 LLM agents in parallel "
        "across 6+ provider fallback chains (Groq, DeepSeek, SambaNova, Cerebras, SiliconFlow, Zhipu), "
        "searches GitHub for real repos via domain-anchored queries, deep-dives into source code, "
        "extracts copy-paste patterns and verified libraries with source attribution, "
        "produces a quality-judged markdown research brief (architecture_matches_problem scored double), "
        "and delivers a structured 10-file knowledge package ready to feed to Claude Code or Codebuff"
    ),
    "domain": ["ml", "data", "cli", "web"],
    "primary_language": "python",
    "complexity_estimate": "high",
    "core_problems": [
        "Multi-agent async orchestration with parallel fanout, semaphore throttling, and checkpoint/resume",
        "GitHub repo search with domain-anchored queries, batch relevance scoring, and deep-dive code extraction",
        "Multi-provider LLM pool with key rotation, rate limiting, circuit breakers, and automatic fallback chains",
        "Pattern extraction from combined GitHub + web findings anchored to the original idea",
        "Research brief synthesis with ideal-outcome injection and hallucination prevention",
        "Quality judging with architecture-correctness dimension and re-research loop control",
    ],
}

DECOMPOSITION = {
    "sub_problems": [
        {
            "id": "SP-1",
            "title": "Multi-Agent Async Orchestration Pipeline",
            "description": (
                "Orchestrate 7+ agents in sequence with parallel fanout for GitHub+Web research. "
                "Includes checkpoint/resume system, semaphore-limited concurrency, and re-research loop."
            ),
            "why_critical": "The backbone — everything else runs inside this orchestration layer.",
            "github_search_queries": [
                "python async multi-agent orchestration pipeline checkpointing",
                "asyncio semaphore parallel agent pipeline rate limiting python",
                "multi-agent research pipeline checkpoint resume asyncio",
            ],
            "pypi_search_terms": ["asyncio", "anyio", "prefect", "celery"],
            "stackoverflow_tags": ["python-asyncio", "multi-agent", "pipeline"],
            "ideal_outcome_relevance": "Directly implements the core pipeline that wires all 7 agents",
        },
        {
            "id": "SP-2",
            "title": "GitHub Repo Search + Deep-Dive Code Analysis",
            "description": (
                "Search GitHub with domain-anchored queries, batch-score repos for idea relevance, "
                "apply usage filter (tests, examples, active commits), then deep-dive top 3 for "
                "architecture patterns, reusable code snippets, and dependency lists."
            ),
            "why_critical": "Primary research signal — real code examples drive the knowledge package quality.",
            "github_search_queries": [
                "github api search repositories python batch relevance scoring",
                "python github code analysis extract architecture patterns dependencies",
                "github repo deep dive source code pattern extraction python",
            ],
            "pypi_search_terms": ["PyGithub", "ghapi", "httpx"],
            "stackoverflow_tags": ["github-api", "code-analysis", "python"],
            "ideal_outcome_relevance": "Produces the real-repo findings that feed pattern extraction and the brief",
        },
        {
            "id": "SP-3",
            "title": "Multi-Provider LLM Pool with Fallback Chains",
            "description": (
                "Key rotation across 6+ providers (Groq, DeepSeek, SambaNova, Cerebras, SiliconFlow, Zhipu). "
                "Token bucket rate limiting per provider, circuit breakers, and automatic cascading fallback "
                "when any provider hits rate limits, balance errors, or goes down."
            ),
            "why_critical": "Reliability — without fallbacks a single API failure kills the entire run.",
            "github_search_queries": [
                "python llm provider pool key rotation rate limiting fallback chain",
                "openai api key rotation multiple providers circuit breaker python",
                "multi provider llm client fallback groq deepseek cerebras python",
            ],
            "pypi_search_terms": ["openai", "anthropic", "litellm"],
            "stackoverflow_tags": ["openai-api", "rate-limiting", "circuit-breaker"],
            "ideal_outcome_relevance": "Ensures the pipeline survives any single provider outage",
        },
        {
            "id": "SP-4",
            "title": "Pattern Extraction and Knowledge Packaging",
            "description": (
                "Distill combined GitHub + web findings into architectural patterns, verified library list "
                "(with source_repo attribution), anti-patterns, gotchas, and performance notes — all "
                "anchored to the original idea. Then package into 10 structured markdown files."
            ),
            "why_critical": "Final deliverable — this is what the user actually feeds to Claude Code.",
            "github_search_queries": [
                "python extract architectural patterns from code repositories structured output",
                "llm structured json extraction patterns libraries from research findings",
                "knowledge base builder markdown structured output from research python",
            ],
            "pypi_search_terms": ["pydantic", "jinja2", "rich"],
            "stackoverflow_tags": ["pattern-recognition", "knowledge-base", "markdown"],
            "ideal_outcome_relevance": "Produces the knowledge package that is the core deliverable",
        },
        {
            "id": "SP-5",
            "title": "Research Brief Synthesis + Quality Judging",
            "description": (
                "Generate a multi-section markdown research brief with ideal-outcome injection in every section. "
                "Quality judge scores on 5 dimensions (architecture_matches_problem counts double), "
                "forces RE_RESEARCH verdict if architecture score < 5, and loops up to 2 times."
            ),
            "why_critical": "Quality gate — prevents hallucinated or wrong-architecture briefs from shipping.",
            "github_search_queries": [
                "llm research brief generation structured markdown multi-section python",
                "ai quality judge scoring research output re-research loop python",
                "automated research synthesis quality scoring iterative improvement llm",
            ],
            "pypi_search_terms": ["pydantic", "jinja2", "mistralai"],
            "stackoverflow_tags": ["llm", "quality-assurance", "text-generation"],
            "ideal_outcome_relevance": "Guarantees the final brief matches the ideal outcome before delivery",
        },
    ]
}

def seed():
    state = ResearchState(IDEA)
    run_id = state.run_id

    state.checkpoint("intake", INTAKE)
    state.checkpoint("decomposer", DECOMPOSITION)

    print(f"\nOK Seeded run: {run_id}")
    print(f"   Output dir: {state.base_path}")
    print(f"\n   In the UI — paste this as the idea:")
    print(f"   {IDEA[:120]}...")
    print(f"\n   And this as the resume_id (if UI supports it), OR run:")
    print(f"   python main.py \"{IDEA[:80]}...\" --resume {run_id}")
    print(f"\n   Run ID to copy: {run_id}")
    return run_id

if __name__ == "__main__":
    seed()
