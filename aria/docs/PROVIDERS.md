# ARIA v2 — Provider Setup

All providers are free-tier. Add keys to `.env` in the project root.

## Required (pipeline won't run without at least one)

| Provider | Env vars | Free tier | Get key |
|----------|----------|-----------|---------|
| **Groq** | `GROQ_API_KEY_1` … `GROQ_API_KEY_4` | 28 RPM/key | console.groq.com |
| **DeepSeek** | `DEEPSEEK_API_KEY_1`, `DEEPSEEK_API_KEY_2` | generous | platform.deepseek.com |

## Recommended (improves quality + speed)

| Provider | Env vars | Free tier | Get key |
|----------|----------|-----------|---------|
| **SambaNova** | `SAMBANOVA_API_KEY_1`, `SAMBANOVA_API_KEY_2` | 18 RPM/key | cloud.sambanova.ai |
| **SiliconFlow** | `SILICONFLOW_API_KEY_1`, `SILICONFLOW_API_KEY_2` | 28 RPM/key | cloud.siliconflow.cn |
| **NVIDIA NIM** | `NVIDIA_API_KEY_1`, `NVIDIA_API_KEY_2` | 18 RPM/key | build.nvidia.com |
| **Cerebras** | `CEREBRAS_API_KEY` | 28 RPM | cloud.cerebras.ai |
| **Zhipu** | `ZHIPU_API_KEY` | generous | open.bigmodel.cn |

## Optional

| Provider | Env vars | Notes |
|----------|----------|-------|
| **GitHub** | `GITHUB_TOKEN` | Without token: 60 req/hr unauthenticated. With: 5000 req/hr |
| **Ollama** | — | Offline mode only (`--offline` flag). Install `qwen2.5-coder:3b-instruct-q4_K_M` |

## .env template

```env
# Groq (up to 4 keys for 112 RPM total)
GROQ_API_KEY_1=gsk_...
GROQ_API_KEY_2=gsk_...
GROQ_API_KEY_3=gsk_...
GROQ_API_KEY_4=gsk_...

# DeepSeek
DEEPSEEK_API_KEY_1=sk-...
DEEPSEEK_API_KEY_2=sk-...

# SambaNova
SAMBANOVA_API_KEY_1=...
SAMBANOVA_API_KEY_2=...

# SiliconFlow
SILICONFLOW_API_KEY_1=...
SILICONFLOW_API_KEY_2=...

# NVIDIA NIM
NVIDIA_API_KEY_1=nvapi-...
NVIDIA_API_KEY_2=nvapi-...

# Cerebras
CEREBRAS_API_KEY=...

# Zhipu
ZHIPU_API_KEY=...

# GitHub (optional but recommended)
GITHUB_TOKEN=ghp_...
```

## Provider Status

Live status is visible in the UI under **Providers**. The status column shows:

- `●` green — ready
- `⚠` yellow — degraded (rate limited or intermittent)
- `⚠ key` — invalid API key (regenerate)
- `💸` — out of credits (top up or switch key)
- `⚰` — model deprecated (update config.py)
- `✕` red — circuit open (too many consecutive failures)

ARIA routes around failed providers automatically using the fallback chain.
