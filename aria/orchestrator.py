"""
ARIA v2 — Orchestrator Module
Research pipeline controller.

Wires all 7 agents together:
1. Intake → 2. Decomposer → [Human Checkpoint]
   → 3. GitHub Researcher (parallel, max 3 concurrent)
   → 4. Web Researcher (parallel, max 3 concurrent)
   → 5. Pattern Extractor → 6. Synthesizer → 7. Quality Judge (gap → re-research loop)

Includes:
- LoopGuard (max steps per agent)
- Budget tracker (max re-research loops)
- Parallel fanout with asyncio.Semaphore(3)
- Human-in-the-loop checkpoint after decomposition
"""

import asyncio
import json
import os
import sys
from typing import Any, Optional

from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt

from agents.decomposer import DecomposerAgent
from agents.github_researcher import GitHubResearchAgent
from agents.intake import IntakeAgent
from agents.knowledge_packager import KnowledgePackagerAgent
from agents.pattern_extractor import PatternExtractorAgent
from agents.quality_judge import QualityJudgeAgent
from agents.synthesizer import SynthesizerAgent
from agents.web_researcher import WebResearchAgent
from config import research
from state import ResearchState
from tools.code_extractor import CodeExtractor
from tools.logger import log
from tools.project_scaffolder import ProjectScaffolder

# ─── Loop Guard ─────────────────────────────────────────────────────────────────

MAX_STEPS_PER_AGENT = 10


class AgentStepLimitReached(RuntimeError):
    """Raised when a LoopGuard exhausts its step budget."""


class LoopGuard:
    """
    Guardrail that prevents agents from running too many steps.

    Each agent gets max_steps ticks. If exceeded, raises AgentStepLimitReached.
    NOTE: Never raises StopIteration — PEP 479 forbids that inside coroutines.
    """

    def __init__(self, name: str, max_steps: int = MAX_STEPS_PER_AGENT):
        self.name = name
        self.steps = 0
        self.max_steps = max_steps

    def tick(self) -> None:
        """Record a step. Raises AgentStepLimitReached if max exceeded."""
        self.steps += 1
        if self.steps >= self.max_steps:
            raise AgentStepLimitReached(
                f"Agent {self.name} hit max step limit ({self.max_steps}). "
                "Summarising partial results and continuing."
            )


# ─── Orchestrator ──────────────────────────────────────────────────────────────

