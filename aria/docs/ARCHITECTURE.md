# ARIA v2 — Architecture

## Pipeline

```
Idea (plain English)
  │
  ▼
01 · Intake         parse scope, infer domain/complexity, define ideal outcome
  │
  ▼
02 · Decompose      break into 3–7 sub-problems, assign GitHub query keywords
  │
  ├──────────────────────────────────────────────┐
  ▼                                              ▼
03 · GitHub Research (parallel, max 3)    04 · Web Research (parallel, max 3)
    search API → score repos                  Jina Reader + DDG → LLM synthesis
    → deep dive top results                   per sub-problem
  │                                              │
  └──────────────┬───────────────────────────────┘
                 ▼
         05 · Pattern Extractor
              cross-SP pattern identification
                 │
                 ▼
         06 · Synthesizer
              outline-first brief generation
                 │
                 ▼
         07 · Quality Judge
              6-axis scoring → gap detection
              → re-research loop (max 2)
                 │
                 ▼
         08 · Knowledge Packager
              assembles knowledge_package/
```

## Agents

| # | Agent | Model | Purpose |
|---|-------|-------|---------|
| 1 | IntakeAgent | Groq | Parse idea, define ideal outcome |
| 2 | DecomposerAgent | Groq | Sub-problem decomposition |
| 3 | GitHubResearchAgent | DeepSeek | GitHub search + deep dive |
| 4 | WebResearchAgent | NVIDIA NIM | Jina/DDG + synthesis |
| 5 | PatternExtractorAgent | SambaNova | Cross-SP patterns |
| 6 | SynthesizerAgent | NVIDIA NIM | Outline-first brief |
| 7 | QualityJudgeAgent | Groq | Score + gap detection |
| 8 | KnowledgePackager | — | Assemble output files |

## Provider Pool

- Circuit breakers per provider (CLOSED → OPEN → HALF_OPEN)
- Token-bucket rate limiting per provider
- Key rotation across multiple keys per provider
- Error recording: maps HTTP status codes → `invalid_key / no_credits / model_deprecated / rate_limited`
- Fallback chain: Groq → Cerebras → SiliconFlow → Zhipu

## State / Checkpointing

Each agent writes a JSON checkpoint to `output/<run_id>/`. Any step can be resumed after interrupt. The orchestrator checks `state.is_done()` before re-running a step.

## GitHub Query Strategy

- Decomposer generates ≤5 keyword queries per SP (longer queries return 0 results from GitHub API)
- `_shorten_query()` strips stopwords and trims to 4 keywords as fallback
- Usage filter: ≥5 stars OR <6 months old (eliminates abandoned repos, keeps new/niche ones)
- Deep dive: reads README + key source files, extracts architecture pattern + code snippets

## Knowledge Package Output

```
knowledge_package/
  00_PROBLEM.md       — restated problem + ideal outcome
  01_DECOMPOSITION.md — sub-problems with queries
  02_TOP_REPOS.md     — recommended repos + why
  04_PATTERNS.md      — architectural patterns extracted
  05_LIBRARIES.md     — library table with justifications
  06_BUILD_PLAN.md    — full synthesized brief + build order
```

Feed `06_BUILD_PLAN.md` (or the full folder) to a coding agent to start Sprint 1.
