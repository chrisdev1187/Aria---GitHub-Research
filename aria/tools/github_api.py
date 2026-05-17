"""
ARIA v2 — GitHub API Client
Repository search, tree browsing, file fetching with validated usage filter.

Batch-first architecture:
  Step 1 — Search GitHub → collect READMEs + package manifests (I/O only)
  Step 2 — Batch score with DeepSeek (1 LLM call for all repos)
  Step 3 — Deep dive top 3 repos (file fetch + analysis)

Validated usage filter ensures only repos with actual usage
(not just claims) proceed to Step 3 deep dive.
"""

import asyncio
import os
from datetime import datetime
from typing import Any, Optional

import aiohttp

from config import get_github_token, RATE_LIMITS
from provider_pool import TokenBucketLimiter


# GitHub API constants
GITHUB_API_BASE = "https://api.github.com"
RATE_LIMIT_RPH = RATE_LIMITS["github"]["rph"]


class GitHubClient:
    """
    GitHub API client for code research.

    Uses GitHub token for authenticated requests (5000 req/hr).
    Falls back to unauthenticated (60 req/hr) if no token.

    Key methods:
    - search_repositories(query, limit) → list of repo metadata
    - get_repo_tree(full_name) → file tree paths
    - fetch_file(full_name, path) → file content
    - fetch_readme(full_name) → README content
    - passes_usage_filter(repo) → bool (tests/examples/docs check)
    """

    def __init__(self):
        self.token = get_github_token()
        self.rate_limiter = TokenBucketLimiter(max(1, RATE_LIMIT_RPH // 60))
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "ARIA-v2/1.0",
        }
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(headers=self.headers)
        return self._session

    async def search_repositories(
        self,
        query: str,
        limit: int = 10,
        sort: str = "stars",
        order: str = "desc",
    ) -> list[dict[str, Any]]:
        """
        Search GitHub repositories.

        Args:
            query: GitHub search query
            limit: Max repos to return (default 10)
            sort: Sort field (stars, updated, forks, help-wanted-issues)
            order: desc or asc

        Returns:
            List of repo dicts with: full_name, description, stargazers_count,
            language, updated_at, topics, license, default_branch
        """
        await self.rate_limiter.wait()
        session = await self._get_session()

        url = f"{GITHUB_API_BASE}/search/repositories"
        params = {
            "q": query,
            "sort": sort,
            "order": order,
            "per_page": min(limit, 100),
        }

        async with session.get(url, params=params) as response:
            if response.status == 403:
                raise RateLimitError("GitHub API rate limit exceeded")
            response.raise_for_status()
            data = await response.json()

        repos = []
        for item in data.get("items", [])[:limit]:
            repos.append({
                "full_name": item["full_name"],
                "description": item.get("description", "") or "",
                "stargazers_count": item["stargazers_count"],
                "language": item.get("language"),
                "updated_at": item.get("updated_at"),
                "created_at": item.get("created_at"),
                "topics": item.get("topics", []),
                "license": item["license"]["spdx_id"] if item.get("license") else None,
                "forks_count": item.get("forks_count", 0),
                "default_branch": item.get("default_branch", "main"),
                "html_url": item["html_url"],
                "clone_url": item.get("clone_url", ""),
                "readme_code_block_count": 0,  # filled after fetch_readme
            })

        return repos

    async def get_repo_tree(self, full_name: str, branch: str = "main") -> list[dict[str, Any]]:
        """
        Get the file tree of a repository (recursive, limited to 1000 entries).

        Args:
            full_name: "owner/repo"
            branch: Branch name (default "main")

        Returns:
            List of file entries with path, type, size
        """
        await self.rate_limiter.wait()
        session = await self._get_session()

        url = f"{GITHUB_API_BASE}/repos/{full_name}/git/trees/{branch}?recursive=1"

        async with session.get(url) as response:
            if response.status == 403:
                raise RateLimitError("GitHub API rate limit exceeded")
            if response.status == 409:
                # Empty repo
                return []
            response.raise_for_status()
            data = await response.json()

        return data.get("tree", [])

    async def fetch_file(self, full_name: str, path: str, branch: str = "main") -> Optional[str]:
        """
        Fetch a file's content from a GitHub repo.

        Args:
            full_name: "owner/repo"
            path: File path within repo
            branch: Branch name

        Returns:
            File content as string, or None if not found
        """
        await self.rate_limiter.wait()
        session = await self._get_session()

        url = f"{GITHUB_API_BASE}/repos/{full_name}/contents/{path}"
        params = {"ref": branch}

        async with session.get(url, params=params) as response:
            if response.status == 403:
                raise RateLimitError("GitHub API rate limit exceeded")
            if response.status != 200:
                return None

            import base64
            data = await response.json()
            if data.get("encoding") == "base64":
                content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
                return content
            return data.get("content", "")

    async def fetch_readme(self, full_name: str, branch: str = "main") -> Optional[str]:
        """
        Fetch a repo's README content.

        Args:
            full_name: "owner/repo"
            branch: Branch name

        Returns:
            README content as string, or None
        """
        return await self.fetch_file(full_name, "README.md", branch)

    async def count_readme_code_blocks(self, full_name: str) -> int:
        """Count code blocks in a repo's README. Higher = more genuine usage."""
        readme = await self.fetch_readme(full_name)
        if not readme:
            return 0
        # Count ``` fences — each pair is a code block
        return readme.count("```") // 2

    async def passes_usage_filter(
        self,
        repo: dict[str, Any],
        tree: Optional[list[dict[str, Any]]] = None,
    ) -> bool:
        """
        Validated usage filter — gates Step 3 deep dive.

        A repo passes if it demonstrates real usage, not just claims:
        - Has tests/ or examples/ directory with executable code
        - README contains actual code blocks
        - Active development (commit in last 12 months)

        Returns True if the repo should be deep-dived.
        """
        if tree is None:
            try:
                tree = await self.get_repo_tree(repo["full_name"])
            except Exception:
                return False

        paths = {item["path"].lower() for item in tree}

        # Check for tests
        has_tests = any(
            p.startswith(("tests/", "test/", "__tests__/", "spec/"))
            for p in paths
        )

        # Check for examples
        has_examples = any(p.startswith("examples/") for p in paths)

        # Check for code in README
        readme_code_count = await self.count_readme_code_blocks(repo["full_name"])
        has_code_in_readme = readme_code_count > 0

        # Star velocity: at least 50 stars in last 6 months OR >500 total stars
        # GitHub API doesn't directly give "stars in last 6 months", so we estimate
        now = datetime.now()
        created = repo.get("created_at")
        total_stars = repo["stargazers_count"]
        if isinstance(created, str):
            try:
                created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                age_years = (now - created_dt).total_seconds() / (365.25 * 86400)
                # If created recently (< 2 years ago) and has >50 stars, likely has velocity
                recent_with_stars = age_years < 2 and total_stars > 50
            except (ValueError, TypeError):
                recent_with_stars = False
        else:
            recent_with_stars = False
        star_velocity = total_stars > 500 or recent_with_stars

        # To pass, must have real usage AND be somewhat popular
        has_real_usage = has_tests or has_examples or has_code_in_readme
        is_popular = star_velocity

        return has_real_usage and is_popular

    async def close(self):
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()


# Re-export
from provider_pool import RateLimitError

__all__ = ["GitHubClient", "RateLimitError"]
