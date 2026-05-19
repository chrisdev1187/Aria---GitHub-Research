# ARIA v2 — Provider Setup

All providers are free-tier. Add keys to `.env` in the project root.

## Required (pipeline won't run without at least one)

| Provider | Env vars | Free tier | Get key |
|----------|----------|-----------|---------|
| **Groq** | `GROQ_API_KEY_1` … `GROQ_API_KEY_4` | 28 RPM/key → 112 RPM total | console.groq.com |
| **DeepSeek** | `DEEPSEEK_API_KEY_1`, `DEEPSEEK_API_KEY_2` | 58 RPM/key | platform.deepseek.com |

## Recommended (improves quality + speed)

| Provider | Env vars | Free tier | Get key |
|----------|----------|-----------|---------|
| **NVIDIA NIM** | `NVIDIA_API_KEY_1`, `NVIDIA_API_KEY_2` | 18 RPM/key | build.nvidia.com |
| **SambaNova** | `SAMBANOVA_API_KEY_1`, `SAMBANOVA_API_KEY_2` | 18 RPM/key | cloud.sambanova.ai |
| **Cerebras** | `CEREBRAS_API_KEY` | 28 RPM | cloud.cerebras.ai |
| **SiliconFlow** | `SILICONFLOW_API_KEY_1`, `SILICONFLOW_API_KEY_2` | 28 RPM/key | cloud.siliconflow.cn |
| **Zhipu** | `ZHIPU_API_KEY` | generous | open.bigmodel.cn |

## Optional

| Provider | Env vars | Notes |
|----------|----------|-------|
| **Gemini Flash** | `GEMINI_API_KEY` | Large file reads only (1M context). If unset, code extractor falls back to 30K char truncation silently |
| **GitHub** | `GITHUB_TOKEN` | Without token: 60 req/hr. With: 5000 req/hr. Strongly recommended |
| **Ollama** | — | Offline mode only (`--offline` flag). Requires `qwen2.5-coder:3b-instruct-q4_K_M` |

## .env template

```env
# Groq — primary (intake, decompose, quality judge) — up to 4 keys for 112 RPM total
GROQ_API_KEY_1=gsk_...
GROQ_API_KEY_2=gsk_...
GROQ_API_KEY_3=gsk_...
GROQ_API_KEY_4=gsk_...

# DeepSeek — GitHub research + pattern extraction
DEEPSEEK_API_KEY_1=sk-...
DEEPSEEK_API_KEY_2=sk-...

# NVIDIA NIM — web research + synthesis
NVIDIA_API_KEY_1=nvapi-...
NVIDIA_API_KEY_2=nvapi-...

# SambaNova — parallel research fallback
SAMBANOVA_API_KEY_1=...
SAMBANOVA_API_KEY_2=...

# Cerebras — fast fallback
CEREBRAS_API_KEY=...

# SiliconFlow — fallback chain
SILICONFLOW_API_KEY_1=...
SILICONFLOW_API_KEY_2=...

# Zhipu — last-resort fallback
ZHIPU_API_KEY=...

# Gemini Flash — large file reads (optional)
GEMINI_API_KEY=...

# GitHub — strongly recommended
GITHUB_TOKEN=ghp_...
```

## Provider → Agent assignment

| Agent | Primary | Fallback |
|-------|---------|---------|
| Intake | Groq | Cerebras → SiliconFlow → Zhipu |
| Decomposer | Groq | Cerebras → SiliconFlow → Zhipu |
| GitHub Researcher | DeepSeek | SiliconFlow |
| Web Researcher | NVIDIA NIM | Groq → Zhipu |
| Pattern Extractor | DeepSeek | Ollama (offline) |
| Synthesizer | NVIDIA NIM | SambaNova |
| Quality Judge | Groq | Cerebras (brief capped at 6K) → SiliconFlow → Zhipu |
| Large file reads | Gemini Flash | truncation at 30K chars |

## Provider Status (UI → Providers screen)

| Badge | Meaning | What to do |
|-------|---------|------------|
| `● ready` | Configured + healthy | Nothing |
| `⚠ rate limited` | Hitting RPM limit | ARIA retries automatically; add more keys to increase capacity |
| `⚠ degraded` | Intermittent errors | ARIA is routing around it; monitor |
| `✕ invalid key` | 401 from provider | Regenerate key and update `.env` |
| `💸 no credits` | 402 / insufficient balance | Top up on provider dashboard |
| `⚰ model error` | Model name wrong or deprecated | Update model name in `config.py` |
| `✕ circuit open` | 3+ consecutive failures | Provider auto-recovers in ~60s |
| `○ unconfigured` | No key set | Add key to `.env` to enable |

ARIA routes around failed providers automatically using the fallback chain. The circuit opens after 3 consecutive failures and recovers after 60 seconds.
