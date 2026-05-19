# ARIA v2 — Architecture

## Pipeline

```
Idea (plain English)
  │
  ▼
01 · Intake              parse scope, infer domain/complexity, define ideal outcome
  │
  ▼
02 · Decompose           break into 3–7 sub-problems, assign ≤5 GitHub query keywords each
  │
  ├──────────────────────────────────────────────┐
  ▼                                              ▼
03 · GitHub Research (parallel per SP)    04 · Web Research (parallel per SP)
    search API → score repos                  Jina Reader + DDG → LLM synthesis
    → deep dive top 3 results                 per sub-problem
    → usage filter (≥5 stars or <6mo)         (skipped in build mode)
  │                                              │
  └──────────────┬───────────────────────────────┘
                 ▼
         05 · Pattern Extractor
              cross-SP pattern identification
                 │
                 ▼
         06 · Synthesizer
              outline-first brief generation
              (web findings matched by sub_problem_id, not array index)
                 │
                 ▼
         07 · Quality Judge
              6-axis scoring → gap detection
              → re-research loop (max 2, each pass checkpointed)
                 │
                 ▼
         08 · Knowledge Packager
              assembles knowledge_package/
```

## Agents

| # | Agent | Provider | Purpose |
|---|-------|----------|---------|
| 1 | IntakeAgent | Groq | Parse idea, infer domain, define ideal outcome |
| 2 | DecomposerAgent | Groq | Sub-problem decomposition + GitHub queries |
| 3 | GitHubResearchAgent | DeepSeek | GitHub search → score → deep dive top repos |
| 4 | WebResearchAgent | NVIDIA NIM | Jina Reader + DDG + LLM synthesis per SP |
| 5 | PatternExtractorAgent | DeepSeek | Cross-SP pattern identification |
| 6 | SynthesizerAgent | NVIDIA NIM | Outline-first brief generation |
| 7 | QualityJudgeAgent | Groq | 6-axis score + gap detection + re-research trigger |
| 8 | KnowledgePackager | — | Assemble output files |

## Provider Pool

**Key rotation** — all providers with multiple keys rotate across them on every call. Clients are cached per key (not per provider), so keys 0–N are all used in round-robin. `wait_for_capacity()` peeks at the current rotation index to throttle on the correct key's bucket.

**Circuit breakers** — per-provider (CLOSED → OPEN → HALF_OPEN). Opens after 3 consecutive failures, recovers after 60s. Both the pool's own `RateLimitError`/`APIError` and SDK-level `openai.RateLimitError`/`openai.APIStatusError` are caught and converted correctly.

**Token-bucket rate limiting** — per key, per provider. Refills at `rpm/60` tokens/second. Safe across parallel agent tasks (`asyncio.Lock` per bucket).

**Error recording** — HTTP status → typed error (`invalid_key`, `no_credits`, `model_deprecated`, `rate_limited`). Surfaced in the UI Providers screen with actionable next-step text.

**Fallback chain** — Groq → Cerebras → SiliconFlow → Zhipu

**Provider context limits** — Quality Judge is context-aware: Groq gets `brief[:30000]`, Cerebras (8K ctx model) gets `brief[:6000]` with a log warning. SiliconFlow/Zhipu get `brief[:20000]`.

## GitHub Query Strategy

- Decomposer generates ≤5 keyword queries per SP (longer queries return 0 results)
- `_shorten_query()` strips stopwords and trims to 4 keywords as fallback
- Usage filter: ≥5 stars OR <6 months old (eliminates abandoned repos, keeps new/niche ones)
- Deep dive: README + key source files → architecture pattern + code snippets
- Large repos: when tree is `truncated: true`, `_sample_truncated_tree()` fetches targeted subtrees for `src/`, `lib/`, `app/`, `core/`, `pkg/`, `internal/`, `cmd/` (up to 3 dirs, deduplicated)

## State / Checkpointing

Each agent writes a JSON checkpoint to `output/<run_id>/`. Any step can be resumed after interrupt — the orchestrator checks `state.is_done()` before re-running.

Re-research loop: each pass saves `re_research_N` before the next pass starts. A crash mid-loop resumes from the last completed pass.

## Observability

**Live (UI):** active agent name, current provider, per-agent wall-clock timings, total LLM call counter.

**File logs:** `output/<run_id>/aria.log` — every line tagged with `run_id`, `level`, `logger name`. Format: `TIMESTAMP | LEVEL | RUN_ID | aria.module | message`. Filter a single run with `grep <run_id> aria.log`.

## Knowledge Package Output

```
knowledge_package/
  00_PROBLEM.md         restated problem + ideal outcome
  01_DECOMPOSITION.md   sub-problems with GitHub query keywords
  02_TOP_REPOS.md       repos to study: stars, architecture, key pattern,
                        code snippet, dependencies, gotchas, fork guidance
                        + supplemental "Deep-Dived Repositories" section
  04_PATTERNS.md        architectural patterns extracted across all SPs
  05_LIBRARIES.md       library table with justifications
  06_BUILD_PLAN.md      full synthesized brief + recommended build order
  07_WEB_RESEARCH.md    web research findings per sub-problem
  08_RISKS.md           risk analysis
  ARIA_research_brief.md  full narrative brief (same as 06 but standalone)
```

Feed `06_BUILD_PLAN.md` (or the full folder) to a coding agent to start Sprint 1.
