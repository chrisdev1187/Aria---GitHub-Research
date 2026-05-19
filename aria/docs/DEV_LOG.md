# ARIA v2 — Dev Log

---

## 2026-05-19 — Phase Alpha 0.0001-7 · Provider Health + Bug Fixes

### Provider error visibility (UI)
- `provider_pool.py`: added `record_error(provider, http_status, message)` + `get_provider_health()` — maps HTTP codes to typed errors (`invalid_key`, `no_credits`, `model_deprecated`, `rate_limited`)
- `main.py` status endpoint now returns structured `ui_status`, `ui_color`, `last_error`, `circuit_state`, `circuit_failures`
- `UI/screens.jsx` ProvidersScreen: color-coded status badges (● ready / ⚠ warn / ✕ failed), `last_error.msg` shown inline, circuit failure counts
- IntakeScreen sidebar: shows error reason in red/yellow instead of model name when provider is degraded

### StopIteration crash fix (orchestrator)
- `LoopGuard.tick()` was raising `StopIteration` inside async coroutines — Python 3.7+ (PEP 479) converts this to `RuntimeError: coroutine raised StopIteration`
- Introduced `AgentStepLimitReached(RuntimeError)` custom exception
- Research guards now scale: `max_steps=len(sub_problems) + 2` — 11 SPs no longer hit the 10-step cap
- `_run_web_research` given same exception-isolation pattern as `_run_github_research`

### GitHub query shortening
- `agents/github_researcher.py`: added `_shorten_query()` — strips stopwords, trims to 4 keywords
- Tries 4-word query first, falls back to 3-word if 0 results
- Decomposer system prompt updated: Rule 6 — max 5 words per GitHub query

### Usage filter relaxed
- `tools/github_api.py` `passes_usage_filter()`: lowered from `>500 stars` to `>=5 stars or <6 months old`
- Eliminates false negatives on new/niche repos

### Provider config fixes
- `sambanova`: updated model to `Meta-Llama-3.3-70B-Instruct` (3.1-8B deprecated 2026-05)
- `cerebras`: corrected model to `llama3.1-8b` (llama-3.3-70b not available on Cerebras)
- `ollama`: corrected model names to `qwen2.5-coder:3b-instruct-q4_K_M` / `7b`
- Web researcher primary LLM changed from SiliconFlow (401 expired keys) to NVIDIA NIM

### Web researcher fallback
- `agents/web_researcher.py`: fallback chain `NvidiaClient → GroqClient → ZhipuClient`
- Added `logging.getLogger("aria.web_researcher")` with per-failure warning output

### All client files patched
- All 7 provider clients now pass `_provider=self.provider` to `validated_generate()` so HTTP errors are recorded in `pool._last_errors`

---

## 2026-05-17 — Phase Alpha 0.0001-5 · UI Dashboard

### UI built (React/Vite)
- Intake screen: idea textarea, dry-run estimate sidebar, provider status chips
- Active run screen: live agent-swarm DAG, token/cost counters, live event feed via WebSocket
- Knowledge package screen: tabbed file browser (Brief / Sub-problems / Patterns / Repos / Raw artifacts)
- Past runs screen: searchable run history with quality scores
- Providers screen: key status table
- Prompts screen: editable system prompt viewer
- Dark mode toggle

### WebSocket live feed
- `main.py` server-sent events → WebSocket bridge
- Agent events streamed: `intake`, `decompose`, `github_SP-N`, `web_SP-N`, `pattern`, `synth`, `judge`, `package`

---

## 2026-05-16 — Phase Alpha 0.0001-4 · Provider Pool

### Provider pool architecture
- `provider_pool.py`: `ProviderPool` with per-provider circuit breakers (CLOSED/OPEN/HALF_OPEN)
- Token-bucket rate limiters per provider
- `validated_generate()`: schema validation via Pydantic, retry on malformed JSON
- Fallback chain: Groq → Cerebras → SiliconFlow → Zhipu

### Providers integrated
- Groq (4 keys, llama-3.3-70b-versatile) — primary fast inference
- DeepSeek (2 keys, deepseek-chat) — deep analysis
- SambaNova (2 keys) — parallel research
- SiliconFlow (2 keys, Qwen2.5-72B) — web research
- NVIDIA NIM (2 keys) — synthesis
- Cerebras (1 key) — fast fallback
- Zhipu (1 key, glm-4-flash) — last-resort fallback
- Ollama (local) — offline mode only

---

## 2026-05-15 — Phase Alpha 0.0001-3 · 7-Agent Pipeline

### Agents built
1. `IntakeAgent` — parses idea, infers domain/complexity, defines ideal outcome
2. `DecomposerAgent` — breaks idea into 3-7 implementation sub-problems with GitHub query keywords
3. `GitHubResearchAgent` — searches GitHub API, scores repos, deep-dives top results
4. `WebResearchAgent` — Jina Reader + DuckDuckGo scrape → LLM synthesis per SP
5. `PatternExtractorAgent` — cross-SP pattern identification
6. `SynthesizerAgent` — outline-first brief generation
7. `QualityJudgeAgent` — scores brief on 6 axes, flags gaps, triggers re-research loop

### State + checkpointing
- `state.py`: `ResearchState` saves each agent's output as JSON checkpoint
- Resume from any step after interrupt

### Knowledge packager
- `agents/knowledge_packager.py`: assembles `knowledge_package/` from all agent outputs
- Files: `00_PROBLEM`, `01_DECOMPOSITION`, `02_TOP_REPOS`, `04_PATTERNS`, `05_LIBRARIES`, `06_BUILD_PLAN`

---

## 2026-05-14 — Phase Alpha 0.0001-1 · Project Bootstrap

### Architecture decided
- Reference repos studied: `gpt-researcher`, `stanford-oval/storm`, `dzhng/deep-research`, `langchain` (see `docs/NOTES.md`)
- Key decisions: plain async agents (no framework), batch-first GitHub analysis (2 calls vs 80+), ideal-outcome injection, 7-provider waterfall

### Repo structure
- `agents/` — 7 agent modules
- `tools/` — API clients (GitHub, Jina, provider clients)
- `config.py` — all env + rate-limit config
- `provider_pool.py` — circuit breakers + key rotation
- `orchestrator.py` — pipeline wiring
- `state.py` — checkpoint persistence
- `main.py` — CLI entry + FastAPI serve mode
- `UI/` — React dashboard
