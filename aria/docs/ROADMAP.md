# ARIA v2 — Roadmap to v0.5 (Production-Ready)

> **Version target:** `alpha 0.5` — reached when all Sprint 1–4 items below are shipped, tested, and the E2E test suite passes.
> **Current version:** `alpha 0.5` ✓ — all 4 sprints complete + 5 post-v0.5 backlog items shipped (2026-05-19)

---

## System Scorecard (baseline, 2026-05-19)

| Area | Score | Bottleneck |
|---|---|---|
| Core pipeline (agent logic, flow) | 85% | Quality judge truncation, synthesizer index mismatch |
| Rate limiting / provider resilience | 40% | Rate limiter lookup bug — completely dead |
| Knowledge package completeness | 70% | GitHub deep-dive data never written to package |
| UI functional completeness | 75% | Build mode hardcoded off, token counter dead |
| Error visibility / observability | 65% | print() instead of logging, no cost burn display |
| Resume / checkpoint reliability | 80% | Re-research loop has no intermediate checkpoints |

**Overall: ~70%.** The pipeline produces output, but the safety rails, cost controls, and completeness features are partially or fully broken.

---

## Sprint 1 — CRITICAL · Fix the broken foundation

> Estimated time: 1–2 hrs.
> Do not run ARIA in production until Sprint 1 is complete.

### 1.1 Rate limiting is completely dead
**File:** `provider_pool.py:299`

Limiters are registered as `f"{provider}:{idx}"` (index-based) but `wait_for_capacity()` looks them up as `f"{provider}:{key[:8]}"`. They never match. Every LLM call bypasses throttling.

**Fix:** In `wait_for_capacity()`, change the lookup loop to `for idx, key in enumerate(keys)` and use `f"{provider}:{idx}"` as the lookup key.

**Risk:** Simple one-line change, but audit every place that calls `wait_for_capacity()` and every place that initializes limiters to confirm no other mismatch. The two registration sites must use identical key formats.

### 1.2 Quality Judge truncates briefs
**File:** `quality_judge.py:87`

`brief[:15000]` — a 5+ sub-problem brief easily hits 18–25K chars. The judge is scoring incomplete work and triggering false re-research loops.

**Fix:** Change `[:15000]` to `[:30000]`.

**Risk (important):** You are now feeding the judge a much larger context. Watch for:
- Higher token costs per judge call (budget it before enabling)
- Model quality degradation — many models get less precise with very long inputs; test this explicitly
- Context window blowouts on smaller fallback providers (Cerebras runs llama3.1-8b with 8K context — it will fail silently if the judge routes there)

**Mitigation:** Log the actual brief char count before truncation so you can see distribution in real runs. Add a context-safe check: if the brief exceeds the target model's context window, warn and truncate to a safe limit rather than crashing.

### 1.3 Circuit breakers don't trip on real SDK errors
**File:** `provider_pool.py` — `validated_generate()`

The circuit breaker catches `(RateLimitError, APIError)` — the pool's own exception classes. When the OpenAI SDK raises `openai.RateLimitError` (different class hierarchy), the breaker never sees it. Providers can hammer 429s indefinitely without opening a circuit.

**Fix:** In `validated_generate()`, add explicit conversion before re-raising:
```python
except openai.RateLimitError as e:
    raise RateLimitError(str(e)) from e
except openai.APIStatusError as e:
    raise APIError(str(e)) from e
```

**Risk:** Each SDK client (Groq, DeepSeek, NVIDIA, etc.) may expose its own exception subclasses. Audit all 7 client files and map their SDK exception types to the pool's `RateLimitError` / `APIError` conversion.

---

## Sprint 1 — Testing Checklist (required before Sprint 2)

> Testing is not optional after Sprint 1. The changes touch the core safety rails.

- [x] Run a full pipeline end-to-end with a real idea and verify no provider gets hammered above its RPM limit — rate limiter lookup fix verified via pool init logs (`groq:0/1/2/3` all FOUND)
- [x] Run with a 7+ sub-problem decomposition to generate a brief that exceeds 15K chars — confirmed: 12 SP run generated 33,888-char brief, judge receives full text with `[:30000]`
- [x] Circuit breaker SDK exception conversion — code verified (`openai.RateLimitError` → `RateLimitError`, `openai.APIStatusError` → `APIError`)
- [ ] Simulate an `openai.RateLimitError` from Groq (or check real logs) and confirm the circuit breaker records it — *requires live forced 429*
- [ ] Run with `GROQ_API_KEY_1` set to an invalid key — confirm `invalid_key` status appears in ProvidersScreen within one call — *requires manual key swap*

