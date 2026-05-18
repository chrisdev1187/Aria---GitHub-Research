#!/usr/bin/env python3
"""
ARIA v2 — Agentic Research Intelligence Architecture
Deep Code Research System CLI

Usage:
    python main.py "build a CLI tool that monitors GitHub repos for new releases"
    python main.py "make it so users can chat with their PDFs" --dry-run
    python main.py "build an auth system" --offline
    python main.py "create a data pipeline" --deep --resume
"""

import asyncio
import os
import pathlib
import re
import sys
import traceback
from typing import Optional

# Windows encoding fix: ensure UTF-8 for Rich library output
if sys.platform == "win32":
    sys.stdin.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    os.environ["PYTHONIOENCODING"] = "utf-8"

import typer
from rich import box
from rich.table import Table

from config import PROVIDER_MODELS, hardware, research
from provider_pool import pool as provider_pool
from state import ResearchState
from tools.logger import log

# Ensure the aria directory is on the path
sys.path.insert(0, str(pathlib.Path(__file__).parent))

app = typer.Typer(
    name="aria",
    help="ARIA v2 — Agentic Research Intelligence Architecture",
    add_completion=False,
    rich_markup_mode="rich",
)



# ─── Utility Functions ─────────────────────────────────────────────────────────

def calculate_api_estimate(idea: str) -> dict:
    """
    Estimate API calls without running any models.

    Returns a dict with estimated call counts per provider and total runtime.
    """
    sub_problems = max(3, min(7, len(idea.split()) // 5))
    repos_per_sp = max(3, min(10, sub_problems + 2))

    return {
        "groq": 2 + 1,  # intake + decomposer + quality judge
        "deepseek": sub_problems * 2,  # batch score + deep dive per SP
        "siliconflow": sub_problems if research.enable_web_research else 0,
        "nvidia": 1,  # synthesizer
        "github_api": sub_problems * repos_per_sp + sub_problems,  # search + fetches
        "jina": sub_problems * 3 if research.enable_web_research else 0,
        "gemini": sub_problems,  # large file reads only
        "total_calls": 0,  # calculated below
        "minutes": 0,
        "risk": "low",
    }


def print_banner() -> None:
    """Display the ARIA banner."""
    banner = """
+====================================================================+
|                                                                    |
|   ARIA v2 - Agentic Research Intelligence Architecture             |
|   Deep Code Research System                                        |
|   By chrisdev1187 | Nagasubramanian Methodology                   |
|                                                                    |
+====================================================================+
    """
    log.banner(banner, style="bold cyan")


def print_provider_status() -> None:
    """Show configured providers and their status."""
    table = Table(title="Provider Status", box=box.ROUNDED)
    table.add_column("Provider", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Model", style="yellow")
    table.add_column("Keys", style="blue")

    for provider, status_text in provider_pool.get_provider_status().items():
        model = PROVIDER_MODELS.get(provider, "—")
        keys = len(provider_pool._key_pools.get(provider, []))
        table.add_row(provider, status_text, model, str(keys))

    log.console.print(table)


def print_hardware_warning() -> None:
    """Display hardware warnings if RAM is tight."""
    warning = hardware.warn_if_tight()
    if warning:
        log.warning(warning)


# ─── CLI Commands ──────────────────────────────────────────────────────────────

@app.callback()
def callback():
    """ARIA v2 — Deep Code Research System"""
    pass


@app.command()
def run(
    idea: str = typer.Argument(
        ...,
        help="The idea or problem to research in plain English",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Estimate API calls without running any models",
    ),
    deep: bool = typer.Option(
        False,
        "--deep",
        help="Use Qwen 7B locally (requires ~5.5GB RAM, use with caution)",
    ),
    offline: bool = typer.Option(
        False,
        "--offline",
        help="Ollama-only mode — no cloud API calls. Use for privacy-sensitive research.",
    ),
    resume: Optional[str] = typer.Option(
        None,
        "--resume",
        help="Resume from a previous run ID (e.g., 20250101_120000_build_a_cli)",
    ),
    focus: Optional[str] = typer.Option(
        None,
        "--focus",
        help="Comma-separated focus areas (e.g., 'security,performance,scalability')",
    ),
    mode: str = typer.Option(
        "research",
        "--mode",
        help="Operation mode: 'research' (pure research + knowledge package) or 'build' (research + Codebuff handoff)",
    ),
):
    """
    Research a technical idea deeply using multi-provider AI analysis.

    Two modes:
    - RESEARCH (default): Runs the pipeline, produces a knowledge package with
      repos, patterns, extracted code, and build plan.
    - BUILD: Same research pipeline + generates a build-ready prompt file
      and a Codebuff handoff command to build from the knowledge package.
    """
    print_banner()

    # Validate mode
    if mode not in ("research", "build"):
        log.error(f"❌ Error: Mode must be 'research' or 'build'. Got '{mode}'.")
        raise typer.Exit(1)

    if mode == "build":
        log.info("[bold green]🔧 Build mode: Research + Codebuff handoff[/bold green]")

    # Set hardware config
    hardware.use_deep_model = deep
    hardware.use_offline_mode = offline

    # Validate idea length
    if len(idea.strip()) < 20:
        log.error(
            "❌ Error: Idea must be at least 20 characters. "
            "Please provide more detail about what you want to build.\n"
            "[dim]Example: 'build a CLI tool that monitors GitHub repos for new releases "
            "and sends Slack notifications'[/dim]"
        )
        raise typer.Exit(1)

    # ─── Dry Run Mode ──────────────────────────────────────────────────
    if dry_run:
        estimate = calculate_api_estimate(idea)

        total = sum(v for k, v in estimate.items() if isinstance(v, int) and k != "total_calls")
        estimate["total_calls"] = total
        estimate["minutes"] = max(1, total // 20)

        # Risk assessment
        if total > 200:
            estimate["risk"] = "high"
        elif total > 100:
            estimate["risk"] = "medium"

        log.panel(
            "ARIA Dry Run",
            f"[bold]📋 Dry Run Estimate for:[/bold]\n{idea}\n\n"
            f"[bold]Groq calls:[/bold]      ~{estimate['groq']}\n"
            f"[bold]DeepSeek calls:[/bold]  ~{estimate['deepseek']}\n"
            f"[bold]NVIDIA calls:[/bold]    ~{estimate['nvidia']}\n"
            f"[bold]SiliconFlow calls:[/bold] ~{estimate['siliconflow']}\n"
            f"[bold]GitHub API:[/bold]      ~{estimate['github_api']} requests\n"
            f"[bold]Jina fetches:[/bold]    ~{estimate['jina']}\n"
            f"[bold]Gemini reads:[/bold]    ~{estimate['gemini']} (large files only)\n\n"
            f"[bold]Estimated runtime:[/bold] ~{estimate['minutes']} minutes\n"
            f"[bold]Rate limit risk:[/bold]  {'🟢 LOW' if estimate['risk'] == 'low' else '🟡 MEDIUM' if estimate['risk'] == 'medium' else '🔴 HIGH'}\n"
            f"[bold]Offline mode:[/bold]     {'🔴 YES (no cloud calls)' if offline else '🟢 NO (cloud providers active)'}",
            style="cyan",
        )

        # Show provider status
        print_provider_status()
        raise typer.Exit()

    # ─── Offline Mode Check ────────────────────────────────────────────
    if offline:
        log.warning("🔌 Offline mode: Using Ollama only (no cloud API calls)")
        log.info(f"[dim]Local model: {hardware.ollama_qwen3b_gb} (~{hardware.ollama_qwen3b_gb}GB RAM)[/dim]")

    # ─── Hardware Warnings ─────────────────────────────────────────────
    print_hardware_warning()

    # ─── Initialize State ──────────────────────────────────────────────
    state = ResearchState(idea, resume_id=resume)

    if resume:
        log.info(f"[bold green]📂 Resuming run:[/bold green] {state.run_id}")
        log.info(state.summary())
    else:
        log.info(f"[bold green]📁 New run:[/bold green] {state.run_id}")
        log.info(f"[dim]Output directory: {state.base_path}[/dim]")

    if focus:
        log.info(f"[bold]🎯 Focus areas:[/bold] {focus}")

    log.info(f"[bold]🧪 Testing idea:[/bold] {idea}")

    # ─── Show Provider Status ──────────────────────────────────────────
    if not offline:
        print_provider_status()

    # ─── Pipeline Execution ────────────────────────────────────────────
    log.info("[bold cyan]🚀 Starting research pipeline...[/bold cyan]")

    result = asyncio.run(_run_pipeline(idea=idea, state=state, offline=offline, focus=focus, mode=mode))
    log.info("[green]✅ Research complete![/green]")

    # Show knowledge package path
    if result and isinstance(result, dict):
        pkg_dir = result.get("package_dir", "")
        if pkg_dir:
            log.info(f"[bold green]📦 Knowledge package:[/bold green] {pkg_dir}")
            log.info("  [dim]Feed this folder to any coding AI to build the solution.[/dim]")
        quality = result.get("quality_score")
        if quality is not None:
            log.info(f"[bold]⭐ Quality Score:[/bold] {quality}/10")
        verdict = result.get("verdict", "")
        if verdict:
            log.info(f"[bold]🎯 Verdict:[/bold] {verdict}")

        # ─── Build Mode ────────────────────────────────────────────────
        if mode == "build":
            # Show scaffold results
            scaffold_dir = result.get("scaffold_dir", "")
            scaffold_files = result.get("scaffold_files", [])
            scaffold_lang = result.get("scaffold_language", "")
            if scaffold_dir:
                log.info(f"[bold green]🏗️  Starter project scaffold:[/bold green] {scaffold_dir}")
                log.info(f"  [dim]Language: {scaffold_lang}[/dim]")
                log.info(f"  [dim]Files created ({len(scaffold_files)}):[/dim]")
                for f in scaffold_files[:15]:
                    log.info(f"    📄 {f}")
                if len(scaffold_files) > 15:
                    log.info(f"    ... and {len(scaffold_files) - 15} more")
                log.info("\n  [dim]Feed this project folder to Codebuff / Claude Code to start building.[/dim]")

            # Generate build handoff prompt
            build_prompt_path = _generate_build_prompt(result, idea)
            if build_prompt_path:
                log.info(f"[bold green]🔧 Build handoff file:[/bold green] {build_prompt_path}")
                log.info("[bold cyan]To build, feed this prompt to Codebuff:[/bold cyan]")
                log.info(f"  [dim]codebuff @{build_prompt_path}[/dim]")
                log.info("[dim]Or copy the prompt file into your conversation with Claude Code, ChatGPT, etc.[/dim]")


@app.command()
def status():
    """Show provider configuration status and hardware info."""
    print_banner()
    print_provider_status()

    # Hardware info
    table = Table(title="Hardware Profile", box=box.ROUNDED)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total RAM", f"{hardware.total_ram_gb}GB")
    table.add_row("Available (after OS + Python)", f"{hardware.available_ram_gb:.1f}GB")
    table.add_row("Default Ollama Model", f"{PROVIDER_MODELS['ollama_default']} (~{hardware.ollama_qwen3b_gb}GB)")
    table.add_row("Max Concurrent Tasks", str(hardware.max_concurrent_tasks))
    table.add_row("Headroom (Qwen 3B)", f"{hardware.headroom_gb:.1f}GB {'✅' if hardware.headroom_gb >= 0.5 else '⚠️'}")
    table.add_row("Headroom (Qwen 7B)", f"{(hardware.available_ram_gb - hardware.ollama_qwen7b_gb):.1f}GB {'✅' if hardware.can_run_qwen7b else '❌'}")
    log.console.print(table)


@app.command()
def providers():
    """Show detailed provider and rate limit information."""
    print_banner()

    # Rate limits table
    table = Table(title="Rate Limits", box=box.ROUNDED)
    table.add_column("Provider", style="cyan")
    table.add_column("Per Key RPM", style="green")
    table.add_column("Keys", style="blue")
    table.add_column("Pool RPM", style="yellow")

    provider_rpm = {
        "groq": {"per_key": 28, "keys": 4},
        "deepseek": {"per_key": 58, "keys": 2},
        "sambanova": {"per_key": 18, "keys": 2},
        "siliconflow": {"per_key": 28, "keys": 2},
        "nvidia": {"per_key": 18, "keys": 2},
        "cerebras": {"per_key": 28, "keys": 1},
        "gemini": {"per_key": 13, "keys": 1},
    }

    for provider, info in provider_rpm.items():
        table.add_row(
            provider,
            str(info["per_key"]),
            str(info["keys"]),
            str(info["per_key"] * info["keys"]),
        )

    log.console.print(table)
    log.info("[dim]Total effective pool RPM: ~430 RPM[/dim]")


@app.command()
def health():
    """
    Show system health: provider status, log path, and active log file.

    Useful for checking whether the system is healthy before starting a run.
    Logs are written to the run's output directory when a run is active.
    """
    log.banner(
        "+====================================================================+\n"
        "|                                                                    |\n"
        "|   ARIA v2 — System Health                                         |\n"
        "|   Provider status, log path, and diagnostics                       |\n"
        "|                                                                    |\n"
        "+====================================================================+",
        style="bold cyan",
    )

    # Provider health
    print_provider_status()

    # Log file info
    log.info(f"[bold]Log file:[/bold] {log.get_log_path()}")

    # Rate limit info
    provider_rpm = {
        "groq": {"per_key": 28, "keys": 4},
        "deepseek": {"per_key": 58, "keys": 2},
        "sambanova": {"per_key": 18, "keys": 2},
        "siliconflow": {"per_key": 28, "keys": 2},
        "nvidia": {"per_key": 18, "keys": 2},
        "cerebras": {"per_key": 28, "keys": 1},
        "gemini": {"per_key": 13, "keys": 1},
    }
    total_rpm = sum(v["per_key"] * v["keys"] for v in provider_rpm.values())
    log.info(f"[bold]Total pool RPM:[/bold] ~{total_rpm}")

    # Hardware health
    print_hardware_warning()
    # Check if a home directory log exists
    home_log = os.path.join(os.path.expanduser("~"), ".aria", "aria.log")
    if os.path.exists(home_log):
        log.info(f"[dim]Persistent log: {home_log}[/dim]")


@app.command()
def serve(
    port: int = typer.Option(
        8080,
        "--port", "-p",
        help="Port to serve the UI on",
    ),
    open_browser: bool = typer.Option(
        True,
        "--open/--no-open",
        help="Open the browser automatically",
    ),
):
    """
    Launch the ARIA UI dashboard.

    Serves the React-based research dashboard with live API endpoints
    so the UI shows real-time pipeline progress instead of mock data.
    """
    import asyncio
    import json
    import os as _os
    import re as _re
    import socket
    import threading
    import time as _time
    import webbrowser
    from datetime import datetime
    from http.server import HTTPServer, SimpleHTTPRequestHandler

    import state as state_module
    from tools.run_context import run_context

    ui_dir = pathlib.Path(__file__).parent / "UI"
    if not ui_dir.exists():
        log.error(f"❌ UI directory not found at {ui_dir}")
        raise typer.Exit(1)

    # ---- hardware info helper (cached 30 s) ----
    _hw_cache: dict = {"data": None, "ts": 0.0}

    def _get_hardware_info() -> dict:
        total_gb = hardware.total_ram_gb
        avail_gb = hardware.available_ram_gb
        try:
            import ctypes
            class _MEM(ctypes.Structure):
                _fields_ = [
                    ("dwLength",                ctypes.c_ulong),
                    ("dwMemoryLoad",             ctypes.c_ulong),
                    ("ullTotalPhys",             ctypes.c_ulonglong),
                    ("ullAvailPhys",             ctypes.c_ulonglong),
                    ("ullTotalPageFile",         ctypes.c_ulonglong),
                    ("ullAvailPageFile",         ctypes.c_ulonglong),
                    ("ullTotalVirtual",          ctypes.c_ulonglong),
                    ("ullAvailVirtual",          ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            m = _MEM()
            m.dwLength = ctypes.sizeof(m)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            total_gb = round(m.ullTotalPhys / 1024 ** 3, 1)
            avail_gb = round(m.ullAvailPhys / 1024 ** 3, 1)
        except Exception:
            pass

        ollama_running = False
        ollama_models: list[str] = []
        try:
            import requests as _req
            _base = _os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
            _r = _req.get(f"{_base}/api/tags", timeout=2)
            if _r.status_code == 200:
                ollama_running = True
                ollama_models = [m["name"] for m in _r.json().get("models", [])]
        except Exception:
            pass

        h3b = round(avail_gb - hardware.ollama_qwen3b_gb, 1)
        h7b = round(avail_gb - hardware.ollama_qwen7b_gb, 1)
        return {
            "total_ram_gb": total_gb,
            "available_ram_gb": avail_gb,
            "headroom_qwen3b_gb": h3b,
            "headroom_qwen7b_gb": h7b,
            "can_run_qwen3b": h3b >= 0,
            "can_run_qwen7b": h7b >= 0,
            "max_concurrent_agents": hardware.max_concurrent_tasks,
            "ollama_running": ollama_running,
            "ollama_models": ollama_models,
        }

    # Check if port is available
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", port))
        sock.close()
    except OSError:
        log.warning(f"⚠️  Port {port} is already in use. Trying port 0 for a random port...")
        port = 0

    # ---- background pipeline runner ----

    def _run_in_background(idea: str, mode: str):
        """Run the full pipeline in a daemon thread, pushing progress to RunContext."""
        try:
            run_context.reset()
            run_context.update(
                status="running",
                idea=idea,
                mode=mode,
                started_at=datetime.now().isoformat(timespec="seconds"),
                progress_pct=0,
            )

            # Set global config
            from config import research
            research.enable_human_checkpoint = False

            # Monkey-patch ResearchState.checkpoint to also update RunContext
            _original_checkpoint = state_module.ResearchState.checkpoint
            _phase_order = [
                "intake", "decomposer",
                "github_research", "web_research",
                "pattern_extractor", "synthesizer",
                "quality_judge", "knowledge_package",
            ]

            def _checkpoint_with_context(self, agent_name, result):
                _original_checkpoint(self, agent_name, result)
                # Calculate progress percentage
                try:
                    idx = _phase_order.index(agent_name)
                    pct = int((idx + 1) / len(_phase_order) * 95)
                except ValueError:
                    pct = run_context.progress_pct

                updates = {"phase": agent_name, "progress_pct": pct}

                # Extract structured data from agent results
                if agent_name == "intake":
                    updates["sub_problems"] = []
                    updates["ideal_outcome"] = result.get("ideal_outcome", "")
                    updates["core_problems"] = result.get("core_problems", [])
                    updates["domain"] = result.get("domain", [])
                    updates["primary_language"] = result.get("primary_language", "")
                    updates["complexity_estimate"] = result.get("complexity_estimate", "")
                elif agent_name == "decomposer":
                    sps = result.get("sub_problems", [])
                    # Normalise to list of dicts with at least a title
                    sub_problems = []
                    if isinstance(sps, list) and len(sps) > 0:
                        for i, sp in enumerate(sps):
                            if isinstance(sp, str):
                                sub_problems.append({"id": f"SP-{i+1}", "title": sp})
                            elif isinstance(sp, dict):
                                sp_norm = dict(sp)
                                # Normalize field name: decomposer outputs github_search_queries, UI expects github_queries
                                if "github_search_queries" in sp_norm and "github_queries" not in sp_norm:
                                    sp_norm["github_queries"] = sp_norm.pop("github_search_queries")
                                sub_problems.append(sp_norm)
                    updates["sub_problems"] = sub_problems
                    # Initialize research_statuses — always, even if no sub-problems
                    sp_ids = [sp.get("id", f"SP-{i+1}") for i, sp in enumerate(sub_problems)]
                    research_statuses = {
                        "github": {sid: "queued" for sid in sp_ids},
                        "web": {sid: "queued" for sid in sp_ids},
                    }
                    updates["research_statuses"] = research_statuses
                # Per-sub-problem research checkpoints: github_SP-1, web_SP-2, etc.
                # Update the sub-problem's status individually as each finishes
                elif re.match(r'^github_', agent_name):
                    sp_id = agent_name[len("github_"):]
                    rs = dict(run_context.research_statuses)
                    github_statuses = dict(rs.get("github", {}))
                    if sp_id in github_statuses:
                        github_statuses[sp_id] = "done"
                    rs["github"] = github_statuses
                    updates["research_statuses"] = rs
                    updates["phase"] = "github_research"
                elif re.match(r'^web_', agent_name):
                    sp_id = agent_name[len("web_"):]
                    rs = dict(run_context.research_statuses)
                    web_statuses = dict(rs.get("web", {}))
                    if sp_id in web_statuses:
                        web_statuses[sp_id] = "done"
                    rs["web"] = web_statuses
                    updates["research_statuses"] = rs
                    updates["phase"] = "web_research"
                elif agent_name == "pattern_extractor":
                    patterns = result.get("patterns", result)
                    if isinstance(patterns, dict):
                        updates["patterns"] = patterns
                elif agent_name == "synthesizer":
                    brief = result.get("brief", "") or result.get("markdown", "") or str(result)
                    updates["brief_md"] = brief
                elif agent_name == "quality_judge":
                    dims = result.get("dimensions", {})
                    updates["quality_coverage"] = dims.get("addresses_ideal_outcome", 0) / 10
                    updates["quality_novelty"] = dims.get("sub_problems_covered", 0) / 10
                    updates["quality_actionability"] = dims.get("architecture_actionable", 0) / 10
                elif agent_name == "knowledge_package":
                    files = result.get("files", result.get("package_files", []))
                    repos = result.get("extracted_repos", result.get("repos", []))
                    updates["package_files"] = files if isinstance(files, list) else []
                    updates["extracted_repos"] = repos if isinstance(repos, list) else []

                run_context.add_log("info", f"Phase complete: {agent_name}")
                run_context.update(**updates)

            state_module.ResearchState.checkpoint = _checkpoint_with_context

            # Create state and run
            state_obj = state_module.ResearchState(idea)
            run_context.update(run_id=state_obj.run_id)
            from orchestrator import run_pipeline

            # Windows ProactorEventLoop has cleanup bugs that corrupt httpx connections.
            # Switch to SelectorEventLoop for the background thread to avoid this.
            # Also clear cached AsyncOpenAI clients — they're bound to the old loop.
            import sys as _sys
            if _sys.platform == "win32":
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            from provider_pool import pool as _pool_ref
            _pool_ref._clients.clear()  # force fresh clients in the new loop

            _loop = asyncio.new_event_loop()
            asyncio.set_event_loop(_loop)
            try:
                result = _loop.run_until_complete(
                    run_pipeline(
                        idea=idea,
                        state=state_obj,
                        offline=False,
                        focus="",
                        mode=mode,
                        quiet=True,
                    )
                )
            finally:
                try:
                    _pending = asyncio.all_tasks(_loop)
                    if _pending:
                        _loop.run_until_complete(asyncio.gather(*_pending, return_exceptions=True))
                except Exception:
                    pass
                _loop.close()
                # Restore default policy for next run
                if _sys.platform == "win32":
                    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

            run_context.update(
                status="done",
                result=result,
                finished_at=datetime.now().isoformat(timespec="seconds"),
                progress_pct=100,
            )
            run_context.add_log("success", f"Pipeline complete! Output: {result.get('output_path', 'N/A')}")

        except Exception as exc:
            tb = traceback.format_exc()
            run_context.update(
                status="error",
                error=tb,
                finished_at=datetime.now().isoformat(timespec="seconds"),
            )
            run_context.add_log("error", f"Pipeline failed: {exc}")
        finally:
            # Restore original checkpoint to prevent double-wrap on subsequent runs
            state_module.ResearchState.checkpoint = _original_checkpoint

    # ---- API + static file handler ----

    class AriaHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(ui_dir), **kwargs)

        def log_message(self, format, *args):
            pass  # suppress per-request noise

        def end_headers(self):
            # Strip query string before checking extension so ?v=xxx cache-busters still get no-cache
            path_clean = self.path.split("?")[0]
            if any(path_clean.endswith(ext) for ext in (".js", ".jsx", ".html", ".css")):
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.send_header("Pragma", "no-cache")
                self.send_header("Expires", "0")
            super().end_headers()

        def _send_json(self, data, status=200):
            body = json.dumps(data, default=str).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            # Serve index.html for / and /index.html (including any ?t= cache-buster)
            path_base = self.path.split("?")[0]
            if path_base in ("/", "/index.html"):
                idx = ui_dir / "index.html"
                html = idx.read_text("utf-8")
                ts = str(int(_time.time()))
                # Replace all versioned and unversioned local script/style refs
                import re as _re
                for fname in ("data.js", "tweaks-panel.jsx", "swarm.jsx", "screens.jsx", "app.jsx", "styles.css"):
                    html = _re.sub(
                        rf'(src|href)="{_re.escape(fname)}(\?[^"]*)?\"',
                        lambda m, f=fname, t=ts: f'{m.group(1)}="{f}?v={t}"',
                        html
                    )
                # Inject server-time badge (non-React, bypasses all JS caching)
                badge = (
                    f'<div id="_aria_srv_badge" style="position:fixed;bottom:6px;right:8px;'
                    f'font:10px/1 monospace;color:var(--muted-2,#999);'
                    f'pointer-events:none;z-index:9999;opacity:0.6">'
                    f'srv·{ts}</div>\n'
                )
                html = html.replace("</body>", badge + "</body>")
                body = html.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.send_header("Pragma", "no-cache")
                self.send_header("Expires", "0")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            if self.path == "/api/status":
                status = run_context.to_dict()

                # Always refresh provider data from the live singleton
                try:
                    from provider_pool import pool as _pool
                    from config import PROVIDER_MODELS as _PM, RATE_LIMITS as _RL
                    _providers = []
                    for _name, _st in _pool.get_provider_status().items():
                        _ready = _pool.is_available(_name)
                        _keys = len(_pool._key_pools.get(_name, []))
                        _rpm_key = f"{_name}_per_key"
                        _rpm = _RL.get(_rpm_key, {}).get("rpm", 30) * max(_keys, 1)
                        _providers.append({
                            "name": _name,
                            "status": "ok" if _ready else "err",
                            "model": _PM.get(_name, "unknown"),
                            "keys": _keys,
                            "rpm": _rpm,
                            "status_text": _st,
                        })
                    status["providers"] = _providers
                except Exception:
                    pass

                # Hardware info (cached 30 s)
                if _time.time() - _hw_cache["ts"] > 30:
                    _hw_cache["data"] = _get_hardware_info()
                    _hw_cache["ts"] = _time.time()
                status["hardware"] = _hw_cache["data"]

                self._send_json(status)

            elif self.path == "/api/reset":
                run_context.reset()
                self._send_json({"status": "idle"})

            elif self.path == "/api/runs":
                runs = []
                output_dir = pathlib.Path(__file__).parent / "output"
                if output_dir.exists():
                    for d in sorted(output_dir.iterdir(), reverse=True):
                        if not d.is_dir():
                            continue
                        run: dict = {
                            "run_id": d.name,
                            "idea": "",
                            "date": "",
                            "status": "partial",
                            "has_brief": (d / "ARIA_research_brief.md").exists(),
                            "quality_score": None,
                        }
                        parts = d.name.split("_", 2)
                        if len(parts) >= 2:
                            run["date"] = (
                                f"{parts[0][:4]}-{parts[0][4:6]}-{parts[0][6:]} "
                                f"{parts[1][:2]}:{parts[1][2:4]}"
                            )
                        if len(parts) == 3:
                            run["idea"] = parts[2].replace("_", " ")
                        state_file = d / "state.json"
                        if state_file.exists():
                            try:
                                s = json.loads(state_file.read_text("utf-8"))
                                if s.get("knowledge_package", {}).get("status") == "done":
                                    run["status"] = "complete"
                                elif any(v.get("status") == "failed" for v in s.values() if isinstance(v, dict)):
                                    run["status"] = "failed"
                            except Exception:
                                pass
                        quality_file = d / "quality_judge.json"
                        if quality_file.exists():
                            try:
                                q = json.loads(quality_file.read_text("utf-8"))
                                run["quality_score"] = q.get("overall_score")
                            except Exception:
                                pass
                        runs.append(run)
                self._send_json({"runs": runs})

            elif self.path == "/api/prompts":
                prompts_dir = pathlib.Path(__file__).parent / "prompts"
                _agent_map = {
                    "intake_system":    "Intake Agent",
                    "decompose_system": "Decomposer",
                    "github_research":  "GitHub Researcher",
                    "web_research":     "Web Researcher",
                    "pattern_extract":  "Pattern Extractor",
                    "synthesize_system":"Synthesizer",
                    "judge_system":     "Quality Judge",
                }
                prompts = []
                for f in sorted(prompts_dir.glob("*.txt")):
                    try:
                        content = f.read_text("utf-8")
                        prompts.append({
                            "name": f.stem,
                            "agent": _agent_map.get(f.stem, f.stem),
                            "content": content,
                            "chars": len(content),
                        })
                    except Exception:
                        pass
                self._send_json({"prompts": prompts})

            else:
                super().do_GET()

        def do_POST(self):
            if self.path == "/api/run":
                content_length = int(self.headers.get("Content-Length", 0))
                if content_length == 0:
                    self._send_json({"error": "Empty request body"}, 400)
                    return
                body = json.loads(self.rfile.read(content_length))
                idea = body.get("idea", "").strip()
                mode = body.get("mode", "research")
                if len(idea) < 10:
                    self._send_json({"error": "Idea must be at least 10 characters"}, 400)
                    return

                # Launch pipeline in background thread
                t = threading.Thread(
                    target=_run_in_background,
                    args=(idea, mode),
                    daemon=True,
                )
                t.start()

                self._send_json({
                    "status": "started",
                    "idea": idea,
                    "mode": mode,
                })
            else:
                self._send_json({"error": "Not found"}, 404)

        def do_OPTIONS(self):
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

    server = HTTPServer(("127.0.0.1", port), AriaHandler)
    actual_port = server.server_address[1]
    url = f"http://127.0.0.1:{actual_port}"

    log.banner(
        "+====================================================================+\n"
        "|                                                                    |\n"
        "|   ARIA v2 — UI Dashboard                                          |\n"
        "|   Research pipeline with live API endpoints                        |\n"
        "|                                                                    |\n"
        "+====================================================================+",
        style="bold cyan",
    )

    log.info(f"[bold green]🚀 ARIA UI:[/bold green] {url}")
    log.info(f"[dim]  Serving {ui_dir}[/dim]")
    log.info("[dim]  Press Ctrl+C to stop[/dim]")

    if open_browser:
        import time as _t2
        bust_url = f"{url}/?t={int(_t2.time())}"
        webbrowser.open(bust_url)
        log.info(f"[dim]  Browser opened to {bust_url}[/dim]")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("\n[dim]Shutting down server...[/dim]")
        run_context.reset()
        server.shutdown()


async def _run_pipeline(
    idea: str,
    state: ResearchState,
    offline: bool,
    focus: Optional[str],
    mode: str = "research",
) -> dict:
    """Run the full research pipeline (module-level async function)."""
    from orchestrator import run_pipeline
    return await run_pipeline(
        idea=idea,
        state=state,
        offline=offline,
        focus=focus,
        mode=mode,
    )


def _generate_build_prompt(result: dict, idea: str) -> Optional[str]:
    """
    Generate a build-ready prompt file for Codebuff/Claude CLI handoff.

    Creates a markdown file in the knowledge package directory that
    contains all the context needed for a coding AI to start building.

    Returns:
        Path to the generated prompt file, or None if not available.
    """
    pkg_dir = result.get("package_dir", "")
    if not pkg_dir:
        return None

    quality = result.get("quality_score", "?")
    verdict = result.get("verdict", "UNKNOWN")

    prompt_content = (
        f"# ARIA Build Handoff\n\n"
        f"## Problem\n{idea}\n\n"
        f"## Research Quality\n"
        f"- Quality Score: {quality}/10\n"
        f"- Verdict: {verdict}\n\n"
        f"## Knowledge Package\n"
        f"The full research knowledge package is at: `{pkg_dir}`\n\n"
        f"### Contents\n"
        f"1. `00_PROBLEM.md` — Problem statement and ideal outcome\n"
        f"2. `01_DECOMPOSITION.md` — Sub-problem breakdown with search queries\n"
        f"3. `02_TOP_REPOS.md` — Ranked repositories with analysis\n"
        f"4. `extracted_code/` — Actual source files from top repos\n"
        f"5. `04_PATTERNS.md` — Architectural patterns and approaches\n"
        f"6. `05_LIBRARIES.md` — Recommended libraries with justifications\n"
        f"7. `06_BUILD_PLAN.md` — Phased implementation plan\n"
        f"8. `07_WEB_RESEARCH.md` — Web research findings\n"
        f"9. `08_RISKS.md` — Gotchas, anti-patterns, and risks\n\n"
        f"## Build Instructions\n"
        f"Read the full knowledge package above, then build the solution.\n"
        f"Start with the build plan in `06_BUILD_PLAN.md` and follow the phases.\n"
        f"Reference extracted code from `extracted_code/` for implementation patterns.\n"
        f"Use the recommended libraries from `05_LIBRARIES.md` for dependencies.\n"
    )

    prompt_path = os.path.join(pkg_dir, "..", "ARIA_build_handoff.md")
    prompt_path = os.path.normpath(prompt_path)
    try:
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write(prompt_content)
        return prompt_path
    except OSError:
        return None


def main():
    """Entry point."""
    app()


if __name__ == "__main__":
    main()
