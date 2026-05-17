"""
ARIA v2 — Research State Module
Checkpoint/recovery system. Saves and loads agent output state from JSON files
so the pipeline can resume from any failure point.
"""

import json
import pathlib
from datetime import datetime
from typing import Any, Optional


def slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug."""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in text).strip("_").lower()[:64]


def timestamp() -> str:
    """Generate a timestamp string for directory naming."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


class ResearchState:
    """
    Checkpoint system for research pipeline.

    Persists agent outputs to output/{run_id}/state.json so the pipeline can
    resume from any failure point using --resume.

    Usage:
        state = ResearchState("my_idea")
        state.checkpoint("intake", {"result": ...})
        if state.is_done("intake"):
            result = state.load("intake")
    """

    def __init__(self, idea: str, resume_id: Optional[str] = None):
        self.run_id = resume_id or f"{timestamp()}_{slugify(idea)}"
        self.base_path = pathlib.Path("output") / self.run_id
        self.state_path = self.base_path / "state.json"
        self.state: dict[str, dict] = self._load()

    def _load(self) -> dict[str, dict]:
        """Load existing state if resuming."""
        if self.state_path.exists():
            try:
                return json.loads(self.state_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return {}
        self.base_path.mkdir(parents=True, exist_ok=True)
        return {}

    def save_artifact(self, name: str, data: dict[str, Any]) -> pathlib.Path:
        """
        Save an artifact JSON file (e.g., intake.json, decomposition.json).
        Returns the path to the saved file.
        """
        file_path = self.base_path / f"{name}.json"
        file_path.write_text(
            json.dumps(data, indent=2, default=str),
            encoding="utf-8",
        )
        return file_path

    def checkpoint(self, agent_name: str, result: dict[str, Any]) -> None:
        """
        Mark an agent as completed and save its result to state.json
        and as a named artifact.
        """
        # Save as named artifact
        artifact_path = self.save_artifact(agent_name, result)

        # Update state
        self.state[agent_name] = {
            "status": "done",
            "artifact": str(artifact_path),
            "completed_at": timestamp(),
        }
        self._persist()

    def fail(self, agent_name: str, error: str) -> None:
        """Mark an agent as failed with error details."""
        self.state[agent_name] = {
            "status": "failed",
            "error": error,
            "failed_at": timestamp(),
        }
        self._persist()

    def is_done(self, agent_name: str) -> bool:
        """Check if an agent has completed successfully."""
        return self.state.get(agent_name, {}).get("status") == "done"

    def is_failed(self, agent_name: str) -> bool:
        """Check if an agent has failed."""
        return self.state.get(agent_name, {}).get("status") == "failed"

    def load(self, agent_name: str) -> Optional[dict[str, Any]]:
        """Load an agent's saved artifact."""
        entry = self.state.get(agent_name, {})
        artifact_path = entry.get("artifact")
        if artifact_path and pathlib.Path(artifact_path).exists():
            try:
                return json.loads(pathlib.Path(artifact_path).read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return None
        return None

    def _persist(self) -> None:
        """Write current state to disk."""
        self.state_path.write_text(
            json.dumps(self.state, indent=2, default=str),
            encoding="utf-8",
        )

    def summary(self) -> str:
        """Return a human-readable summary of current research state."""
        lines = [f"📁 Run ID: {self.run_id}", f"📂 Path: {self.base_path}", ""]
        for agent, info in self.state.items():
            status = info.get("status", "unknown")
            icon = "✅" if status == "done" else "❌" if status == "failed" else "⏳"
            lines.append(f"  {icon} {agent}: {status}")
        return "\n".join(lines)
