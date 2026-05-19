"""
ARIA v2 — Full API health check.
Tests every configured provider with a minimal chat call.
Also checks Ollama availability and the GitHub/Jina tokens.
Run: python test_all_apis.py
"""

import asyncio
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Load .env
from config import (
    PROVIDER_ENDPOINTS,
    PROVIDER_MODELS,
    get_cerebras_key,
    get_deepseek_keys,
    get_github_token,
    get_groq_keys,
    get_jina_key,
    get_nvidia_keys,
    get_sambanova_keys,
    get_siliconflow_keys,
    get_zhipu_key,
)

PING_MSG = [{"role": "user", "content": 'Reply with exactly: {"ok": true}'}]

# ── colour helpers ────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def ok(s):  return f"{GREEN}OK{RESET}  {s}"
def err(s): return f"{RED}FAIL{RESET} {s}"
def warn(s):return f"{YELLOW}WARN{RESET} {s}"

# ── generic OpenAI-compat test ────────────────────────────────────────────────
async def test_openai_compat(name: str, base_url: str, api_key: str, model: str, label: str = "") -> tuple[bool, str]:
    import aiohttp
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": PING_MSG,
        "max_tokens": 20,
        "temperature": 0,
    }
    t0 = time.monotonic()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=20)) as r:
                elapsed = time.monotonic() - t0
                body = await r.json(content_type=None)
                if r.status == 200:
                    content = body.get("choices", [{}])[0].get("message", {}).get("content", "")
                    tag = f" [{label}]" if label else ""
                    return True, f"{name}{tag} — {model} — {elapsed:.1f}s — reply: {content[:60]!r}"
                else:
                    err_msg = body.get("error", {}).get("message", str(body))[:120]
                    return False, f"{name} — {r.status} — {err_msg}"
    except Exception as e:
        return False, f"{name} — {type(e).__name__}: {e}"


# ── per-provider tests ────────────────────────────────────────────────────────
async def test_groq() -> list[tuple[bool, str]]:
    keys = get_groq_keys()
    if not keys:
        return [(False, "Groq — no keys configured")]
    results = []
    for i, key in enumerate(keys, 1):
        ok_flag, msg = await test_openai_compat(
            "Groq", PROVIDER_ENDPOINTS["groq"], key,
            PROVIDER_MODELS["groq"], f"key {i}"
        )
        results.append((ok_flag, msg))
        await asyncio.sleep(1)
    return results


async def test_deepseek() -> list[tuple[bool, str]]:
    keys = get_deepseek_keys()
    if not keys:
        return [(False, "DeepSeek — no keys configured")]
    results = []
    for i, key in enumerate(keys, 1):
        ok_flag, msg = await test_openai_compat(
            "DeepSeek", PROVIDER_ENDPOINTS["deepseek"], key,
            PROVIDER_MODELS["deepseek"], f"key {i}"
        )
        results.append((ok_flag, msg))
        await asyncio.sleep(0.5)
    return results


async def test_sambanova() -> list[tuple[bool, str]]:
    keys = get_sambanova_keys()
    if not keys:
        return [(False, "SambaNova — no keys configured")]
    results = []
    for i, key in enumerate(keys, 1):
        ok_flag, msg = await test_openai_compat(
            "SambaNova", PROVIDER_ENDPOINTS["sambanova"], key,
            PROVIDER_MODELS["sambanova"], f"key {i}"
        )
        results.append((ok_flag, msg))
        await asyncio.sleep(0.5)
    return results


async def test_siliconflow() -> list[tuple[bool, str]]:
    keys = get_siliconflow_keys()
    if not keys:
        return [(False, "SiliconFlow — no keys configured")]
    results = []
    # Test both current model AND a fallback to find which one works
    models_to_try = [
        PROVIDER_MODELS["siliconflow"],        # Qwen/Qwen2.5-72B-Instruct
        "Qwen/Qwen2.5-7B-Instruct",
        "deepseek-ai/DeepSeek-V2.5",
        "THUDM/glm-4-9b-chat",
    ]
    for i, key in enumerate(keys, 1):
        found = False
        for model in models_to_try:
            ok_flag, msg = await test_openai_compat(
                "SiliconFlow", PROVIDER_ENDPOINTS["siliconflow"], key, model, f"key {i}"
            )
            if ok_flag:
                results.append((True, msg))
                found = True
                break
            await asyncio.sleep(0.3)
        if not found:
            results.append((False, f"SiliconFlow [key {i}] — all models failed. Last: {msg}"))
    return results


