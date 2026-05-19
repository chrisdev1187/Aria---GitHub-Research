"""
ARIA v2 — Code Extractor Tool
Fetches actual source files from GitHub repos via the API.
Used after repo discovery to extract real implementation code for the knowledge package.

Primary usage: github_researcher → CodeExtractor → knowledge_packager
"""

import json
import logging
import os
from typing import Optional

from tools.gemini_client import GeminiClient
from tools.github_api import GitHubClient

_log = logging.getLogger("aria.code_extractor")

GEMINI_THRESHOLD_CHARS = 50_000  # Use Gemini summary above this size

# Source file extensions we care about — mapped to language labels
SOURCE_FILE_EXTENSIONS: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescriptreact",
    ".jsx": "javascriptreact",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".rb": "ruby",
    ".php": "php",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".sql": "sql",
    ".sh": "shellscript",
    ".bash": "shellscript",
    ".zsh": "shellscript",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".toml": "toml",
    ".xml": "xml",
    ".md": "markdown",
    ".css": "css",
    ".scss": "scss",
    ".less": "less",
    ".html": "html",
    ".vue": "vue",
    ".svelte": "svelte",
    ".astro": "astro",
    ".tf": "terraform",
    ".dockerfile": "dockerfile",
    ".proto": "protobuf",
    ".gradle": "gradle",
    ".cmake": "cmake",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".mts": "typescript",
    ".cts": "typescript",
}

# Directories to skip when crawling repo trees
IGNORED_DIRECTORIES: set[str] = {
    "node_modules", ".git", "__pycache__", "venv", "env", ".venv",
    "dist", "build", ".next", ".nuxt", "target", "vendor",
    ".gradle", "coverage", ".tox", ".eggs", ".egg-info",
    ".github", ".vscode", ".idea", ".DS_Store", "assets",
    "fonts", "images", "img", "icons", "static/fonts",
    "test", "tests", "spec", "__tests__", "fixtures",
    "migrations", ".terraform", "Pods", ".bundle",
    "third_party", "third-party", "external",
    "benchmarks", "docs/_build", "documentation",
    "bower_components", "jspm_packages",
    ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".serverless", ".webpack", ".svelte-kit", ".output",
}

CONFIG_FILE_PATTERNS: set[str] = {
    "package.json", "setup.py", "pyproject.toml", "Cargo.toml",
    "go.mod", "go.sum", "Gemfile", "Podfile", "build.gradle",
    "pom.xml", "Makefile", "Dockerfile", "docker-compose.yml",
    "composer.json", "requirements.txt", "Pipfile", "CMakeLists.txt",
    "README.md", "CONTRIBUTING.md", "LICENSE", "index.js", "index.ts",
    "main.py", "app.py", "cli.py", "lib.rs", "main.rs",
    "src/lib.rs", "src/main.rs",
}

MAX_FILE_SIZE_CHARS = 30_000  # Truncate files longer than this (fallback when Gemini unavailable)
GEMINI_MAX_FILE_CHARS = 200_000  # Skip files beyond this even with Gemini
MAX_FILES_PER_REPO = 25        # Maximum source files to pull per repo


class CodeExtractorError(Exception):
    """Raised when code extraction fails."""


