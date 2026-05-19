"""
ARIA v2 — Knowledge Packager Agent
Stitches ALL pipeline artifacts + extracted code into a structured knowledge package.
This is ARIA's final deliverable — a folder you can feed into any coding AI.

Output structure:
  {run_dir}/knowledge_package/
    ├── README.md                   # Package manifest + how to use
    ├── 00_PROBLEM.md               # Problem statement + ideal outcome
    ├── 01_DECOMPOSITION.md         # Sub-problem breakdown
    ├── 02_TOP_REPOS.md             # Ranked repos with analysis
    ├── 03_EXTRACTED_CODE/          # Actual source files from repos
    │   ├── repo_name/
    │   │   ├── path/to/file.py
    │   │   └── ...
    │   └── _manifest.json
    ├── 04_PATTERNS.md              # Architectural patterns
    ├── 05_LIBRARIES.md             # Recommended libraries
    ├── 06_BUILD_PLAN.md            # Implementation phases
    ├── 07_WEB_RESEARCH.md          # Web research findings
    └── 08_RISKS.md                 # Gotchas and anti-patterns
"""

import os
from datetime import datetime
from typing import Any, Optional


class KnowledgePackagerError(Exception):
    """Raised when knowledge packaging fails."""


class KnowledgePackagerAgent:
    """Stitches all pipeline outputs into a structured knowledge package.

    The knowledge package is a self-contained folder with everything needed
    for another AI (Claude Code, Codebuff, etc.) to build the solution.
    """

    def __init__(self):
        self.provider = "groq"  # Lightweight formatting work

    def run(
        self,
        intake_result: dict[str, Any],
        decomposer_result: dict[str, Any],
        web_results: list[dict[str, Any]],
        pattern_result: dict[str, Any],
        brief: str,
        extracted_code_dir: Optional[str] = None,
        output_dir: str = "",
        run_id: str = "",
    ) -> dict[str, Any]:
        """Create the complete knowledge package.

        Args:
            intake_result: From IntakeAgent
            decomposer_result: From DecomposerAgent
            web_results: List of web research results per sub-problem
            pattern_result: From PatternExtractorAgent
            brief: The synthesized research brief (markdown)
            extracted_code_dir: Path to extracted code directory (if any)
            output_dir: Where to create the knowledge package
            run_id: Run identifier

        Returns:
            {status, package_dir, sections_created, error}
        """
        package_dir = os.path.join(output_dir, "knowledge_package")
        os.makedirs(package_dir, exist_ok=True)

        sections_created = []

        # Normalize pattern_result — LLM occasionally returns a list instead of a dict.
        if isinstance(pattern_result, list):
            pattern_result = pattern_result[0] if pattern_result and isinstance(pattern_result[0], dict) else {}
        if not isinstance(pattern_result, dict):
            pattern_result = {}

        # Normalize decomposer_result — orchestrator passes a list of sub_problems directly.
        if isinstance(decomposer_result, list):
            decomposer_result = {"sub_problems": decomposer_result}
        if not isinstance(decomposer_result, dict):
            decomposer_result = {}

        try:
            # 0: README — Package manifest
            self._write_readme(package_dir, intake_result, run_id)

            # 1: Problem statement
            self._write_problem(package_dir, intake_result)

            # 2: Decomposition
            self._write_decomposition(package_dir, decomposer_result)

            # 3: Top repos
            self._write_top_repos(package_dir, pattern_result)

            # 4: Extracted code (copy it into the package)
            if extracted_code_dir and os.path.isdir(extracted_code_dir):
                self._bundle_extracted_code(extracted_code_dir, package_dir)

            # 5: Patterns
            self._write_patterns(package_dir, pattern_result)

            # 6: Libraries
            self._write_libraries(package_dir, pattern_result)

            # 7: Build plan
            self._write_build_plan(package_dir, brief)

            # 8: Web research
            self._write_web_research(package_dir, web_results)

            # 9: Risks
            self._write_risks(package_dir, pattern_result)

            # 10: Copy ARIA_research_brief.md into package dir so it appears in the UI file tree.
            if brief and brief.strip():
                self._write_md(package_dir, "ARIA_research_brief.md", brief)

            # Count sections created
            sections_created = [
                f for f in os.listdir(package_dir)
                if os.path.isfile(os.path.join(package_dir, f)) and f.endswith(".md")
            ]

            return {
                "status": "done",
                "package_dir": package_dir,
                "sections_created": sorted(sections_created),
                "error": None,
            }

        except Exception as e:
            return {
                "status": "failed",
                "package_dir": package_dir,
                "sections_created": sorted(sections_created),
                "error": str(e),
            }

    # ------------------------------------------------------------------ #
    # Section Writers
    # ------------------------------------------------------------------ #

    def _write_readme(self, package_dir: str, intake: dict[str, Any], run_id: str) -> None:
        """Write the package README — manifest and usage instructions."""
        content = f"""# ARIA Knowledge Package

> **Idea:** {intake.get('raw_idea', 'N/A')}
> **Ideal Outcome:** {intake.get('ideal_outcome', 'N/A')}
> **Run ID:** {run_id}
> **Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## What's Inside

This package contains everything ARIA discovered about your problem — ranked
repos, extracted source code, architectural patterns, and a build plan. It's
designed to be fed into any coding AI for implementation.

| # | File | Description |
|---|------|-------------|
| 00 | `00_PROBLEM.md` | Problem statement and ideal outcome |
| 01 | `01_DECOMPOSITION.md` | Sub-problem breakdown |
| 02 | `02_TOP_REPOS.md` | Ranked repositories with analysis |
| 03 | `extracted_code/` | Actual source code from top repos |
| 04 | `04_PATTERNS.md` | Architectural patterns discovered |
| 05 | `05_LIBRARIES.md` | Recommended libraries and tools |
| 06 | `06_BUILD_PLAN.md` | Implementation phases |
| 07 | `07_WEB_RESEARCH.md` | Web research findings |
| 08 | `08_RISKS.md` | Gotchas and anti-patterns |

## How to Use This Package

1. **Review the problem** in `00_PROBLEM.md` to confirm scope
2. **Study the decomposition** in `01_DECOMPOSITION.md` for task breakdown
3. **Read the repo analysis** in `02_TOP_REPOS.md` for reference implementations
4. **Browse extracted code** in `extracted_code/` for real working examples
5. **Follow the build plan** in `06_BUILD_PLAN.md` for implementation order

Feed this entire folder to Claude Code, Codebuff, or any AI coding tool:
```
# Example: using with Claude Code
cat {run_id}/knowledge_package/06_BUILD_PLAN.md | claude

# Example: using with Codebuff
codebuff --context {run_id}/knowledge_package/ "implement this solution"
```

## Metadata

- **Domain:** {', '.join(intake.get('domain', ['N/A']))}
- **Primary Language:** {intake.get('primary_language', 'N/A')}
- **Complexity:** {intake.get('complexity_estimate', 'N/A')}
"""
        self._write_md(package_dir, "README.md", content)

    def _write_problem(self, package_dir: str, intake: dict[str, Any]) -> None:
        """Write the problem statement section."""
        content = f"""# Problem Statement

## The Idea
{intake.get('raw_idea', 'N/A')}

## Ideal Outcome
{intake.get('ideal_outcome', 'N/A')}

## Core Problems to Solve
"""
        for i, problem in enumerate(intake.get("core_problems", []), 1):
            content += f"\n{i}. {problem}"

        content += f"""

## Metadata
- **Domain:** {', '.join(intake.get('domain', ['N/A']))}
- **Primary Language:** {intake.get('primary_language', 'N/A')}
- **Complexity Estimate:** {intake.get('complexity_estimate', 'N/A')}
"""
        self._write_md(package_dir, "00_PROBLEM.md", content)

    def _write_decomposition(self, package_dir: str, decomposer: dict[str, Any]) -> None:
        """Write the sub-problem decomposition section."""
        sub_problems = decomposer.get("sub_problems", [])
        if not sub_problems:
            self._write_md(package_dir, "01_DECOMPOSITION.md", "# Decomposition\n\n*No decomposition data available.*")
            return

        content = "# Problem Decomposition\n\n"
        for sp in sub_problems:
            content += f"""## {sp.get('id', '?')}: {sp.get('title', '?')}

**Description:** {sp.get('description', 'N/A')}

**Why Critical:** {sp.get('why_critical', 'N/A')}

**Search Queries:**
- GitHub: `{', '.join(sp.get('github_search_queries', []))}`
"""
            # Optional fields
            if sp.get("pypi_search_terms"):
                content += f"- PyPI: {', '.join(sp['pypi_search_terms'])}\n"
            if sp.get("npm_search_terms"):
                content += f"- npm: {', '.join(sp['npm_search_terms'])}\n"
            if sp.get("stackoverflow_tags"):
                content += f"- StackOverflow: {', '.join(sp['stackoverflow_tags'])}\n"
            content += "\n---\n\n"

        self._write_md(package_dir, "01_DECOMPOSITION.md", content)

    def _write_top_repos(self, package_dir: str, patterns: dict[str, Any]) -> None:
        """Write the top repos analysis section."""
        repos_to_fork = patterns.get("repos_to_fork", [])
        libraries = patterns.get("libraries_to_use", [])

        content = "# Top Repositories & Code References\n\n"

        if repos_to_fork:
            content += "## Recommended Repos to Study\n\n"
            for repo in repos_to_fork:
                name = repo.get("name", repo.get("repo", "?"))
                url = repo.get("url", f"https://github.com/{name}" if name != "?" else "")
                changes = repo.get("changes_to_implement", repo.get("changes", ""))
                content += f"""### {name}
- **URL:** {url}
- **Why:** {repo.get('why', repo.get('reason', repo.get('description', 'N/A')))}
- **Changes Needed:** {changes}

"""
        else:
            # Try alternative structure
            arch_patterns = patterns.get("architectural_patterns", [])
            if arch_patterns:
                content += "## Reference Repositories\n\n"
                for ap in arch_patterns:
                    content += f"- **{ap.get('name', 'Pattern')}:** {ap.get('description', '')}\n"

        # Add library sources
        if libraries:
            content += "\n## Library Sources\n\n"
            for lib in libraries:
                src = lib.get("source_repo", lib.get("source", lib.get("repo", "")))
                if src:
                    content += f"- **{lib.get('name', lib.get('library', '?'))}** — {src}\n"
                    if lib.get("version"):
                        content += f"  - Version: {lib['version']}\n"

        self._write_md(package_dir, "02_TOP_REPOS.md", content)

    def _write_patterns(self, package_dir: str, patterns: dict[str, Any]) -> None:
        """Write the architectural patterns section."""
        arch_patterns = patterns.get("architectural_patterns", [])
        content = "# Architectural Patterns\n\n"

        if not arch_patterns:
            content += "*No architectural patterns identified.*\n"
        else:
            for p in arch_patterns:
                content += f"""## {p.get('name', 'Pattern')}
{p.get('description', '')}

"""
        self._write_md(package_dir, "04_PATTERNS.md", content)

    def _write_libraries(self, package_dir: str, patterns: dict[str, Any]) -> None:
        """Write the recommended libraries section."""
        libraries = patterns.get("libraries_to_use", [])
        content = "# Recommended Libraries & Tools\n\n"

        if not libraries:
            content += "*No libraries recommended.*\n"
        else:
            content += "| Library | Version | Justification | Source |\n"
            content += "|---------|---------|---------------|--------|\n"
            for lib in libraries:
                src = lib.get("source_repo", lib.get("source", lib.get("repo", "")))
                content += f"""| {lib.get('name', lib.get('library', '?'))} """
                content += f"""| {lib.get('version', 'latest')} """
                content += f"""| {lib.get('justification', lib.get('reason', ''))} """
                content += f"""| {src} |\n"""

        self._write_md(package_dir, "05_LIBRARIES.md", content)

    def _write_build_plan(self, package_dir: str, brief: str) -> None:
        """Write the implementation build plan — extracted from the brief."""
        content = "# Build Plan & Implementation Guide\n\n"

        if not brief.strip() or len(brief) < 100:
            content += "*No build plan available — research brief was empty.*\n"
        else:
            # Just include the full brief — it has the build order baked in
            content += brief

        self._write_md(package_dir, "06_BUILD_PLAN.md", content)

    def _write_web_research(self, package_dir: str, web_results: list[dict[str, Any]]) -> None:
        """Write the web research findings section."""
        content = "# Web Research Findings\n\n"

        if not web_results:
            content += "*No web research data available.*\n"
        else:
            for result in web_results:
                sp_id = result.get("sub_problem_id", "?")
                sp_title = result.get("sub_problem_title", "")
                results_count = result.get("results_count", 0)
                content += f"## {sp_id}: {sp_title}\n\n"
                content += f"**Results found:** {results_count}\n\n"

                for r in result.get("results", []):
                    content += f"""### {r.get('title', 'Untitled')}
- **URL:** {r.get('url', '')}
- **Summary:** {r.get('snippet', 'N/A')}

"""
        self._write_md(package_dir, "07_WEB_RESEARCH.md", content)

    def _write_risks(self, package_dir: str, patterns: dict[str, Any]) -> None:
        """Write the risks, anti-patterns and gotchas section."""
        anti_patterns = patterns.get("anti_patterns", [])
        gotchas = patterns.get("gotchas", [])

        content = "# Risks, Anti-Patterns & Gotchas\n\n"

        if anti_patterns:
            content += "## Anti-Patterns to Avoid\n\n"
            for ap in anti_patterns:
                content += f"""### {ap.get('name', 'Anti-Pattern')}
{ap.get('description', '')}

"""

        if gotchas:
            content += "## Gotchas & Surprises\n\n"
            for g in gotchas:
                content += f"""- **{g.get('title', g.get('name', 'Issue'))}:** {g.get('description', '')}\n"""

        # Performance and security considerations
        perf = patterns.get("performance", patterns.get("performance_considerations", []))
        if perf:
            content += "\n## Performance Considerations\n\n"
            for p in perf:
                content += f"- {p.get('description', p.get('name', str(p)))}\n"

        sec = patterns.get("security", patterns.get("security_considerations", []))
        if sec:
            content += "\n## Security Considerations\n\n"
            for s in sec:
                content += f"- {s.get('description', s.get('name', str(s)))}\n"

        if not anti_patterns and not gotchas:
            content += "*No risks or anti-patterns identified.*\n"

        self._write_md(package_dir, "08_RISKS.md", content)

    def _bundle_extracted_code(self, source_dir: str, package_dir: str) -> None:
        """Copy extracted code into the knowledge package."""
        import shutil
        dest_dir = os.path.join(package_dir, "extracted_code")
        if os.path.isdir(source_dir):
            if os.path.isdir(dest_dir):
                shutil.rmtree(dest_dir)
            shutil.copytree(source_dir, dest_dir, dirs_exist_ok=True)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _write_md(package_dir: str, filename: str, content: str) -> str:
        """Write a markdown file to the package directory."""
        path = os.path.join(package_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")
        return path

    @staticmethod
    def _safe_text(text: Any, max_len: int = 500) -> str:
        """Safely truncate text for display."""
        s = str(text) if text is not None else ""
        if len(s) > max_len:
            return s[:max_len] + "..."
        return s


__all__ = ["KnowledgePackagerAgent", "KnowledgePackagerError"]
