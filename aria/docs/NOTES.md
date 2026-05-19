# ARIA v2 — Reference Repo Research Notes
## Phase Alpha 0.0001: What to Borrow from Each Project

---

## 1. assafelovic/gpt-researcher

**URL:** https://github.com/assafelovic/gpt-researcher
**Purpose:** Closest existing tool — generates research reports via LLMs

### What to Borrow
- **Sub-problem decomposition pattern:** Breaks a question into sub-questions, researches each independently
- **Report generation structure:** Introduction → Findings → Analysis → Conclusion flow
- **Parallel research execution:** Uses asyncio to research multiple sub-questions concurrently

### What to Ignore
- **Web-first focus:** Primarily scrapes web articles, not code. We focus on GitHub repos
- **Paid APIs:** Uses OpenAI/Anthropic paid keys. ARIA is 100% free APIs
- **No code analysis:** Doesn't read or evaluate actual source files

### Key Pattern to Adapt
```
gpt-researcher approach:                      ARIA approach:
  question → sub-questions                      idea → sub-problems
  → web search each (Selenium/Serp)             → GitHub search each (API)
  → scrape + summarize articles                 → clone + read READMEs + source
  → write report                                → extract patterns + write brief
```

---

## 2. stanford-oval/storm

**URL:** https://github.com/stanford-oval/storm
**Purpose:** Multi-perspective research synthesis system (Stanford)

### What to Borrow
- **→ Outline-first synthesis pattern:** Generates an outline BEFORE doing detailed research.
  This grounds everything and prevents scope creep.
- **Multi-perspective approach:** For each sub-problem, looks at it from different angles
  (implementation, architecture, alternatives, pitfalls)
- **Iterative refinement:** Outline → Research → Revise → Finalize loop

### What to Ignore
- **Wikipedia dependency:** STORM uses Wikipedia as its primary knowledge source.
  ARIA uses GitHub as primary source.
- **Knowledge curation loop:** STORM's "knowledge curation" is too heavy for ARIA's
  use case. We use a lighter gap-detection loop instead.

### Key Pattern to Adapt
```
STORM:                                    ARIA:
  topic → outline                          idea → ideal outcome
  → perspective search                     → sub-problem decomposition
  → deep dive each perspective             → GitHub deep dive each sub-problem
  → synthesize                             → synthesize (outline-first)
  → revise                                 → quality judge → gaps → re-research
```

---

## 3. dzhng/deep-research

**URL:** https://github.com/dzhng/deep-research
**Purpose:** Iterative deep research loop with gap detection

### What to Borrow
- **→ Gap-detection + re-research loop:** After initial research, identify what's
  missing and re-research. Max 2 loops to prevent infinite cycling.
- **Research depth scoring:** Score how well each finding addresses the original
  question, not just surface relevance.
- **Follow-up question generation:** Automatically generate follow-up questions
  to fill gaps found in initial research.

### What to Ignore
- **Browser automation:** deep-research uses Playwright for web scraping.
  ARIA uses structured APIs (GitHub API, Jina Reader) — more reliable.
- **Single-LLM design:** All reasoning through one model. ARIA uses a
  7-provider waterfall for different strengths.

### Key Pattern to Adapt
```
deep-research:                            ARIA:
  question → research                      idea → decompose
  → analyze for gaps                       → research all sub-problems
  → generate follow-up questions           → quality judge scores each finding
  → re-research gaps                       → re-research low-scoring areas
  → final answer                           → produce final brief
```

---

## 4. langchain-ai/langchain

**URL:** https://github.com/langchain-ai/langchain
**Purpose:** Framework for LLM application development

### What to Borrow
- **→ ReAct loop reference pattern:** The Thought → Action → Observation cycle
  is adapted as ARIA's PER (Planner-Executor-Reflector) pattern
- **Tool-calling patterns:** How to structure tool definitions and handle
  tool outputs cleanly
- **Agent state management:** Patterns for passing context between agents

### What to Ignore
- **The entire framework:** LangChain adds unnecessary abstraction for ARIA.
  ARIA is intentionally light — agents are plain async functions, not
  LangChain AgentExecutors.
- **Vector store dependencies:** LangChain pushes Chroma/Pinecone/etc.
  ARIA doesn't need a vector DB at this stage.

### Key Pattern to Adapt
```
LangChain ReAct:                          ARIA PER:
  Thought → decide next step               Plan → define sub-problem approach
  Action → call a tool                     Execute → GitHub search + analysis
  Observation → parse tool output          Reflect → quality judge scores result
  → Repeat                                 → Re-research if score < threshold
```

---

## Architecture Decisions from Research

| Decision | Source | Rationale |
|----------|--------|-----------|
| Outline-first synthesis | STORM | Prevents scope creep, keeps research focused |
| Gap-detection re-research loop | deep-research | Ensures completeness without infinite cycling |
| Parallel sub-problem research | gpt-researcher | 5 sub-problems × 3 concurrent = 2x speedup |
| Batch-first GitHub analysis | Original (ARIA spec) | 2 LLM calls vs 80-120 per sub-problem |
| Ideal outcome injection | Original (ARIA spec) | Solves context amnesia — biggest weakness of all 4 tools |
| Plain agents, not framework | Original | LangChain is overkill for 7 directed agents |
| Validated usage filter | Original (ARIA spec) | Filters repos without tests/examples/docs |

---

## Build Decisions for Phase Alpha 0.0001-5

1. **Build fresh** — ARIA's code-search focus is novel enough that forking
   gpt-researcher would be more work than building from scratch

2. **Python, not TypeScript** — All reference repos are Python. Ecosystem
   compatibility is cleaner in Python (Pydantic, aiohttp, Rich)

3. **No vector DB** — For <100 PDFs/repos, keyword + LLM scoring is sufficient.
   Skip Chroma/Pinecone until Sprint 4 if needed

4. **OpenAI-compatible clients** — DeepSeek, SambaNova, SiliconFlow, NVIDIA NIM
   all support OpenAI's API format. One AsyncOpenAI client + different base URLs
   covers 6/7 providers. Only Gemini and Ollama need separate clients.

5. **Sequential Ollama, parallel cloud** — RAM constraint (8GB) means Ollama
   calls use asyncio.Lock(). Cloud providers run in parallel via asyncio.gather.

6. **Dry-run before execute** — Borrowed from deep-research. Show cost/time
   estimate before making any API calls.
