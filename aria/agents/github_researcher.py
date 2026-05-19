"""
ARIA v2 — Agent 3: GitHub Research Agent
Finds and deeply analyses repos solving ONE specific sub-problem.

Batch-first architecture (solves RPM bottleneck):
  Step 1 — COLLECT: GitHub search → fetch READMEs + manifests (I/O, not LLM)
  Step 2 — BATCH ANALYSE: One DeepSeek call scores ALL repos in context
  Step 3 — DEEP DIVE: Top 3 scored repos → fetch source files → one more DeepSeek call

Total: 2 LLM calls per sub-problem (down from 80-120).

Validated Usage Filter (gates Step 3):
  - Has tests/ or examples/ directory
  - README has actual code blocks
  - Active development in last 12 months
  - >500 stars or recent star velocity
"""

import asyncio
from pathlib import Path
from typing import Any, Optional

from config import research
from tools.deepseek_client import DeepSeekClient
from tools.github_api import GitHubClient
from tools.jina_reader import JinaReader

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "github_research.txt"

# Words that add no search value on GitHub's search API
_STOPWORDS = {
    "python", "a", "an", "the", "and", "or", "for", "from", "in", "on",
    "with", "to", "of", "by", "via", "using", "multiple", "various",
    "based", "simple", "easy", "fast", "best", "great", "how", "what",
    "build", "building", "implementation", "tool", "tools", "system",
    "systems", "app", "apps", "library", "framework", "approach", "pattern",
    "example", "examples", "tutorial", "guide", "project", "projects",
}


def _shorten_query(query: str, max_words: int = 4) -> str:
    """
    Trim a verbose decomposer query to max_words high-signal keywords.
    GitHub search returns 0 results for 6+ word queries — keep it short.
    """
    words = query.lower().split()
    kept = [w for w in words if w not in _STOPWORDS]
    if not kept:
        kept = words
    return " ".join(kept[:max_words])


