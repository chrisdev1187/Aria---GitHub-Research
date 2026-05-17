# ARIA Architecture Documentation

## System Overview

ARIA (Agentic Research Intelligence Architecture) is a multi-agent AI research system that transforms a software idea into a structured, actionable knowledge package. It operates as a directed acyclic graph of specialized agents, each responsible for a distinct research phase.

## Core Design Principles

1. **Separation of Concerns** — Each agent handles exactly one phase of the pipeline
2. **Resilience First** — Circuit breakers, fallback chains, and rate limiting at every layer
3. **Parallel Where Possible** — Research per sub-problem runs concurrently via asyncio
4. **Checkpointed State** — Every agent's output is persisted for resumability
5. **Provider Agnostic** — LLM clients are swappable, with automatic fallback between providers

---

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         CLI (main.py)                        │
│  typer commands: run | status | providers | health | serve   │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                    Orchestrator (orchestrator.py)             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │ LoopGuard│  │ResearchSt│  │ Progress  │  │ Checkpoint │  │
│  │ (max 10  │  │ate (disk │  │ (Rich CLI)│  │  Handler   │  │
│  │ steps)   │  │ persist) │  │           │  │ (main.py)  │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────┬─────┘  │
│                                                    │        │
│  ┌─────────────────────────────────────────────────┼──────┐ │
│  │ Agent Pipeline                                  │      │ │
│  │                                                 ▼      │ │
│  │  1. Intake ────► 2. Decomposer ────► Research ────►   │ │
│  │       │                │             │    │            │ │
│  │       │                │    ┌────────┘    └────────┐   │ │
│  │       │                │    ▼                      ▼   │ │
│  │       │                │  GitHub Research   Web Research│ │
│  │       │                │  (per sub-problem) (per sub-pr)│ │
│  │       │                │    └────────┬─────────┘        │ │
│  │       │                │             ▼                   │ │
│  │       │                │   5. Pattern Extractor         │ │
│  │       │                │             │                  │ │
│  │       │                │             ▼                  │ │
│  │       │                │   6. Synthesizer               │ │
│  │       │                │             │                  │ │
│  │       │                │             ▼                  │ │
│  │       │                │   7. Quality Judge ◄──┐       │ │
│  │       │                │             │         │       │ │
│  │       │                │         [re-research]─┘       │ │
│  │       │                │             │                  │ │
│  │       │                │             ▼                  │ │
│  │       │                │   8. Knowledge Packager       │ │
│  │       └────────────────┴────────────────────────────────┘ │
│  └──────────────────────────────────────────────────────────┘┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                     Output (knowledge_package/)               │
│  README.md │ PROBLEM.md │ DECOMPOSITION.md │ TOP_REPOS.md   │
│  PATTERNS.md │ LIBRARIES.md │ BUILD_PLAN.md │ WEB_RESEARCH.md │
│  RISKS.md │ extracted_code/ │ [project/ (build mode)]       │
└───────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                    UI Dashboard (main.py serve)               │
│  React SPA │ Real-time polling │ Swarm visualization         │
│  Agent status │ Sub-problem cards │ Logs │ Package viewer    │
└──────────────────────────────────────────────────────────────┘
```

---

## Agent Specifications

### 1. Intake Agent (`agents/intake.py`)

**Purpose**: Transform raw natural language idea into structured analysis.

**Provider**: Groq (default) → Ollama (offline)

**Output Schema**:
```json
{
  "ideal_outcome": "A CLI tool that monitors GitHub releases...",
  "domain": ["cli", "devops"],
  "primary_language": "Python",
  "complexity_estimate": "medium",
  "core_problems": ["GitHub API polling", "Slack integration"]
}
```

**Key Logic**:
- Loads system prompt from `prompts/intake_system.txt`
- Uses `validated_generate` for structured JSON output
- Falls back to Ollama with Qwen 7B when `--deep` flag is set

---

### 2. Decomposer Agent (`agents/decomposer.py`)

**Purpose**: Break the idea into 3-7 specific, searchable technical sub-problems.

**Provider**: Groq → Cerebras → SiliconFlow → Zhipu

**Output Schema** (per sub-problem):
```json
{
  "id": "SP-1",
  "title": "GitHub Release Monitoring System",
  "description": "Design a system that polls GitHub API...",
  "why_critical": "Core functionality that all other features depend on",
  "github_search_queries": ["github release monitoring api", "..."]
}
```

**Key Logic**:
- Generates search queries for both GitHub and web research
- Each sub-problem includes Stack Overflow tags and package-specific search terms
- Enforces 3-7 sub-problem range

---

### 3. GitHub Research Agent (`agents/github_researcher.py`)

**Purpose**: Research GitHub repositories for each sub-problem.

**Provider**: DeepSeek → Groq → Zhipu

**Process**:
1. **COLLECT** — Searches GitHub API, fetches READMEs (I/O only, no LLM)
2. **BATCH ANALYSE** — Single LLM call scores 20+ candidate repos on relevance, code quality, maintenance, and utility
3. **DEEP DIVE** — Validated usage filter (tests, activity) + detailed analysis of top 3 repos

**Key Features**:
- Usage filter checks for tests/examples directory, code blocks in README
- Parallel fetching via asyncio
- Token-aware file prioritization (manifest files first, then source)

---

### 4. Web Research Agent (`agents/web_researcher.py`)

**Purpose**: Find technical articles, tutorials, and documentation.

**Provider**: SiliconFlow (Qwen2.5-72B)

**Process**:
1. Generates targeted search queries from sub-problem data
2. Searches via DuckDuckGo, deduplicates, filters for technical content
3. Enriches top results using Jina Reader
4. LLM synthesizes insights, approaches, articles, and pitfalls

**Key Features**:
- Domain-based filtering (github.com, docs.*, stackoverflow.com)
- Rate-limited with 2-second delay between DDG requests
- Content extraction via `r.jina.ai`

---

### 5. Pattern Extractor (`agents/pattern_extractor.py`)

**Purpose**: Aggregate all research findings into reusable patterns.

**Provider**: DeepSeek → Ollama (offline)

**Output Schema**:
```json
{
  "architectural_patterns": ["Event-driven polling", "..."],
  "libraries_to_use": [
    {"name": "PyGithub", "version": ">=2.0", "reason": "GitHub API client"}
  ],
  "repos_to_fork": [
    {"name": "owner/repo", "url": "...", "why": "Similar release monitoring"}
  ],
  "anti_patterns": ["Polling too frequently", "..."],
  "gotchas": ["GitHub API rate limits per token"],
  "performance_considerations": ["Caching response data"],
  "security_considerations": ["Token storage"]
}
```

**Key Logic**:
- Consolidates GitHub findings (relevance scores, architecture, key patterns) and web findings (key insights)
- System prompt enforces structured JSON output

---

### 6. Synthesizer (`agents/synthesizer.py`)

**Purpose**: Generate the master research brief.

**Provider**: NVIDIA NIM → SambaNova → Groq → Zhipu

**Process**:
- Generates 5 sections: Header/Summary, Decomposition, Sub-problem Findings, Architecture, Build Order
- Each section gets the "ideal outcome" injected to maintain focus (context amnesia prevention)
- Final output is a comprehensive markdown document

---

### 7. Quality Judge (`agents/quality_judge.py`)

**Purpose**: Score the brief and decide if re-research is needed.

**Provider**: Groq → Cerebras → SiliconFlow → Zhipu

**Scoring Dimensions**:
| Dimension | Weight | Description |
|-----------|--------|-------------|
| Ideal Outcome Alignment | 0-10 | Does the brief address the core idea? |
| Sub-problem Coverage | 0-10 | Are all sub-problems thoroughly researched? |
| Architecture Actionability | 0-10 | Are implementation paths clear? |
| Specific Recommendations | 0-10 | Are concrete repos/libraries recommended? |

**Verdicts**:
- **SHIP** (≥8/10) — Ready for implementation
- **NEEDS_GAPS_FILLED** (5-7/10) — Minor gaps, proceed with caution
- **RE_RESEARCH** (<5/10) — Trigger up to 2 re-research loops

---

### 8. Knowledge Packager (`agents/knowledge_packager.py`)

**Purpose**: Stitch all outputs into a structured deliverable.

**Output Directory Structure**:
```
knowledge_package/
├── README.md               # Project overview & usage guide
├── 00_PROBLEM.md           # Problem statement & ideal outcome
├── 01_DECOMPOSITION.md     # Sub-problem breakdown
├── 02_TOP_REPOS.md         # Ranked repos with analysis
├── 03_EXTRACTED_CODE/      # Source files from repos
├── 04_PATTERNS.md          # Architectural patterns
├── 05_LIBRARIES.md         # Recommended libraries
├── 06_BUILD_PLAN.md        # Implementation phases
├── 07_WEB_RESEARCH.md      # Web findings per sub-problem
└── 08_RISKS.md             # Anti-patterns & gotchas
```

**Build Mode** (when `--mode build`):
- Deeper code extraction (25 files per repo, 10 repos max)
- Generates `project/` scaffold with:
  - Language-specific directory structure
  - Package manager config (requirements.txt, package.json, etc.)
  - Entry point and test skeleton
  - BUILD_NOTES.md with implementation guidance
  - `ARIA_build_handoff.md` designed for AI coding tools

---

## Multi-Provider LLM System

### Provider Pool (`provider_pool.py`)

The `ProviderPool` singleton manages all LLM API interactions:

```
ProviderPool (singleton)
├── Groq (4 keys, ~112 RPM total)
├── DeepSeek (2 keys, ~116 RPM total)
├── SambaNova (1 key)
├── SiliconFlow (1 key)
├── NVIDIA (1 key)
├── Cerebras (1 key)
├── Zhipu (1 key)
├── Gemini (1 key)
│
└── Rate Limiters (TokenBucketLimiter per key)
└── Circuit Breakers (5 failures → 60s open)
```

**Key Rotation**: Each provider can have multiple API keys (e.g., `GROQ_API_KEY`, `GROQ_API_KEY_2`, `GROQ_API_KEY_3`, `GROQ_API_KEY_4`). Keys are used in round-robin fashion.

**Rate Limiting**: Each key has a `TokenBucketLimiter` that enforces RPM limits. When a key is exhausted, requests are queued via `asyncio.sleep` until capacity is available.

**Circuit Breaker**: After 5 consecutive failures, a provider enters OPEN state for 60 seconds, then transitions to HALF_OPEN to test recovery. This prevents cascading failures across the pipeline.

### Fallback Chain

Each client implements a fallback chain. For example, GroqClient:

```
groq_client.generate() →
  try Groq → if fails:
  try Cerebras → if fails:
  try SiliconFlow → if fails:
  try Zhipu → if all fail:
  raise ProviderUnavailable
