"""
ARIA v2 — Configuration Module
Loads all provider keys from environment, defines rate limits, hardware-aware defaults.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Try to load .env from project root first, then aria/ directory
_env_path = Path(__file__).parent / ".env"
_parent_env = Path(__file__).parent.parent / ".env"
if _parent_env.exists():
    load_dotenv(dotenv_path=_parent_env, override=True)
elif _env_path.exists():
    load_dotenv(dotenv_path=_env_path, override=True)
else:
    load_dotenv()  # fall back to system PATH


# ─── Rate Limits ───────────────────────────────────────────────────────────────

RATE_LIMITS = {
    "groq_per_key": {"rpm": 28},  # 30 limit - 2 safety buffer
    "groq_pool": {"rpm": 112},  # 4 keys × 28
    "deepseek_per_key": {"rpm": 58},  # generous free tier
    "deepseek_pool": {"rpm": 116},  # 2 keys × 58
    "sambanova_per_key": {"rpm": 18},
    "siliconflow_per_key": {"rpm": 28},
    "nvidia_per_key": {"rpm": 18},
    "cerebras": {"rpm": 28},
    "gemini_flash": {"rpm": 13},  # 15 limit - 2 buffer (context reads only)
    "github": {"rph": 4900},  # 5000 - 100 buffer
    "jina": {"delay_s": 1.0},
    "ddg": {"delay_s": 2.0},
}


# ─── Provider Endpoints ────────────────────────────────────────────────────────

PROVIDER_ENDPOINTS = {
    "groq": "https://api.groq.com/openai/v1",
    "deepseek": "https://api.deepseek.com",
    "sambanova": "https://api.sambanova.ai/v1",
    "siliconflow": "https://api.siliconflow.cn/v1",
    "nvidia": "https://integrate.api.nvidia.com/v1",
    "cerebras": "https://api.cerebras.ai/v1",
    "zhipu": "https://open.bigmodel.cn/api/paas/v4",
}


# ─── Provider → Model Mapping ──────────────────────────────────────────────────

PROVIDER_MODELS = {
    "groq": "llama-3.3-70b-versatile",
    "deepseek": "deepseek-chat",
    "sambanova": "Meta-Llama-3.3-70B-Instruct",   # 3.1-8B deprecated 2026-05
    "siliconflow": "Qwen/Qwen2.5-72B-Instruct",
    "nvidia": "meta/llama-3.1-8b-instruct",
    "cerebras": "llama3.1-8b",                     # llama-3.3-70b removed from Cerebras
    "zhipu": "glm-4-flash",
    "gemini": "gemini-2.0-flash",
    "ollama_default": "qwen2.5-coder:3b-instruct-q4_K_M",  # match installed model name
    "ollama_deep": "qwen2.5-coder:7b-instruct-q4_K_M",
}


# ─── Agent → Provider Assignment ───────────────────────────────────────────────

AGENT_PROVIDER_MAP = {
    "intake": "groq",
    "decomposer": "groq",
    "github_researcher": "deepseek",
    "github_large_files": "gemini",  # 1M context reader only
    "web_researcher": "nvidia",
    "pattern_extractor": "deepseek",
    "synthesizer": "nvidia",
    "quality_judge": "groq",
}

AGENT_FALLBACK_MAP = {
    "intake": "cerebras",
    "decomposer": "cerebras",
    "github_researcher": "siliconflow",
    "web_researcher": "zhipu",
    "pattern_extractor": "ollama_default",  # local fallback for offline mode
    "synthesizer": "sambanova",
    "quality_judge": "cerebras",
}


# ─── API Key Loaders ───────────────────────────────────────────────────────────

def _get_keys(prefix: str, count: int) -> list[str]:
    """
    Load N API keys for a provider.

    Supports two naming conventions:
    - First key: ``{prefix}`` (without _1 suffix, e.g. ``GROQ_API_KEY``)
    - Subsequent keys: ``{prefix}_{i}`` (e.g. ``GROQ_API_KEY_2``, ``GROQ_API_KEY_3``)

    This matches the actual .env naming convention used in the project.
    """
    keys = []
    # First key uses base name without _1
    first = os.getenv(prefix, "")
    if first and first.strip():
        keys.append(first.strip())
    # Subsequent keys use _{i} suffix starting from _2
    for i in range(2, count + 1):
        key = os.getenv(f"{prefix}_{i}", "")
        if key and key.strip():
            keys.append(key.strip())
    return keys


def get_groq_keys() -> list[str]:
    """Load Groq API keys (supports GROQ_API_KEY + GROQ_API_KEY_2/3/4)."""
    return _get_keys("GROQ_API_KEY", 4)


def get_deepseek_keys() -> list[str]:
    """Load DeepSeek API keys (supports DEEPSEEK_API_KEY + DEEPSEEK_API_KEY_2)."""
    return _get_keys("DEEPSEEK_API_KEY", 2)


def get_sambanova_keys() -> list[str]:
    return _get_keys("SAMBANOVA_API_KEY", 2)


def get_siliconflow_keys() -> list[str]:
    return _get_keys("SILICONFLOW_API_KEY", 2)


def get_nvidia_keys() -> list[str]:
    return _get_keys("NVIDIA_API_KEY", 2)


def get_cerebras_key() -> Optional[str]:
    key = os.getenv("CEREBRAS_API_KEY", "") or None
    return key


def get_zhipu_key() -> Optional[str]:
    key = os.getenv("ZHIPU_API_KEY", "") or None
    return key


def get_gemini_keys() -> list[str]:
    """
    Load Gemini API keys (supports up to 4 keys for rate-limit redundancy).
    Uses same naming: GEMINI_API_KEY, GEMINI_API_KEY_2, GEMINI_API_KEY_3, GEMINI_API_KEY_4
    """
    return _get_keys("GEMINI_API_KEY", 4)


def get_openrouter_key() -> Optional[str]:
    return os.getenv("OPENROUTER_API_KEY", "") or None


def get_github_token() -> Optional[str]:
    token = os.getenv("GITHUB_TOKEN", "") or None
    return token


def get_jina_key() -> Optional[str]:
    return os.getenv("JINA_API_KEY", "") or None


# ─── Hardware Config ───────────────────────────────────────────────────────────

@dataclass
class HardwareConfig:
    """Hardware-aware configuration — tuned for Intel UHD 620, 8GB RAM."""
    total_ram_gb: float = 8.0
    os_overhead_gb: float = 2.0
    python_overhead_gb: float = 0.8
    ollama_qwen3b_gb: float = 2.2
    ollama_qwen7b_gb: float = 5.5
    max_concurrent_tasks: int = 3
    use_deep_model: bool = False
    use_offline_mode: bool = False

    @property
    def available_ram_gb(self) -> float:
        """Calculate available RAM after OS and Python overhead."""
        return self.total_ram_gb - self.os_overhead_gb - self.python_overhead_gb

    @property
    def can_run_qwen7b(self) -> bool:
        """Qwen 7B requires ~5.5GB. Only safe with --deep flag."""
        return self.available_ram_gb >= self.ollama_qwen7b_gb

    @property
    def can_run_qwen3b(self) -> bool:
        """Qwen 3B requires ~2.2GB. Safe on 8GB systems."""
        return self.available_ram_gb >= self.ollama_qwen3b_gb

    @property
    def headroom_gb(self) -> float:
        """Available headroom after running Ollama."""
        model_ram = self.ollama_qwen7b_gb if self.use_deep_model else self.ollama_qwen3b_gb
        return self.available_ram_gb - model_ram

    def warn_if_tight(self) -> Optional[str]:
        """Return a warning string if RAM is tight."""
        if self.use_deep_model and not self.can_run_qwen7b:
            return (
                "⚠️  WARNING: Qwen 7B requires ~5.5GB RAM. "
                f"Only {self.available_ram_gb:.1f}GB available. "
                "Use --deep at your own risk."
            )
        if self.headroom_gb < 0.5:
            return (
                f"⚠️  RAM headroom is only {self.headroom_gb:.1f}GB. "
                "System may be unstable under load."
            )
        return None


# ─── Research Config ───────────────────────────────────────────────────────────

@dataclass
class ResearchConfig:
    """Research behavior configuration."""
    max_repos_per_subproblem: int = int(os.getenv("MAX_REPOS_PER_SUBPROBLEM", "10"))
    max_files_per_repo: int = int(os.getenv("MAX_FILES_PER_REPO", "5"))
    max_research_loops: int = int(os.getenv("MAX_RESEARCH_LOOPS", "2"))
    max_subproblems: int = int(os.getenv("MAX_SUBPROBLEMS", "12"))
    max_concurrent_agents: int = int(os.getenv("MAX_CONCURRENT_AGENTS", "3"))
    enable_web_research: bool = os.getenv("ENABLE_WEB_RESEARCH", "true").lower() == "true"
    enable_human_checkpoint: bool = os.getenv("ENABLE_HUMAN_CHECKPOINT", "true").lower() == "true"


# ─── Global Config Singleton ───────────────────────────────────────────────────

hardware = HardwareConfig()
research = ResearchConfig()
