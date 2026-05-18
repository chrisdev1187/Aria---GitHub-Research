"""
ARIA v2 — Run Context
Thread-safe singleton that bridges the pipeline to the UI API.
The pipeline writes progress updates here; the serve command serves them via HTTP.
"""

import threading
from datetime import datetime
from typing import Any, Optional


class RunContext:
    """Singleton holding the current/last run state for the UI API."""

    _instance: Optional["RunContext"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "RunContext":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._reset()
            return cls._instance

    # ---- internal helpers ----

    def _reset(self) -> None:
        self.run_id: Optional[str] = None
        self.status: str = "idle"  # idle | running | done | error
        self.phase: str = ""
        self.progress_pct: int = 0
        self.idea: str = ""
        self.mode: str = "research"
        self.started_at: Optional[str] = None
        self.finished_at: Optional[str] = None
        self.result: Optional[dict] = None
        self.error: Optional[str] = None
        self.ideal_outcome: str = ""
        self.core_problems: list[str] = []
        self.domain: list[str] = []
        self.primary_language: str = ""
        self.complexity_estimate: str = ""
        self.research_statuses: dict = {}  # {researcher: {sp_id: "queued"|"active"|"done"}}
        self.sub_problems: list[dict] = []
        self.brief_md: str = ""
        self.patterns: dict = {}
        self.package_files: list = []
        self.extracted_repos: list = []
        self.research_repos: list = []   # live-populated from github research, shown before manifest is ready
        self.package_dir: str = ""
        self.extracted_code_dir: str = ""
        self.providers: list[dict] = []
        self.logs: list[dict] = []
        self.quality_coverage: float = 0.0
        self.quality_novelty: float = 0.0
        self.quality_actionability: float = 0.0
        self._lock_internal = threading.Lock()

    def reset(self) -> None:
        with self._lock_internal:
            self._reset()

    # ---- write helpers (thread-safe) ----

    def update(self, **kwargs: Any) -> None:
        with self._lock_internal:
            for k, v in kwargs.items():
                if hasattr(self, k):
                    setattr(self, k, v)

    def add_log(self, level: str, message: str) -> None:
        with self._lock_internal:
            self.logs.append({
                "time": datetime.now().isoformat(timespec="seconds"),
                "level": level,
                "message": message,
            })

    # ---- read helper (thread-safe snapshot) ----

    def to_dict(self) -> dict:
        with self._lock_internal:
            result_dict = self.result or {}
            return {
                "run_id": self.run_id,
                "status": self.status,
                "phase": self.phase,
                "progress_pct": self.progress_pct,
                "idea": self.idea,
                "mode": self.mode,
                "started_at": self.started_at,
                "finished_at": self.finished_at,
                "ideal_outcome": self.ideal_outcome,
                "core_problems": self.core_problems,
                "domain": self.domain,
                "primary_language": self.primary_language,
                "complexity_estimate": self.complexity_estimate,
                "research_statuses": self.research_statuses,
                "sub_problems": self.sub_problems,
                "providers": self.providers,
                "patterns": self.patterns,
                "package_files": self.package_files,
                "brief_md": self.brief_md,
                "result": self.result,
                "error": self.error,
                "overall_score": result_dict.get("quality_score"),
                "verdict": result_dict.get("verdict"),
                "quality_coverage": self.quality_coverage,
                "quality_novelty": self.quality_novelty,
                "quality_actionability": self.quality_actionability,
                # Serve research_repos as fallback until manifest-based extracted_repos are ready
                "extracted_repos": self.extracted_repos if self.extracted_repos else self.research_repos,
                "package_dir": self.package_dir,
                "extracted_code_dir": self.extracted_code_dir,
                "logs": self.logs[-100:],
            }


# Module-level singleton — import and use directly
run_context = RunContext()