```

---

## State Management

### ResearchState (`state.py`)

The `ResearchState` class provides disk-persisted checkpointing:

```python
state = ResearchState(idea)
state.checkpoint("intake", result)     # Saves to output/{run_id}/artifacts/intake.json
state.checkpoint("decomposer", result) # Saves to output/{run_id}/artifacts/decomposer.json
state.fail("github_*", error)          # Marks agent as failed
state.load("pattern_extractor")        # Loads saved artifact
state.is_done("synthesizer")           # Check agent completion
```

**Storage Layout**:
```
output/{run_id}/
├── artifacts/
│   ├── intake.json
│   ├── decomposer.json
│   ├── github_SP-1.json
│   ├── web_SP-1.json
│   ├── pattern_extractor.json
│   └── ...
├── state.json              # Current state summary
├── aria.log                # Pipeline log
└── knowledge_package/      # Final output
```

### RunContext (`tools/run_context.py`)

The `RunContext` singleton is a thread-safe state holder for the UI:

- **Thread Safety**: All mutations use `threading.Lock()`
- **Fields**: status, phase, progress_pct, idea, sub_problems, research_statuses, patterns, logs, etc.
- **Export**: `to_dict()` returns a snapshot for API responses
- **Polling**: UI polls `/api/status` every 2 seconds during a run

---

## UI Architecture

### Tech Stack
- **Runtime**: Python HTTP server (built-in) serving a React SPA
- **Frontend**: React 18 + Babel standalone (no build step required)
- **Styling**: Custom CSS with oklch color space, light/dark themes
- **Communication**: REST polling via `/api/status` endpoint

### Component Tree
```
index.html
└── <div id="root">
    └── App (app.jsx)
        ├── Topbar
        │   ├── Brand
        │   ├── PhaseIndicator
        │   └── ThemeToggle
        ├── Main
        │   ├── IntakeScreen (when view === "intake")
        │   │   ├── IdeaInput
        │   │   ├── FocusSelector
        │   │   ├── DryRunEstimate
        │   │   └── ProviderStatus
        │   ├── PipelineScreen (when view === "running")
        │   │   ├── AgentSwarm (swarm.jsx)
        │   │   ├── ProgressBar
        │   │   ├── SubProblemCards
        │   │   ├── AnalyticsPanel
        │   │   └── LogFeed
        │   └── PackageScreen (when view === "done")
        │       ├── TabNav (Brief, Sub-problems, Patterns, Repos, Raw)
        │       ├── MarkdownRenderer
        │       ├── FileBrowser
        │       ├── PatternGallery
        │       └── RepoList
        └── TweaksPanel
            ├── ThemeSelector
            ├── AccentColorPicker
            └── PipelineControls