class Orchestrator:
    """
    Research pipeline orchestrator.

    Controls the sequence:
    intake → decompose → [checkpoint] → research (parallel) → patterns
    → synthesize → judge → [re-research if needed, max 2 loops]
    → knowledge package → [build handoff if mode='build']

    Modes:
    - research: Pure research + knowledge package (default)
    - build: Same as research + generates Codebuff handoff prompt
    """

    def __init__(self, idea: str, state: ResearchState, offline: bool = False, focus: Optional[str] = None, mode: str = "research", quiet: bool = False):
        self.idea = idea
        self.state = state
        self.offline = offline
        self.focus = focus
        self.mode = mode
        self.quiet = quiet
        self.semaphore = asyncio.Semaphore(research.max_concurrent_agents)
        self.research_loops = 0
        self.max_research_loops = research.max_research_loops

        # Agent instances
        self.intake_agent = IntakeAgent(offline=offline)
        self.decomposer = DecomposerAgent(offline=offline)
        self.github_researcher = GitHubResearchAgent(offline=offline)
        self.web_researcher = WebResearchAgent()
        self.pattern_extractor = PatternExtractorAgent(offline=offline)
        self.synthesizer = SynthesizerAgent()
        self.quality_judge = QualityJudgeAgent()
        self.knowledge_packager = KnowledgePackagerAgent()
        self.code_extractor = CodeExtractor()
        self.project_scaffolder = ProjectScaffolder()

    async def run(self) -> dict[str, Any]:
        """
        Run the full research pipeline.

        Returns:
            Dict with final brief path and quality score
        """
        result = {
            "run_id": self.state.run_id,
            "idea": self.idea,
            "output_path": str(self.state.base_path / "ARIA_research_brief.md"),
        }

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            console=log.console,
            disable=self.quiet,
        ) as progress:

            # 🟢 Step 1: Intake
            task1 = progress.add_task("[cyan]1/7 Intake Agent...", total=1)
            intake_result = await self._run_intake()
            progress.update(task1, completed=1)

            # 🟢 Step 2: Decomposer
            task2 = progress.add_task("[cyan]2/7 Decomposition Agent...", total=1)
            decomposition = await self._run_decomposer(intake_result)
            progress.update(task2, completed=1)

            # 🟢 Human checkpoint
            if research.enable_human_checkpoint:
                progress.stop()
                if not self._human_checkpoint(decomposition):
                    log.warning("Research cancelled by user.")
                    result["status"] = "cancelled"
                    return result
                progress.start()

            # 🟢 Steps 3-4: GitHub + Web Research (parallel, max 3 concurrent)
            task3 = progress.add_task(
                f"[cyan]3/7 GitHub Research ({len(decomposition)} sub-problems)...",
                total=len(decomposition),
            )

            github_findings = await self._run_github_research(decomposition, intake_result, progress, task3)

            web_findings = []
            if research.enable_web_research:
                task4 = progress.add_task(
                    f"[cyan]4/7 Web Research ({len(decomposition)} sub-problems)...",
                    total=len(decomposition),
                )
                web_findings = await self._run_web_research(decomposition, intake_result, progress, task4)

            # 🟢 Step 5: Pattern Extraction
            task5 = progress.add_task("[cyan]5/7 Pattern Extraction...", total=1)
            patterns = await self._run_pattern_extraction(github_findings, web_findings, intake_result)
            progress.update(task5, completed=1)

            # 🟢 Step 6: Synthesizer
            task6 = progress.add_task("[cyan]6/7 Synthesis Agent...", total=1)
            brief = await self._run_synthesis(intake_result, decomposition, github_findings, web_findings, patterns)
            progress.update(task6, completed=1)

            # 🟢 Step 7: Quality Judge + re-research loop
            task7 = progress.add_task("[cyan]7/7 Quality Judge...", total=1)
            quality = await self._run_quality_judge(brief, intake_result)
            progress.update(task7, completed=1)

            # Re-research loop
            while quality.get("verdict") == "RE_RESEARCH" and self.research_loops < self.max_research_loops:
                self.research_loops += 1
                log.info(f"[yellow]🔄 Re-research loop {self.research_loops}/{self.max_research_loops}[/yellow]")

                # Enrich sub-problems with gap directives so researchers target missing areas
                directives = quality.get("re_research_directives", [])
                if directives:
                    enriched_sps = []
                    for sp in decomposition:
                        sp_copy = dict(sp)
                        extra = [f"{sp.get('title', '')} {d}" for d in directives[:3]]
                        sp_copy["github_search_queries"] = list(sp.get("github_search_queries", [])) + extra
                        sp_copy["web_queries"] = list(sp.get("web_queries", [])) + extra
                        enriched_sps.append(sp_copy)
                else:
                    enriched_sps = decomposition

                # force_refresh=True bypasses cached checkpoints from the first pass
                new_github = await self._run_github_research(enriched_sps, intake_result, progress, task3, force_refresh=True)
                github_findings.extend(new_github)

                # Deduplicate repos by full_name to avoid token waste on re-research
                seen_repos = set()
                deduped_findings = []
                for gf in github_findings:
                    if isinstance(gf, dict):
                        all_repos = gf.get("all_repos", [])
                        if isinstance(all_repos, list):
                            deduped = []
                            for repo in all_repos:
                                name = repo.get("full_name", "")
                                if name not in seen_repos:
                                    seen_repos.add(name)
                                    deduped.append(repo)
                            gf["all_repos"] = deduped
                            deduped_findings.append(gf)
                github_findings = deduped_findings

                if research.enable_web_research:
                    new_web = await self._run_web_research(enriched_sps, intake_result, progress, task4, force_refresh=True)
                    web_findings.extend(new_web)

                new_patterns = await self._run_pattern_extraction(github_findings, web_findings, intake_result, force_refresh=True)
                # Merge arrays so re-research accumulates rather than overwrites
                for key, val in new_patterns.items():
                    if isinstance(val, list) and isinstance(patterns.get(key), list):
                        seen = {str(x) for x in patterns[key]}
                        patterns[key] = patterns[key] + [x for x in val if str(x) not in seen]
                    elif val:  # only overwrite scalars/dicts if new value is non-empty
                        patterns[key] = val

                brief = await self._run_synthesis(intake_result, decomposition, github_findings, web_findings, patterns)
                quality = await self._run_quality_judge(brief, intake_result, previous_judgements=[quality])

            # Save final brief
            brief_path = self.state.base_path / "ARIA_research_brief.md"
            brief_path.write_text(brief, encoding="utf-8")

            # Save quality judgement
            self.state.checkpoint("quality_judge", quality)

            # 🟢 Step 8: Knowledge Package — stitch everything into a structured folder
            task8 = progress.add_task("[cyan]8/8 Building Knowledge Package...", total=1)
            package_result = await self._run_knowledge_packager(
                intake_result=intake_result,
                decomposition=decomposition,
                github_findings=github_findings,
                web_findings=web_findings,
                patterns=patterns,
                brief=brief,
            )
            progress.update(task8, completed=1)

            if package_result.get("status") == "done":
                log.info(f"[dim]  📦 Knowledge package: {package_result['package_dir']}[/dim]")
                sections = package_result.get("sections_created", [])
                if sections:
                    log.info(f"[dim]  📄 Sections: {', '.join(sections)}[/dim]")

        # ─── Final Output ──────────────────────────────────────────────
        score = quality.get("overall_score", 0)
        verdict = quality.get("verdict", "UNKNOWN")

        result["status"] = "complete"
        result["quality_score"] = score
        result["verdict"] = verdict
        result["research_loops"] = self.research_loops + 1
        result["package_dir"] = package_result.get("package_dir", "") if isinstance(package_result, dict) else ""
        result["sections_created"] = package_result.get("sections_created", []) if isinstance(package_result, dict) else []
        # Propagate scaffold results (set in _run_knowledge_packager for build mode)
        result["scaffold_dir"] = package_result.get("scaffold_dir", "") if isinstance(package_result, dict) else ""
        result["scaffold_files"] = package_result.get("scaffold_files", []) if isinstance(package_result, dict) else []
        result["scaffold_language"] = package_result.get("scaffold_language", "") if isinstance(package_result, dict) else ""

        log.panel(
            "ARIA Results",
            f"[bold]Research Complete![/bold]\n\n"
            f"📁 Output: {result['output_path']}\n"
            f"⭐ Quality Score: {score}/10\n"
            f"🎯 Verdict: {self._verdict_icon(verdict)} {verdict}\n"
            f"🔄 Research loops: {result['research_loops']}\n"
            f"[dim]Feed this brief to Claude Code to start building.[/dim]",
            style="green" if score >= 7 else "yellow",
        )

        return result

    async def _run_intake(self) -> dict[str, Any]:
        """Step 1: Run Intake Agent."""
        guard = LoopGuard("intake")
        guard.tick()

        if self.state.is_done("intake"):
            result = self.state.load("intake")
            log.info("[dim]📦 Intake loaded from checkpoint[/dim]")
            return result or {}

        log.info(f"[bold]🧪 Analysing:[/bold] {self.idea}")
        result = await self.intake_agent.run(self.idea)

        self.state.checkpoint("intake", result)
        log.info(f"[dim]✅ Ideal outcome: {result.get('ideal_outcome', '')[:80]}...[/dim]")
        return result

    async def _run_decomposer(self, intake_result: dict[str, Any]) -> list[dict[str, Any]]:
        """Step 2: Run Decomposer Agent."""
        guard = LoopGuard("decomposer")
        guard.tick()

        if self.state.is_done("decomposer"):
            result = self.state.load("decomposer")
            log.info("[dim]📦 Decomposition loaded from checkpoint[/dim]")
            return result if isinstance(result, list) else result.get("sub_problems", [])

        result = await self.decomposer.run(intake_result)

        # Ensure we save as a clean list
        sub_problems = result if isinstance(result, list) else result.get("sub_problems", [])
        self.state.checkpoint("decomposer", {"sub_problems": sub_problems})

        log.info(f"[dim]✅ Decomposed into {len(sub_problems)} sub-problems[/dim]")
        for sp in sub_problems:
            log.info(f"  • {sp.get('id', '?')}: {sp.get('title', '')}")
        return sub_problems

    def _human_checkpoint(self, sub_problems: list[dict[str, Any]]) -> bool:
        """Human-in-the-loop checkpoint after decomposition."""
        log.info("[bold cyan]📋 Proposed Sub-Problems:[/bold cyan]")
        for sp in sub_problems:
            log.info(f"  [bold]{sp.get('id', '?')}[/bold]: {sp.get('title', '')}")
            log.info(f"       {sp.get('description', '')}")

        # Auto-continue in non-interactive mode (no TTY)
        if not sys.stdin.isatty():
            log.info("[dim]Non-interactive mode — auto-continuing...[/dim]")
            return True

        log.info("[bold]Proceed with research?[/bold]")
        try:
            response = Prompt.ask("", choices=["Y", "n", "edit"], default="Y")
            if response.lower() == "n":
                return False
            if response.lower() == "edit":
                log.warning("Edit mode: Modify decomposition.json and re-run with --resume")
        except (EOFError, KeyboardInterrupt):
            log.warning("No input available — auto-continuing...")
        return True

    async def _run_github_research(
        self,
        sub_problems: list[dict[str, Any]],
        intake_result: dict[str, Any],
        progress: Progress,
        task,
        force_refresh: bool = False,
    ) -> list[dict[str, Any]]:
        """Steps 3: Run GitHub Research in parallel (max 3 concurrent)."""
        guard = LoopGuard("github_researcher", max_steps=len(sub_problems) + 2)

        async def research_one(sp: dict[str, Any]) -> dict[str, Any]:
            async with self.semaphore:
                guard.tick()
                sp_id = sp.get("id", "")
                if not force_refresh and self.state.is_done(f"github_{sp_id}"):
                    result = self.state.load(f"github_{sp_id}")
                else:
                    result = await self.github_researcher.run(sp, intake_result)
                    self.state.checkpoint(f"github_{sp_id}", result)
                progress.update(task, advance=1)
                return result

        tasks = [research_one(sp) for sp in sub_problems]
        raw = await asyncio.gather(*tasks, return_exceptions=True)

        results = []
        for sp, r in zip(sub_problems, raw):
            if isinstance(r, Exception):
                log.warning(
                    f"[red]⚠️  GitHub research FAILED for {sp.get('id', '?')} "
                    f"({sp.get('title', '')}): {type(r).__name__}: {r}[/red]"
                )
                results.append({
                    "sub_problem_id": sp.get("id", ""),
                    "sub_problem_title": sp.get("title", ""),
                    "repos_found": 0,
                    "repos_scored": 0,
                    "repos_deep_dived": 0,
                    "all_repos": [],
                    "deep_dive_results": [],
                    "error": str(r),
                })
            else:
                results.append(r)
        return results

    async def _run_web_research(
        self,
        sub_problems: list[dict[str, Any]],
        intake_result: dict[str, Any],
        progress: Progress,
        task,
        force_refresh: bool = False,
    ) -> list[dict[str, Any]]:
        """Steps 4: Run Web Research in parallel."""
        guard = LoopGuard("web_researcher", max_steps=len(sub_problems) + 2)

        async def research_one(sp: dict[str, Any]) -> dict[str, Any]:
            async with self.semaphore:
                guard.tick()
                sp_id = sp.get("id", "")
                if not force_refresh and self.state.is_done(f"web_{sp_id}"):
                    result = self.state.load(f"web_{sp_id}")
                else:
                    result = await self.web_researcher.run(sp, intake_result)
                    self.state.checkpoint(f"web_{sp_id}", result)
                progress.update(task, advance=1)
                return result

        tasks = [research_one(sp) for sp in sub_problems]
        raw = await asyncio.gather(*tasks, return_exceptions=True)

        results = []
        for sp, r in zip(sub_problems, raw):
            if isinstance(r, Exception):
                log.warning(
                    f"[red]⚠️  Web research FAILED for {sp.get('id', '?')} "
                    f"({sp.get('title', '')}): {type(r).__name__}: {r}[/red]"
                )
                results.append({
                    "sub_problem_id": sp.get("id", ""),
                    "sub_problem_title": sp.get("title", ""),
                    "insights": [],
                    "error": str(r),
                })
            else:
                results.append(r)
        return results

    async def _run_pattern_extraction(
        self,
        github_findings: list[dict[str, Any]],
        web_findings: list[dict[str, Any]],
        intake_result: dict[str, Any],
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        """Step 5: Run Pattern Extractor."""
        guard = LoopGuard("pattern_extractor")
        guard.tick()

        if not force_refresh and self.state.is_done("pattern_extractor"):
            result = self.state.load("pattern_extractor")
            return result or {}

        # Filter out exceptions
        valid_github = [g for g in github_findings if isinstance(g, dict)]
        valid_web = [w for w in web_findings if isinstance(w, dict)]

        result = await self.pattern_extractor.run(valid_github, valid_web, intake_result)
        self.state.checkpoint("pattern_extractor", result)
        return result

    async def _run_synthesis(
        self,
        intake_result: dict[str, Any],
        decomposition: list[dict[str, Any]],
        github_findings: list[dict[str, Any]],
        web_findings: list[dict[str, Any]],
        patterns: dict[str, Any],
    ) -> str:
        """Step 6: Run Synthesis Agent."""
        guard = LoopGuard("synthesizer")
        guard.tick()

        if self.state.is_done("synthesizer"):
            cached = self.state.load("synthesizer")
            if cached and isinstance(cached, dict) and "brief" in cached:
                return cached["brief"]

        valid_github = [g for g in github_findings if isinstance(g, dict)]
        valid_web = [w for w in web_findings if isinstance(w, dict)]

        brief = await self.synthesizer.run(intake_result, decomposition, valid_github, valid_web, patterns)
        self.state.checkpoint("synthesizer", {"brief": brief})
        return brief

    async def _run_quality_judge(
        self,
        brief: str,
        intake_result: dict[str, Any],
        previous_judgements: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """Step 7: Run Quality Judge."""
        guard = LoopGuard("quality_judge")
        guard.tick()

        return await self.quality_judge.run(brief, intake_result, previous_judgements)

    async def _run_knowledge_packager(
        self,
        intake_result: dict[str, Any],
        decomposition: dict[str, Any],
        github_findings: list[dict[str, Any]],
        web_findings: list[dict[str, Any]],
        patterns: dict[str, Any],
        brief: str,
    ) -> dict[str, Any]:
        """
        Step 8: Build knowledge package + optionally generate project scaffold.

        In research mode: standard knowledge package with extracted code.
        In build mode: deeper code extraction + starter project scaffold.
        """
        try:
            # Extract code from top repos identified by pattern extractor
            repos_to_extract = []
            for repo in patterns.get("repos_to_fork", []):
                name = repo.get("name", repo.get("repo", ""))
                if name and "/" in str(name):
                    repos_to_extract.append({
                        "full_name": name,
                        "language": repo.get("language", ""),
                        "description": repo.get("description", ""),
                    })

            # Build mode: deeper extraction (more files, more repos)
            is_build = self.mode == "build"
            extracted_code_dir = None
            if repos_to_extract:
                files_per_repo = 25 if is_build else 15
                max_repos = 10 if is_build else 5
                extracted = await self.code_extractor.extract_top_repos(
                    repos_to_extract,
                    max_files_per_repo=files_per_repo,
                    max_repos=max_repos,
                )
                if extracted:
                    repo_metadata = {r["full_name"]: r for r in repos_to_extract}
                    extracted_code_dir = await self.code_extractor.save_extracted_code(
                        extracted,
                        str(self.state.base_path),
                        repo_metadata=repo_metadata,
                    )

            # Build knowledge package
            result = self.knowledge_packager.run(
                intake_result=intake_result,
                decomposer_result=decomposition,
                web_results=web_findings,
                pattern_result=patterns,
                brief=brief,
                extracted_code_dir=extracted_code_dir,
                output_dir=str(self.state.base_path),
                run_id=self.state.run_id,
            )

            # Populate extracted_repos from manifest (for PackageScreen)
            extracted_repos = []
            package_files = []
            if extracted_code_dir and os.path.isdir(extracted_code_dir):
                manifest_path = os.path.join(extracted_code_dir, "_manifest.json")
                if os.path.isfile(manifest_path):
                    try:
                        with open(manifest_path) as f:
                            manifest = json.load(f)
                        for entry in manifest:
                            langs = set()
                            for pf in entry.get("files", []):
                                if pf.get("language"):
                                    langs.add(pf["language"])
                            extracted_repos.append({
                                "full_name": entry.get("full_name", ""),
                                "why": entry.get("description", ""),
                                "language": next(iter(langs)) if langs else "",
                                "stars": entry.get("stars", 0),
                                "files": entry.get("files_count", 0),
                            })
                            for pf in entry.get("files", []):
                                package_files.append({
                                    "name": pf.get("path", ""),
                                    "kind": "file",
                                    "size": pf.get("size", 0),
                                    "folder": entry.get("full_name", "extracted"),
                                })
                    except (json.JSONDecodeError, OSError):
                        pass

            # Also add markdown files from the knowledge package directory
            pkg_dir = result.get("package_dir", "")
            if pkg_dir and os.path.isdir(pkg_dir):
                for fname in os.listdir(pkg_dir):
                    fpath = os.path.join(pkg_dir, fname)
                    if os.path.isfile(fpath):
                        package_files.append({
                            "name": fname,
                            "kind": "file",
                            "size": os.path.getsize(fpath),
                            "folder": "",
                        })

            result["extracted_repos"] = extracted_repos
            result["package_files"] = package_files

            # Build mode: generate starter project scaffold
            if is_build:
                scaffold_result = await self.project_scaffolder.scaffold(
                    output_dir=result.get("package_dir", str(self.state.base_path)),
                    intake_result=intake_result,
                    patterns=patterns,
                    brief=brief,
                    extracted_code_dir=extracted_code_dir,
                )
                if scaffold_result.get("status") == "done":
                    result["scaffold_dir"] = scaffold_result["project_dir"]
                    result["scaffold_files"] = scaffold_result["created_files"]
                    result["scaffold_language"] = scaffold_result["language"]
                    log.info(f"[dim]  🏗️  Project scaffold: {scaffold_result['project_dir']}[/dim]")
                    log.info(f"[dim]  📄 {len(scaffold_result['created_files'])} files created[/dim]")

            self.state.checkpoint("knowledge_package", result)
            return result
        except Exception as e:
            log.warning(f"⚠️ Knowledge package error: {e}")
            return {"status": "failed", "package_dir": str(self.state.base_path / "knowledge_package"), "error": str(e)}

    @staticmethod
    def _verdict_icon(verdict: str) -> str:
        icons = {
            "SHIP": "🚀",
            "NEEDS_GAPS_FILLED": "📝",
            "RE_RESEARCH": "🔄",
        }
        return icons.get(verdict, "❓")


# ─── Pipeline Entry Point ──────────────────────────────────────────────────────

async def run_pipeline(
    idea: str,
    state: ResearchState,
    offline: bool = False,
    focus: Optional[str] = None,
    mode: str = "research",
    quiet: bool = False,
) -> dict[str, Any]:
    """
    Entry point for the research pipeline.

    Args:
        idea: Raw idea string
        state: ResearchState instance (checkpoint/resume)
        offline: If True, use Ollama only
        focus: Optional comma-separated focus areas
        mode: "research" (default) or "build" (generates Codebuff handoff)
        quiet: If True, suppress Rich live progress display (use when running in a background thread)

    Returns:
        Dict with run results
    """
    orchestrator = Orchestrator(idea, state, offline=offline, focus=focus, mode=mode, quiet=quiet)
    return await orchestrator.run()
