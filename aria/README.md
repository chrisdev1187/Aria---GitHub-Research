# ARIA v2 — alpha 0.5.1

**Agentic Research Intelligence Architecture** — deep code research system.

Describe a build idea in plain English. ARIA decomposes it, fans 8 agents across GitHub + the web in parallel, and produces a build-ready knowledge package.

---

## Quickstart

```bash
# 1. Add API keys
cp .env.example .env   # fill in at least GROQ_API_KEY_1

# 2. Install
pip install -r requirements.txt

# 3. Run CLI
python main.py "build a CLI tool that monitors GitHub repos for new releases"

# 4. Or launch the UI
python main.py serve
# open http://localhost:8080
```

Output lands in `output/<run_id>/knowledge_package/`. Feed `06_BUILD_PLAN.md` to a coding agent to start building.

---

## Modes

| Mode | What it does |
|------|-------------|
| `research` | Full pipeline: GitHub + web research, synthesis, quality judge |
| `build` | Skips web research — faster and cheaper, produces scaffold + brief |
| `--dry-run` | Estimates API calls without running anything |
| `--offline` | Uses local Ollama only, no external API calls |
| `--resume` | Resumes the last interrupted run from its checkpoint |

---

## Output

```
knowledge_package/
  00_PROBLEM.md         restated problem + ideal outcome
  01_DECOMPOSITION.md   sub-problems with GitHub queries
  02_TOP_REPOS.md       repos with stars, architecture notes, code snippets, gotchas
  04_PATTERNS.md        cross-SP architectural patterns
  05_LIBRARIES.md       library table with justifications
  06_BUILD_PLAN.md      full synthesized brief + recommended build order
  07_WEB_RESEARCH.md    web research findings per sub-problem
  08_RISKS.md           risk analysis
  ARIA_research_brief.md  full narrative brief
```

---

## UI

`python main.py serve` launches the React dashboard at `http://localhost:8080`.

Screens: **Intake** · **Pipeline** (live DAG + agent timings) · **Package** (file browser) · **Past Runs** · **Providers** · **Prompts**

Live observability: active agent name, current provider, per-agent timings, LLM call counter.

---

## Docs

| | |
|---|---|
| [Architecture](docs/ARCHITECTURE.md) | Pipeline, agents, provider pool, output format |
| [Providers](docs/PROVIDERS.md) | API key setup, .env template, status indicators |
| [Roadmap](docs/ROADMAP.md) | Sprint history, completion scorecard |
| [Dev Log](docs/DEV_LOG.md) | Change history by session |
| [Research Notes](docs/NOTES.md) | Reference repos studied during design |

---

*By chrisdev1187 · Nagasubramanian Methodology*
