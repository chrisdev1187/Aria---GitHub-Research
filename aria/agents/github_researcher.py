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

from config import research, hardware
from tools.deepseek_client import DeepSeekClient
from tools.github_api import GitHubClient
from tools.jina_reader import JinaReader
from tools.gemini_client import GeminiClient
from provider_pool import SchemaValidationFailed


PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "github_research.txt"


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
        self.gemini = GeminiClient()

    async def run(self, sub_problem: dict[str, Any]) -> dict[str, Any]:
        """
        Research a single sub-problem on GitHub.

        Args:
            sub_problem: Single sub-problem dict from decomposition

        Returns:
            GitHub findings for this sub-problem
        """
        queries = sub_problem.get("github_search_queries", [""])

        # Step 1 — COLLECT: Search GitHub and fetch ALL READMEs
        all_repos = []
        for query in queries[:3]:  # Max 3 search queries
            repos = await self.github.search_repositories(
                query=query,
                limit=research.max_repos_per_subproblem,
            )
            all_repos.extend(repos)

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
        scored_repos = await self._batch_score_repos(repos, sub_problem)

        # Step 3 — DEEP DIVE: Top 3 scored repos (after usage filter)
        deep_dive_repos = []
        for repo in scored_repos[:5]:  # Check top 5 for usage filter
            try:
                tree = await self.github.get_repo_tree(repo["full_name"])
                passes = await self.github.passes_usage_filter(repo, tree)
                if passes:
                    repo["file_tree"] = tree
                    deep_dive_repos.append(repo)
                    if len(deep_dive_repos) >= 3:
                        break
            except Exception:
                continue

        # Deep dive analysis on top repos
        deep_dive_results = []
        for repo in deep_dive_repos:
            analysis = await self._deep_dive_repo(repo, sub_problem)
            deep_dive_results.append(analysis)

        return {
            "sub_problem_id": sub_problem.get("id", ""),
            "sub_problem_title": sub_problem.get("title", ""),
            "repos_found": len(repos),
            "repos_scored": len(scored_repos),
            "repos_deep_dived": len(deep_dive_repos),
            "all_repos": scored_repos,
            "deep_dive_results": deep_dive_results,
        }

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
    ) -> list[dict[str, Any]]:
        """One LLM call to score all repos for relevance."""
        if self.offline:
            return repos  # Skip scoring in offline mode

        deepseek = DeepSeekClient()

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
                    "You are a GitHub repository relevance scorer. "
                    "Score each repo 0-10 for relevance to the given sub-problem. "
                    "Consider: code quality, star count, maintenance, documentation, and actual utility."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Sub-problem: {sub_problem.get('title', '')}\n"
                    f"Description: {sub_problem.get('description', '')}\n\n"
                    f"Repos to score:\n{summaries_text}\n\n"
                    "Return JSON: {\"scores\": [{\"full_name\": \"org/repo\", \"relevance\": 8, \"reason\": \"...\"}, ...]}"
                ),
            },
        ]

        try:
            result = await deepseek.generate(messages)
            scores = result.get("scores", [])

            # Apply scores to repos
            score_map = {s.get("full_name"): s for s in scores}
            for repo in repos:
                s = score_map.get(repo["full_name"], {})
                repo["relevance_score"] = s.get("relevance", 5)
                repo["relevance_reason"] = s.get("reason", "")

            repos.sort(key=lambda r: r.get("relevance_score", 0), reverse=True)
        except Exception:
            # If scoring fails, keep original order
            pass

        return repos

    async def _deep_dive_repo(
        self,
        repo: dict[str, Any],
        sub_problem: dict[str, Any],
    ) -> dict[str, Any]:
        """Deep dive into a single repo — fetch key files and analyse."""
        deepseek = DeepSeekClient()
        repo_info = repo.get("full_name", "")

        # Fetch key source files (up to 5)
        key_files = await self._fetch_key_files(repo)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a code analysis expert. Given a GitHub repository and its key files, "
                    "extract: architecture patterns, key code snippets, design decisions, gotchas."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Repo: {repo_info}\n"
                    f"Description: {repo.get('description', '')}\n"
                    f"Stars: {repo.get('stargazers_count', 0)}\n"
                    f"Sub-problem: {sub_problem.get('title', '')}\n\n"
                    f"Key files:\n{key_files}\n\n"
                    "Return JSON: {\n"
                    '  "architecture": "...",\n'
                    '  "key_pattern": "...",\n'
                    '  "code_snippet": "...",\n'
                    '  "dependencies": ["..."],\n'
                    '  "gotchas": ["..."],\n'
                    '  "fork_worth_it": true/false,\n'
                    '  "what_to_change_if_forked": "..."\n'
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