```

### Data Flow (Frontend)
```
data.js: fetchStatus()
    │
    ├──► window.ARIA_DATA (global state)
    │       ├── sub_problems, patterns, package_files
    │       ├── quality scores, brief_md
    │       └── providers, hardware info
    │
    └──► app.jsx: useApiRun()
            │
            ├── buildRunState(api_response) → local React state
            │       ├── phase, progress_pct
            │       ├── agents (status per agent)
            │       ├── sps (sub-problem statuses)
            │       └── logs, tokens
            │
            └── setView("intake" | "running" | "done")
```

---

## Error Handling & Resilience

### Pipeline Errors
- Caught in `_run_in_background()` with full traceback capture
- `run_context` updated with `status="error"` and stored traceback
- UI shows error log entry with details

### LLM Provider Errors
- **Rate Limit (429)**: Automatic retry with backoff via `TokenBucketLimiter`
- **Auth/Balance (402)**: Triggers fallback chain to next provider
- **Service Unavailable (502/503)**: Circuit breaker opens, fallback chain activated
- **Schema Validation**: `validated_generate` retries with repair prompts

### Agent Errors
- `LoopGuard` prevents infinite loops (max 10 steps per agent)
- `except Exception` in each agent reports failure via `SchemaValidationFailed`
- Orchestrator catches and logs errors, continues with partial results

---

## Performance Considerations

### LLM Call Budget
| Agent | LLM Calls | Tokens (est.) |
|-------|-----------|---------------|
| Intake | 1 | ~1K |
| Decomposer | 1 | ~2K |
| GitHub Research (per SP) | 2 | ~8K |
| Web Research (per SP) | 2 | ~6K |
| Pattern Extractor | 1 | ~5K |
| Synthesizer | 5 | ~15K |
| Quality Judge | 1 | ~3K |
| Knowledge Packager | 1 | ~2K |

### Concurrency
- GitHub + Web research per sub-problem: `asyncio.Semaphore(3)`
- GitHub API calls within a sub-problem: parallel via asyncio
- LLM calls within an agent: sequential (structured output requirement)

### Resource Constraints
- Default: 8GB RAM, Intel UHD 620 (conservative)
- Ollama models: Qwen 7B recommended for `--deep` mode
- File extraction: max 15 files per repo (25 in build mode)
- Web content: capped at 50K characters per URL via Jina Reader
