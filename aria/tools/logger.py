"""
ARIA v2 — Structured Logger

Unified logging system that writes to:
- Console (via Rich for formatted display)
- Log file (structured, rotated, with timestamps and levels)

Usage:
    from tools.logger import log

    log.info("Pipeline started")
    log.warning("Rate limit approaching")
    log.error("Provider unavailable")
    log.debug("DeepSeek response: %s", response)

    # Rich-specific console output
    log.panel("Results", "Score: 8/10", style="green")
    log.table("Providers", ["Name", "Status"], [["Groq", "OK"], ...])
"""

import logging
import os
from datetime import datetime
from typing import Any, Optional


class ARIALogger:
    """
    Structured logger for ARIA.

    Wraps Python's logging module with:
    - Rich console output (formatted, colored)
    - Structured file logging (timestamps, levels, module names)
    - Helper methods for Rich-specific display (panel, table, markdown, banner)

    Log levels:
        DEBUG:    Detailed diagnostic information
        INFO:     Status updates and progress
        WARNING:  Non-critical issues worth noting
        ERROR:    Critical failures that may affect results
    """

    def __init__(self, run_id: Optional[str] = None, log_dir: Optional[str] = None):
        self.run_id = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_dir = log_dir or os.path.join("output", self.run_id)

        # Ensure log directory exists
        os.makedirs(self.log_dir, exist_ok=True)

        # Set up Python logger
        self._logger = logging.getLogger("aria")
        self._logger.setLevel(logging.DEBUG)
        # Clear any existing handlers (for re-initialization)
        self._logger.handlers.clear()

        # -- File handler: structured, timestamped --
        log_path = os.path.join(self.log_dir, "aria.log")
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        self._logger.addHandler(file_handler)

        # -- Console handler: Rich-formatted --
        from rich.console import Console
        from rich.logging import RichHandler
        self.console = Console()
        console_handler = RichHandler(
            console=self.console,
            show_time=False,
            show_path=False,
            show_level=False,
            markup=True,
            rich_tracebacks=True,
        )
        console_handler.setLevel(logging.INFO)
        self._logger.addHandler(console_handler)

        self._log_path = log_path

    @property
    def log_path(self) -> str:
        """Path to the current log file."""
        return self._log_path

    # ── Basic log methods ──────────────────────────────────────────────

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log at DEBUG level."""
        self._logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log at INFO level."""
        self._logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log at WARNING level."""
        self._logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log at ERROR level."""
        self._logger.error(msg, *args, **kwargs)

    # ── Rich-specific display helpers (console only) ───────────────────

    def panel(self, title: str, content: str, style: str = "cyan") -> None:
        """Render a Rich Panel to console only."""
        from rich.panel import Panel as RichPanel
        self.console.print(RichPanel(content, title=title, border_style=style))

    def table(self, title: str, columns: list[str], rows: list[list[str]]) -> None:
        """Render a Rich Table to console only."""
        from rich import box
        from rich.table import Table as RichTable
        table = RichTable(title=title, box=box.ROUNDED)
        for col in columns:
            table.add_column(col)
        for row in rows:
            table.add_row(*row)
        self.console.print(table)

    def markdown(self, content: str) -> None:
        """Render a Rich Markdown block to console only."""
        from rich.markdown import Markdown
        self.console.print(Markdown(content))

    def banner(self, text: str, style: str = "bold cyan") -> None:
        """Print a styled banner line to console only."""
        self.console.print(text, style=style)

    def print(self, *args: Any, **kwargs: Any) -> None:
        """Pass-through to console.print for ad-hoc Rich output."""
        self.console.print(*args, **kwargs)

    # ── Health / status ────────────────────────────────────────────────

    def get_log_path(self) -> str:
        """Get the current log file path."""
        return self._log_path


# ── Global singleton ────────────────────────────────────────────────────────

_log: Optional[ARIALogger] = None


def get_logger(run_id: Optional[str] = None, log_dir: Optional[str] = None) -> ARIALogger:
    """
    Get or create the global ARIA logger singleton.

    If the logger already exists and no new run_id is given, returns the
    existing instance. Pass a new run_id to re-initialize for a different run.
    """
    global _log
    if _log is None or run_id is not None:
        _log = ARIALogger(run_id=run_id, log_dir=log_dir)
    return _log


# Module-level convenience reference (initialized on first use)
log: ARIALogger = get_logger()