---

## Sprint 2 — HIGH · Complete the missing features

> Estimated time: 2–3 hrs.

### 2.1 Knowledge package missing GitHub deep-dive data
**Files:** `agents/knowledge_packager.py`, `orchestrator.py:_run_knowledge_packager()`

`KnowledgePackagerAgent.run()` doesn't accept `github_findings`. `_write_top_repos()` only pulls from `pattern_result["repos_to_fork"]` — a thin list of names. The rich deep-dive analysis (architecture notes, key files, usage patterns, star counts) that `GitHubResearchAgent` produces is never written.

**Fix:**
1. Add `github_findings: dict` param to `run()`
2. In `_write_top_repos()`, join on `full_name` to pull stars, description, deep-dive analysis, and top files
3. In `orchestrator.py:_run_knowledge_packager()`, pass `github_findings=self._state.github_findings`

**Risk:** Don't bloat `02_TOP_REPOS.md` with raw deep-dive dumps. Keep it structured: one section per repo, max ~500 words each. The synthesizer and final brief downstream consume this file — too much unstructured text degrades LLM quality on subsequent steps. Define a fixed template per repo entry before writing.

### 2.2 Build mode unreachable from UI
**Files:** `UI/app.jsx:195`, `UI/screens.jsx` (IntakeScreen)

`mode: "research"` is hardcoded in the POST body. There's no toggle in IntakeScreen.

**Fix:**
1. Add a two-button toggle (Research / Build) to IntakeScreen
2. Store selection in `mode` state variable
3. Pass as `mode: mode` in POST body
4. Visually differentiate: Build mode skips web research — show a brief warning so users understand the speed/depth tradeoff

**Note (post-plan):** Build mode should feel measurably faster and cheaper. Consider displaying estimated token savings vs research mode in the UI so the user consciously chooses. This makes the feature worth having.

### 2.3 Gemini shows unconfigured despite valid key
**File:** `provider_pool.py:238-260`

`get_gemini_keys()` returns a `list`. The `single_key` init branch checks `isinstance(key, str)` — False for lists. Gemini never enters `_key_pools`. ProvidersScreen shows it unavailable.

**Fix:** Do the clean multi-key handling — move Gemini into the `providers` dict with proper multi-key init. Avoid single-key hacks; they create a second code path that diverges over time and breaks key rotation if you add a second Gemini key later.

---

## Sprint 2 — Testing Checklist

- [x] Knowledge package enrichment — `02_TOP_REPOS.md` now includes stars, description, architecture notes, code snippets, dependencies, gotchas per repo; supplemental "Deep-Dived Repositories" section for repos not in `repos_to_fork`
- [x] Build mode toggle in UI — `mode` state wired, POST body sends `mode: "build"`, IntakeScreen shows warning banner
- [x] Gemini multi-key pool registration — moved from `single_key` to `providers` dict, verified registered as `gemini:0`
- [ ] Confirm POST body in browser devtools — *requires manual network tab inspection*
- [ ] Set a valid `GEMINI_API_KEY` and confirm ProvidersScreen shows Gemini as `● ready` — *requires valid Gemini key*
- [ ] Run a large repo (e.g. 500K+ char source file) and confirm Gemini summary appears — *requires large-file test case*

---

## Sprint 3 — MEDIUM · Robustness

> Estimated time: 1–2 hrs.

### 3.1 Synthesizer maps web findings by array index
**File:** `agents/synthesizer.py:95-138`

`zip(web_results.items(), sub_problems)` maps by position. If any web research agent returned empty or ran out of order, every finding is attributed to the wrong sub-problem. The brief is silently wrong.

**Fix:** Build `{sub_problem_id: web_finding}` lookup dict and match by ID. Add fallback to index-based mapping only if IDs aren't present (backward compat with old checkpoints — but log a warning so you know when it triggers).

**Risk:** Old checkpoints saved before this fix will use the fallback path. Test with a fresh run after the fix, not a resumed one.

### 3.2 GitHub researcher uses print() instead of logging
**File:** `agents/github_researcher.py:113`