class GitHubResearchAgent:
    """
    Agent 3 — GitHub Researcher.

    Batch-first architecture for one sub-problem:
    1. Search GitHub (I/O)
    2. Batch score repos with one DeepSeek call
    3. Deep dive top 3 with validated usage filter
    4. Extract key code patterns
    """

    def __init__(self, offline: bool = False):
        self.offline = offline
        self.github = GitHubClient()
        self.jina = JinaReader()

    async def run(
        self,
        sub_problem: dict[str, Any],
        intake_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Research a single sub-problem on GitHub.

        Args:
            sub_problem: Single sub-problem dict from decomposition
            intake_result: Full intake output (raw_idea, ideal_outcome, etc.)

        Returns:
            GitHub findings for this sub-problem
        """
        import logging
        _log = logging.getLogger("aria.github_researcher")

        intake_result = intake_result or {}
        queries = sub_problem.get("github_search_queries", [""])
        sp_id = sub_problem.get("id", "?")

        # Step 1 — COLLECT: Search GitHub and fetch ALL READMEs
        all_repos = []
        search_errors = []
        for query in queries[:5]:  # Use all decomposer queries
            # GitHub search returns 0 for 6+ word queries — use short form first
            short_q = _shorten_query(query, max_words=4)
            candidates = [short_q]
            if short_q.lower() != query.lower():
                # Also try a 3-word fallback and the original as last resort
                candidates.append(_shorten_query(query, max_words=3))
            for attempt_q in candidates:
                try:
                    repos = await self.github.search_repositories(
                        query=attempt_q,
                        limit=research.max_repos_per_subproblem,
                    )
                    if repos:
                        all_repos.extend(repos)
                        break  # found results — skip shorter fallbacks
                except Exception as e:
                    err_msg = f"[{sp_id}] search failed for '{attempt_q[:60]}': {type(e).__name__}: {e}"
                    _log.error(err_msg)
                    search_errors.append(str(e))
                    break  # don't retry on API error

        # Deduplicate by full_name
        seen = set()
        unique_repos = []
        for repo in all_repos:
            if repo["full_name"] not in seen:
                seen.add(repo["full_name"])
                unique_repos.append(repo)

        repos = unique_repos[:research.max_repos_per_subproblem]

        # Fetch READMEs in parallel (I/O, not LLM)
        readme_tasks = [self._fetch_repo_readme(repo) for repo in repos]
        readmes = await asyncio.gather(*readme_tasks, return_exceptions=True)

        for i, result in enumerate(readmes):
            if isinstance(result, str):
                repos[i]["readme_content"] = result[:5000]  # Truncate for context
            else:
                repos[i]["readme_content"] = ""

        # Step 2 — BATCH ANALYSE: One DeepSeek call scores all repos
        scored_repos = await self._batch_score_repos(repos, sub_problem, intake_result)

        # Step 3 — DEEP DIVE: Top 3 scored repos (after usage filter)
        deep_dive_repos = []
        filter_fallbacks = []  # repos that failed filter, used if nothing passes
        for repo in scored_repos[:7]:  # Check top 7 for usage filter
            try:
                branch = repo.get("default_branch", "main")
                tree = await self.github.get_repo_tree(repo["full_name"], branch)
                passes = await self.github.passes_usage_filter(repo, tree)
                if passes:
                    repo["file_tree"] = tree
                    deep_dive_repos.append(repo)
                    if len(deep_dive_repos) >= 3:
                        break
                elif not filter_fallbacks:
                    repo["file_tree"] = tree
                    filter_fallbacks.append(repo)
            except Exception:
                continue

        # If nothing passed the filter, use top-scored repo as fallback
        if not deep_dive_repos and filter_fallbacks:
            deep_dive_repos = filter_fallbacks[:1]

        # Deep dive analysis on top repos
        deep_dive_results = []
        for repo in deep_dive_repos:
            analysis = await self._deep_dive_repo(repo, sub_problem, intake_result)
            deep_dive_results.append(analysis)

        result = {
            "sub_problem_id": sub_problem.get("id", ""),
            "sub_problem_title": sub_problem.get("title", ""),
            "repos_found": len(repos),
            "repos_scored": len(scored_repos),
            "repos_deep_dived": len(deep_dive_repos),
            "all_repos": scored_repos,
            "deep_dive_results": deep_dive_results,
        }
        if search_errors:
            result["search_errors"] = search_errors
        return result

    async def _fetch_repo_readme(self, repo: dict[str, Any]) -> Optional[str]:
        """Fetch a repo's README via Jina Reader."""
        try:
            return await self.jina.read_github_readme(repo["full_name"])
        except Exception:
            return None

    async def _batch_score_repos(
        self,
        repos: list[dict[str, Any]],
        sub_problem: dict[str, Any],
        intake_result: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """One LLM call to score all repos for relevance to the specific idea."""
        if self.offline:
            return repos

        deepseek = DeepSeekClient()

        raw_idea = intake_result.get("raw_idea", "")
        ideal_outcome = intake_result.get("ideal_outcome", "")

        repo_summaries = []
        for r in repos:
            repo_summaries.append(
                f"- {r['full_name']}: {r.get('description', 'No description')[:200]} "
                f"({r['stargazers_count']} stars, language: {r.get('language', 'unknown')})"
            )

        summaries_text = "\n".join(repo_summaries)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a GitHub repository relevance scorer.\n\n"
                    "Your job: score each repo 0-10 for how useful it would be to someone building the SPECIFIC idea below.\n\n"
                    "Scoring criteria — ALL must be considered:\n"
                    "  1. Domain match: does the repo solve the SAME type of problem as the idea? "
                    "A generic NLP library scores low if the idea needs a specific domain tool.\n"
                    "  2. Reusability: can code or patterns from this repo be directly used for the idea?\n"
                    "  3. Recency: actively maintained (commits in last 12 months = bonus).\n"
                    "  4. Stars: higher is better but not the primary signal.\n\n"
                    "IMPORTANT: A repo that is generally good but unrelated to the SPECIFIC idea scores ≤3.\n"
                    "Do not score repos highly just because they share a broad technology (e.g. 'both use Python NLP').\n"
                    "The repo must be relevant to THIS specific idea, not just the sub-problem title."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"IDEA (what the user wants to build):\n{raw_idea}\n\n"
                    f"IDEAL OUTCOME:\n{ideal_outcome}\n\n"
                    f"CURRENT SUB-PROBLEM: {sub_problem.get('title', '')}\n"
                    f"Sub-problem description: {sub_problem.get('description', '')}\n\n"
                    f"Repos to score:\n{summaries_text}\n\n"
                    "Return JSON: {\"scores\": [{\"full_name\": \"org/repo\", \"relevance\": 8, \"reason\": \"one sentence explaining relevance to the IDEA\"}, ...]}"
                ),
            },
        ]

        try:
            result = await deepseek.generate(messages)
            scores = result.get("scores", [])

            score_map = {s.get("full_name"): s for s in scores}
            for repo in repos:
                s = score_map.get(repo["full_name"], {})
                repo["relevance_score"] = s.get("relevance", 5)
                repo["relevance_reason"] = s.get("reason", "")

            repos.sort(key=lambda r: r.get("relevance_score", 0), reverse=True)
        except Exception:
            pass

        return repos

    async def _deep_dive_repo(
        self,
        repo: dict[str, Any],
        sub_problem: dict[str, Any],
        intake_result: dict[str, Any],
    ) -> dict[str, Any]:
        """Deep dive into a single repo — fetch key files and analyse."""
        deepseek = DeepSeekClient()
        repo_info = repo.get("full_name", "")
        raw_idea = intake_result.get("raw_idea", "")
        ideal_outcome = intake_result.get("ideal_outcome", "")

        # Fetch key source files (up to 5)
        key_files = await self._fetch_key_files(repo)

        system_prompt = (
            PROMPT_PATH.read_text(encoding="utf-8")
            if PROMPT_PATH.exists()
            else (
                "You are a code analysis expert. Extract patterns and insights directly useful "
                "for building the specific idea. Focus ONLY on what can be reused for THIS idea."
            )
        )

        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": (
                    f"IDEA: {raw_idea}\n"
                    f"IDEAL OUTCOME: {ideal_outcome}\n\n"
                    f"Repo: {repo_info}\n"
                    f"Description: {repo.get('description', '')}\n"
                    f"Stars: {repo.get('stargazers_count', 0)}\n"
                    f"Sub-problem: {sub_problem.get('title', '')}\n\n"
                    f"Key files:\n{key_files}\n\n"
                    "Return JSON: {\n"
                    '  "architecture": "how the repo is structured, relevant to the idea",\n'
                    '  "key_pattern": "the single most reusable pattern for this idea",\n'
                    '  "code_snippet": "the most relevant code snippet (≤20 lines)",\n'
                    '  "dependencies": ["libs used that are relevant to the idea"],\n'
                    '  "gotchas": ["things to watch out for when reusing this"],\n'
                    '  "fork_worth_it": true/false,\n'
                    '  "what_to_change_if_forked": "what to adapt for the specific idea"\n'
                    "}"
                ),
            },
        ]

        try:
            analysis = await deepseek.generate(messages)
        except Exception:
            analysis = {
                "architecture": "Analysis failed",
                "key_pattern": "",
                "code_snippet": "",
                "dependencies": [],
                "gotchas": ["Could not analyse this repo"],
                "fork_worth_it": False,
                "what_to_change_if_forked": "",
            }

        return {
            "full_name": repo_info,
            "stars": repo.get("stargazers_count", 0),
            "description": repo.get("description", ""),
            "language": repo.get("language", ""),
            "relevance_score": repo.get("relevance_score", 5),
            "analysis": analysis,
        }

    async def _fetch_key_files(self, repo: dict[str, Any]) -> str:
        """Fetch up to 5 key source files from a repo."""
        tree = repo.get("file_tree", [])
        if not tree:
            return "No file tree available"

        # Prioritise: package manifests, main entry points, core source files
        priority_patterns = [
            "package.json", "setup.py", "Cargo.toml", "go.mod",
            "requirements.txt", "pyproject.toml",
            "README.md", "index.js", "index.ts", "main.py", "main.go",
            "src/", "lib/",
        ]

        # Select important files
        selected = []
        seen_dirs = set()

        for pattern in priority_patterns:
            for item in tree:
                path = item.get("path", "")
                if len(selected) >= research.max_files_per_repo:
                    break
                if path.endswith(pattern) or f"/{pattern}" in path:
                    if item.get("type") == "blob" and path not in selected:
                        dir_name = path.split("/")[0] if "/" in path else ""
                        if dir_name and dir_name in seen_dirs:
                            continue
                        selected.append(path)
                        if dir_name:
                            seen_dirs.add(dir_name)

        # Fetch selected files
        contents = []
        for path in selected[:research.max_files_per_repo]:
            try:
                content = await self.github.fetch_file(
                    repo["full_name"],
                    path,
                )
                if content:
                    # Truncate long files
                    if len(content) > 10000:
                        content = content[:10000] + "\n... [truncated]"
                    contents.append(f"--- {path} ---\n{content}")
            except Exception:
                continue

        return "\n\n".join(contents) if contents else "No files could be fetched"


    async def close(self):
        """Clean up resources."""
        await self.github.close()