class CodeExtractor:
    """Fetches source files from GitHub repos for deep analysis.

    Uses the existing GitHubClient (which handles auth, rate limiting).
    Designed to be called after repo discovery — takes the top repos
    and pulls their actual source code into the knowledge package.
    """

    def __init__(self, github: Optional[GitHubClient] = None, gemini: Optional[GeminiClient] = None):
        self.github = github or GitHubClient()
        self._gemini: Optional[GeminiClient] = gemini  # lazy-init on first large-file hit

    async def _get_gemini(self) -> Optional[GeminiClient]:
        """Lazy-init Gemini; returns None if not configured."""
        if self._gemini is None:
            try:
                c = GeminiClient()
                if await c.is_available():
                    self._gemini = c
                else:
                    self._gemini = False  # type: ignore[assignment]  # sentinel: no key
            except Exception:
                self._gemini = False  # type: ignore[assignment]
        return self._gemini if self._gemini is not False else None

    async def extract_repo_files(
        self,
        full_name: str,
        branch: str = "main",
        max_files: int = MAX_FILES_PER_REPO,
        primary_language: Optional[str] = None,
    ) -> list[dict]:
        """Fetch source files from a single repo.

        Returns list of {path, content, language, size} sorted by importance.
        Config files first, then source files matching the primary language.
        """
        try:
            tree = await self.github.get_repo_tree(full_name, branch)
        except Exception as e:
            raise CodeExtractorError(f"Failed to get tree for {full_name}: {e}") from e

        if not tree or not isinstance(tree, list):
            return []

        # Separate config vs source files
        config_files: list[dict] = []
        source_files: list[dict] = []
        other_files: list[dict] = []

        for entry in tree:
            if not isinstance(entry, dict):
                continue
            path: str = entry.get("path", "") or ""
            entry_type: str = entry.get("type", "") or ""

            # Only files
            if entry_type != "file":
                continue

            # Skip ignored directories
            parts = path.replace("\\", "/").split("/")
            if any(p in IGNORED_DIRECTORIES for p in parts):
                continue

            # Determine file size (if available)
            size = entry.get("size", 0)
            if isinstance(size, (int, float)) and size > GEMINI_MAX_FILE_CHARS:
                continue  # too large even for Gemini summary

            _, ext = os.path.splitext(path)
            ext = ext.lower()

            filename = path.split("/")[-1].lower()

            if filename in CONFIG_FILE_PATTERNS or ext in (".json", ".toml", ".yaml", ".yml", ".xml"):
                config_files.append({"path": path, "ext": ext, "size": size})
            elif ext in SOURCE_FILE_EXTENSIONS:
                file_entry = {"path": path, "ext": ext, "size": size,
                              "language": SOURCE_FILE_EXTENSIONS[ext]}
                # Prioritize primary language
                if primary_language and file_entry["language"] == primary_language.lower():
                    source_files.insert(0, file_entry)
                else:
                    source_files.append(file_entry)
            elif ext in (".md", ".txt", ".cfg", ".ini", ".conf"):
                other_files.append({"path": path, "ext": ext, "size": size})

        # Prioritize: configs first, then source, then docs
        prioritized = config_files + source_files + other_files
        selected = prioritized[:max_files]

        # Fetch content for selected files; use Gemini summary for large files
        results: list[dict] = []
        for item in selected:
            try:
                content = await self.github.fetch_file(full_name, item["path"], branch)
                if not content or len(content) <= 20:
                    continue

                summarized = False
                if len(content) > GEMINI_THRESHOLD_CHARS:
                    gemini = await self._get_gemini()
                    if gemini:
                        try:
                            summary = await gemini.summarize_content(content, item["path"])
                            content = f"[Gemini summary — original {len(content):,} chars]\n\n{summary}"
                            summarized = True
                        except Exception as exc:
                            _log.debug("Gemini summarize failed for %s: %s — truncating", item["path"], exc)

                if not summarized:
                    content = content[:MAX_FILE_SIZE_CHARS]

                results.append({
                    "path": item["path"],
                    "content": content,
                    "language": item.get("language", "text"),
                    "size": len(content),
                    "summarized": summarized,
                })
            except Exception:
                continue  # Skip files that fail to fetch

        return results

    async def extract_top_repos(
        self,
        repos: list[dict],
        primary_language: Optional[str] = None,
        max_files_per_repo: int = MAX_FILES_PER_REPO,
        max_repos: int = 10,
    ) -> dict[str, list[dict]]:
        """Extract code from multiple repos.

        Args:
            repos: List of repo dicts (must have 'full_name' key)
            primary_language: Primary language to prioritize
            max_files_per_repo: Max files per repo
            max_repos: Max repos to process

        Returns:
            {repo_full_name: [{path, content, language, size}, ...]}
        """
        results: dict[str, list[dict]] = {}
        for repo in repos[:max_repos]:
            full_name = repo.get("full_name", "")
            if not full_name:
                continue
            try:
                files = await self.extract_repo_files(
                    full_name,
                    max_files=max_files_per_repo,
                    primary_language=primary_language or repo.get("language", ""),
                )
                if files:
                    results[full_name] = files
            except CodeExtractorError:
                continue
        return results

    async def save_extracted_code(
        self,
        extracted: dict[str, list[dict]],
        output_dir: str,
        repo_metadata: Optional[dict[str, dict]] = None,
    ) -> str:
        """Save extracted code to disk inside the knowledge package.

        Creates: {output_dir}/extracted_code/{repo_name}/*.ext

        Args:
            extracted: {repo_full_name: [{path, content, language}]}
            output_dir: Base output directory for extracted code
            repo_metadata: Optional {repo_full_name: {stars, description, url}}

        Returns:
            Path to the extracted_code directory
        """
        code_dir = os.path.join(output_dir, "extracted_code")
        os.makedirs(code_dir, exist_ok=True)

        manifest = []

        for full_name, files in extracted.items():
            repo_slug = full_name.replace("/", "_").replace("\\", "_")
            repo_dir = os.path.join(code_dir, repo_slug)
            os.makedirs(repo_dir, exist_ok=True)

            meta = (repo_metadata or {}).get(full_name, {})
            repo_info = {
                "full_name": full_name,
                "url": f"https://github.com/{full_name}",
                "stars": meta.get("stargazers_count", 0),
                "description": meta.get("description", ""),
                "files_count": len(files),
                "files": [],
            }

            for file_info in files:
                file_path = file_info["path"]
                # Create subdirectories if needed
                safe_path = file_path.replace("\\", "/")
                dest_path = os.path.join(repo_dir, safe_path)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)

                content = file_info.get("content", "")
                with open(dest_path, "w", encoding="utf-8", errors="replace") as f:
                    f.write(content)

                repo_info["files"].append({
                    "path": safe_path,
                    "language": file_info.get("language", "text"),
                    "size": len(content),
                    "saved_at": dest_path,
                })

            manifest.append(repo_info)

        # Write manifest
        manifest_path = os.path.join(code_dir, "_manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, default=str)

        return code_dir


__all__ = ["CodeExtractor", "CodeExtractorError"]