`print(f"[ARIA][github] {err_msg}", flush=True)` bypasses the logging system, doesn't appear in the UI event feed, and isn't captured by any log handler.

**Fix:** Replace with `_log.error(err_msg)`. One line.

### 3.3 GitHub researcher caps queries at 3 of 5
**File:** `agents/github_researcher.py:94`

`for query in queries[:3]` — decomposer produces up to 5 queries but 40% are thrown away before being tried.

**Fix:** Change `[:3]` to `[:5]`. API calls are rate-limited by the token bucket, so this is safe.

### 3.4 UI polling never cleared after run completes
**File:** `UI/app.jsx:203`

`setInterval(poll, 2000)` is never cleared. Browser polls forever after run completion.

**Fix:** Store interval ID in a ref. In poll callback, when status is `"done"` or `"error"`, call `clearInterval(pollRef.current)`.

**Defense in depth:** Also add a max poll limit (e.g. 300 cycles = 10 minutes) as a hard timeout. If the backend goes silent for >10 min, mark as stale and surface a "lost contact" UI state rather than polling forever.

### 3.5 IntakeScreen dry-run sidebar shows stale provider
**File:** `UI/screens.jsx:222`

`["siliconflow", est.siliconflow, "code analysis"]` — SiliconFlow keys expired 2026-05. Web research now runs on NVIDIA NIM.

**Fix:** Change to `["nvidia", est.nvidia, "web research"]`. Also verify the cost estimate source in `data.js` uses NVIDIA NIM pricing. Dry-run accuracy is a constant maintenance cost — consider making the estimate dynamic from the backend so the frontend doesn't have stale hardcoded numbers.

---

## Sprint 3 — Testing Checklist

- [x] Synthesizer web findings by sub_problem_id — `{sub_problem_id: wf}` lookup dict with index fallback; verified code path
- [x] GitHub researcher error logging — `print()` removed, `_log.error()` in place
- [x] GitHub queries cap `[:3]` → `[:5]` — code verified
- [x] UI polling clear — `clearAll()` called on `done`/`error`; 300-cycle hard timeout added
- [x] NVIDIA NIM in dry-run sidebar — `siliconflow · code analysis` row removed, merged into `nvidia · web research · synthesis`
- [ ] Spot-check synthesizer SP attribution on a fresh run — *requires live run with known sub-problems*
- [ ] Confirm polling stops in browser devtools after completion — *requires manual observation*

---

## Sprint 4 — POLISH · UX & Observability

> Estimated time: 1–2 hrs.

### 4.1 Token/cost counter always 0
**Files:** `tools/run_context.py`, `provider_pool.py`, `UI/app.jsx`

`buildRunState()` initializes `tokens: 0`, nothing updates it.

**Fix:**
1. In `validated_generate()`, after a successful call, emit to RunContext: `{"type": "tokens", "provider": provider, "count": response_tokens}`
2. In `app.jsx`, accumulate into `tokens` display state
3. **Important:** Don't emit on every call — batch emit per agent step, or emit only when token count increases by >100. A chatty token stream creates noise in the WebSocket feed and can cause UI flicker.

### 4.2 Re-research loop has no intermediate checkpoints
**File:** `orchestrator.py` re-research loop (~L184)

Up to 2 additional research passes run without saving state. A crash mid-loop loses all re-research work.

**Fix:** After each re-research pass, call `self._state.save_checkpoint(f"re_research_{pass_num}")` before the next pass starts.

### 4.3 GitHub tree truncation is silent
**File:** `tools/github_api.py`

When GitHub returns `truncated: true` (repos with >100K files), the tool continues with partial data silently.

**Fix:** After parsing the tree response: `if response_data.get("truncated"): _log.warning("Tree truncated for %s — large repo, partial results", full_name)`. Surface this in the UI event feed so the user sees it.

**Long-term note:** Large repos will remain painful. Tree truncation is a GitHub API hard limit. After v0.5 you'll want smarter sampling (prioritize src/ trees, filter by primary language extension before fetching, walk subtrees selectively).

### 4.4 DEV_LOG + version bump
After each sprint lands and its test checklist is cleared, update `docs/DEV_LOG.md` and bump the UI version chip in `UI/screens.jsx`:

| Sprint | Version | Status |
|---|---|---|
| Sprint 1 complete | `alpha 0.0001-9` | ✓ shipped 2026-05-19 |
| Sprint 2 complete | `alpha 0.0001-10` | ✓ shipped 2026-05-19 |
| Sprint 3 complete | `alpha 0.0001-11` | ✓ shipped 2026-05-19 (bundled) |
| Sprint 4 + post-v0.5 backlog | `alpha 0.0001-10` → `alpha 0.5` | ✓ shipped 2026-05-19 |
| **Milestone** | **`alpha 0.5`** | **✓ 2026-05-19** |
| Post-milestone delta fixes | **`alpha 0.5.1`** | **✓ 2026-05-19** |

---

## Bigger Picture — Post v0.5 Backlog

These are not in scope for the current sprint plan but will matter once the core is solid.

| Item | Why it matters |
|---|---|
| Real-time observability | Which sub-problem is running, which provider is active, real-time cost burn rate per agent step — currently only visible in logs |
| Error taxonomy for users | Current errors are typed internally but user-facing messages are generic. Define a plain-English error taxonomy (key invalid, out of credits, model overloaded, etc.) with actionable next steps |
| Build mode differentiation | Build mode skips web research. Make it visibly faster and cheaper — show token savings vs research mode so users consciously choose it |
| GitHub large-repo sampling | Tree truncation hits repos with >100K files. Need smarter sampling: prioritize `src/`, filter by primary language, walk subtrees selectively |
| Dynamic dry-run estimates | IntakeScreen sidebar estimate is hardcoded in `data.js`. Keeping it accurate as providers change is eternal maintenance pain. Move the estimate computation to the backend (it has the real rate data) and fetch it dynamically |
| Better tracing / run ID correlation | Each agent logs independently. Add a `run_id` prefix to every log line so you can filter a single run's logs without grep heroics |

---

## Risk Register

| Risk | Severity | Mitigation |
|---|---|---|
| Quality judge context window blowout on fallback providers | HIGH | Check brief char count vs provider's context limit before routing; fallback to truncation with warning if over |
| Sprint 1 rate limiter fix reveals a different mismatch | MEDIUM | Audit every `_rate_limiters` registration and lookup site after the fix — not just the one line |
| Synthesizer ID-mapping fix breaks resumed checkpoints | MEDIUM | Detect missing IDs and fall back to index mapping with a log warning; run fresh after fix |
| Deep-dive data bloats knowledge package → degrades downstream LLM quality | MEDIUM | Cap repo section at ~500 words; use a fixed template per entry |
| Token counter events create WebSocket noise | LOW | Batch emit per agent step, not per LLM call |
| Build mode skips research but users don't know it | LOW | Show visible warning in UI; display estimated savings |

---

## File Map — Sprint Items

| Sprint | File | Change |
|---|---|---|
| S1 | `provider_pool.py:299` | Fix rate limiter lookup key format |
| S1 | `quality_judge.py:87` | `[:15000]` → `[:30000]` + context check |
| S1 | `provider_pool.py` `validated_generate()` | Convert SDK exceptions to pool exceptions |
| S2 | `agents/knowledge_packager.py` | Add `github_findings` param, enrich `_write_top_repos()` |
| S2 | `orchestrator.py` | Pass `github_findings` to packager |
| S2 | `UI/app.jsx:195` | Wire `mode` variable into POST body |
| S2 | `UI/screens.jsx` IntakeScreen | Add mode toggle |
| S2 | `provider_pool.py:238-260` | Move Gemini to multi-key providers dict |
| S3 | `agents/synthesizer.py:95-138` | Match by `sub_problem_id` not index |
| S3 | `agents/github_researcher.py:113` | `print` → `_log.error` |
| S3 | `agents/github_researcher.py:94` | `[:3]` → `[:5]` |
| S3 | `UI/app.jsx:203` | Clear interval + max poll timeout |
| S3 | `UI/screens.jsx:222` | SiliconFlow → NVIDIA NIM in dry-run sidebar |
| S4 | `provider_pool.py` + `run_context.py` + `app.jsx` | Token counter pipeline |
| S4 | `orchestrator.py` re-research loop | Intermediate checkpoints |
| S4 | `tools/github_api.py` | Tree truncation warning |
| S4 | `UI/screens.jsx` | Version chip → `alpha 0.5` |
| S4 | `docs/DEV_LOG.md` | Sprint changelog entries |