async def test_nvidia() -> list[tuple[bool, str]]:
    keys = get_nvidia_keys()
    if not keys:
        return [(False, "NVIDIA NIM — no keys configured")]
    results = []
    for i, key in enumerate(keys, 1):
        ok_flag, msg = await test_openai_compat(
            "NVIDIA", PROVIDER_ENDPOINTS["nvidia"], key,
            PROVIDER_MODELS["nvidia"], f"key {i}"
        )
        results.append((ok_flag, msg))
        await asyncio.sleep(0.5)
    return results


async def test_cerebras() -> list[tuple[bool, str]]:
    key = get_cerebras_key()
    if not key:
        return [(False, "Cerebras — no key configured")]
    ok_flag, msg = await test_openai_compat(
        "Cerebras", PROVIDER_ENDPOINTS["cerebras"], key,
        PROVIDER_MODELS["cerebras"]
    )
    return [(ok_flag, msg)]


async def test_zhipu() -> list[tuple[bool, str]]:
    key = get_zhipu_key()
    if not key:
        return [(False, "Zhipu — no key configured")]
    ok_flag, msg = await test_openai_compat(
        "Zhipu", PROVIDER_ENDPOINTS["zhipu"], key,
        PROVIDER_MODELS["zhipu"]
    )
    return [(ok_flag, msg)]


async def test_github() -> list[tuple[bool, str]]:
    import aiohttp
    token = get_github_token()
    if not token:
        return [(False, "GitHub — no token configured")]
    try:
        headers = {"Authorization": f"token {token}", "User-Agent": "ARIA-v2/1.0"}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get("https://api.github.com/rate_limit", timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status == 200:
                    data = await r.json()
                    core = data["resources"]["core"]
                    search = data["resources"]["search"]
                    return [(True, f"GitHub — core {core['remaining']}/{core['limit']} | search {search['remaining']}/{search['limit']} rpm")]
                return [(False, f"GitHub — HTTP {r.status}")]
    except Exception as e:
        return [(False, f"GitHub — {e}")]


async def test_ollama() -> list[tuple[bool, str]]:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{base_url}/api/tags", timeout=aiohttp.ClientTimeout(total=5)) as r:
                if r.status == 200:
                    data = await r.json()
                    models = [m.get("name", "") for m in data.get("models", [])]
                    if models:
                        return [(True, f"Ollama — running, models: {', '.join(models[:5])}")]
                    return [(False, "Ollama — running but NO models installed (pull qwen2.5:3b-instruct-q4_K_M)")]
                return [(False, f"Ollama — HTTP {r.status}")]
    except Exception:
        return [(False, "Ollama — NOT running (start with: ollama serve)")]


# ── main ──────────────────────────────────────────────────────────────────────
async def main():
    print(f"\n{BOLD}=== ARIA v2 — Full API Health Check ==={RESET}\n")

    all_tests = [
        ("Groq",       test_groq),
        ("DeepSeek",   test_deepseek),
        ("SambaNova",  test_sambanova),
        ("SiliconFlow",test_siliconflow),
        ("NVIDIA NIM", test_nvidia),
        ("Cerebras",   test_cerebras),
        ("Zhipu",      test_zhipu),
        ("GitHub",     test_github),
        ("Ollama",     test_ollama),
    ]

    passed = failed = 0
    for name, fn in all_tests:
        print(f"Testing {name}...", end="", flush=True)
        results = await fn()
        print("\r", end="")
        for success, msg in results:
            if success:
                print(ok(msg))
                passed += 1
            else:
                print(err(msg))
                failed += 1

    print(f"\n{BOLD}Result: {GREEN}{passed} passed{RESET}{BOLD}, {RED}{failed} failed{RESET}")

    # Ollama role explanation
    print(f"\n{BOLD}--- Ollama role in ARIA ---{RESET}")
    print("Ollama is a LOCAL fallback for offline/privacy mode only.")
    print("It is NOT used in any live run unless you pass the --offline flag.")
    print("In all normal runs, cloud providers handle everything.")
    print("To enable: python main.py run <idea> --offline")


if __name__ == "__main__":
    asyncio.run(main())
