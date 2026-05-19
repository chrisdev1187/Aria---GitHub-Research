/* Aria — Screen components: Intake, Pipeline, Package */

(function () {
  const { useState, useMemo, useEffect, useRef } = React;

  // Safely coerce any value to a renderable string — prevents "Objects are not valid as React child" crashes
  // when the LLM returns {issue,description,solution} instead of {name,description}.
  const safeStr = (v) => (!v || typeof v === "object") ? "" : String(v);

  /* ─── tiny icons ─── (inline SVGs, currentColor) */
  const Ic = {
    play: (p={}) => <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor" {...p}><path d="M3 2.5 11.5 7 3 11.5z"/></svg>,
    pause: (p={}) => <svg width="14" height="14" viewBox="0 0 14 14" {...p}><rect x="3" y="2.5" width="3" height="9" fill="currentColor"/><rect x="8" y="2.5" width="3" height="9" fill="currentColor"/></svg>,
    spark: (p={}) => <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M7 1.5v3M7 9.5v3M1.5 7h3M9.5 7h3M2.7 2.7l2 2M9.3 9.3l2 2M11.3 2.7l-2 2M4.7 9.3l-2 2"/></svg>,
    sun: (p={}) => <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" {...p}><circle cx="7" cy="7" r="2.6"/><path d="M7 1v1.6M7 11.4V13M1 7h1.6M11.4 7H13M2.5 2.5l1.2 1.2M10.3 10.3l1.2 1.2M2.5 11.5l1.2-1.2M10.3 3.7l1.2-1.2"/></svg>,
    moon: (p={}) => <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" {...p}><path d="M11.5 8.2A4.7 4.7 0 0 1 5.8 2.5 4.8 4.8 0 1 0 11.5 8.2z"/></svg>,
    plus: (p={}) => <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" {...p}><path d="M7 3v8M3 7h8"/></svg>,
    flask: (p={}) => <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" strokeLinecap="round" {...p}><path d="M5.5 1.5v3.4L2.6 10.4c-.4.7.1 1.6 1 1.6h6.8c.9 0 1.4-.9 1-1.6L8.5 4.9V1.5"/><path d="M5 1.5h4M5 7h4"/></svg>,
    folder: (p={}) => <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" {...p}><path d="M1.5 4v7a1 1 0 0 0 1 1h9a1 1 0 0 0 1-1V5.5a1 1 0 0 0-1-1H7L5.5 3h-3a1 1 0 0 0-1 1z"/></svg>,
    layers: (p={}) => <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" strokeLinecap="round" {...p}><path d="M7 1.5 1.5 4 7 6.5 12.5 4 7 1.5zM1.5 7 7 9.5 12.5 7M1.5 10 7 12.5 12.5 10"/></svg>,
    chip: (p={}) => <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" {...p}><rect x="3" y="3" width="8" height="8" rx="1"/><path d="M5 1v2M9 1v2M5 11v2M9 11v2M1 5h2M1 9h2M11 5h2M11 9h2"/><rect x="5.5" y="5.5" width="3" height="3" fill="currentColor" fillOpacity=".15"/></svg>,
    file: (p={}) => <svg width="12" height="12" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" {...p}><path d="M3 1.5h5L11 4.5V12a.5.5 0 0 1-.5.5h-7A.5.5 0 0 1 3 12V2a.5.5 0 0 1 0-.5z"/><path d="M8 1.5V4.5h3"/></svg>,
    folder_sm: (p={}) => <svg width="12" height="12" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" {...p}><path d="M1.5 4v7a1 1 0 0 0 1 1h9a1 1 0 0 0 1-1V5.5a1 1 0 0 0-1-1H7L5.5 3h-3a1 1 0 0 0-1 1z"/></svg>,
    check: (p={}) => <svg width="12" height="12" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M2.5 7.5 6 11l5.5-8"/></svg>,
    arrow: (p={}) => <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M3 7h8M8 4l3 3-3 3"/></svg>,
    refresh: (p={}) => <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M11.5 6.5a4.5 4.5 0 1 1-1.3-3.2"/><path d="M11.5 1.5v3h-3"/></svg>,
  };
  window.Ic = Ic;

  /* ───────── Intake screen ───────── */
  function IntakeScreen({ onStart }) {
    const D = window.ARIA_DATA;
    const [idea, setIdea] = useState(D.idea);
    const [mode, setMode] = useState("research");
    const [deep, setDeep] = useState(false);
    const [offline, setOffline] = useState(false);
    const [focus, setFocus] = useState(new Set(["reliability"]));
    const [cfg, setCfg] = useState({ max_repos: 10, max_concurrent: 3, enable_web: true, max_loops: 2 });
    const [resumeId, setResumeId] = useState("");
    const focusOptions = ["reliability", "performance", "security", "scalability", "developer-ux"];

    // Dynamic estimate — fetched from backend, debounced 600ms
    const [est, setEst] = useState({ sub_problems: 3, groq: 3, deepseek: 6, nvidia: 4, githubApi: 18, jina: 9, gemini: 3, total: 43, minutes: 2, risk: "low", savings_calls: 0, savings_pct: 0 });
    const estTimer = useRef(null);
    useEffect(() => {
      if (idea.trim().length < 10) return;
      clearTimeout(estTimer.current);
      estTimer.current = setTimeout(async () => {
        try {
          const r = await fetch(`/api/estimate?idea=${encodeURIComponent(idea.trim())}&mode=${mode}`);
          if (r.ok) {
            const d = await r.json();
            setEst({ ...d, githubApi: d.github_api ?? d.githubApi ?? 0 });
          }
        } catch (_) {}
      }, 600);
      return () => clearTimeout(estTimer.current);
    }, [idea, mode, cfg.enable_web]);

    function toggleFocus(k) {
      const n = new Set(focus); n.has(k) ? n.delete(k) : n.add(k); setFocus(n);
    }

    return (
      <div className="page fade-in">
        <div className="page-header">
          <div>
            <h1 className="page-title">New research run</h1>
            <div className="page-sub">
              Describe an idea in plain English. Aria will decompose it, fan researchers across
              GitHub + the web in parallel, and stitch the findings into a build-ready brief.
            </div>
          </div>
          <div className="row">
            <span className="chip mono">v2 · alpha 0.5.1</span>
          </div>
        </div>

        <div className="intake-grid">
          {/* ─── Left: idea + suggestions ─── */}
          <div>
            <div className="idea-card">
              <div className="head">
                <span className="label">idea</span>
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <div className="toggle">
                    <button className={mode === "research" ? "on" : ""} onClick={() => setMode("research")}>research</button>
                    <button className={mode === "build" ? "on" : ""} onClick={() => setMode("build")}>build</button>
                  </div>
                  <div className="toggle">
                    <button className={!offline ? "on" : ""} onClick={() => setOffline(false)}>cloud</button>
                    <button className={offline ? "on" : ""} onClick={() => setOffline(true)}>offline</button>
                  </div>
                </div>
              </div>
              {mode === "build" && (
                <div style={{ padding: "4px 12px 0", fontSize: 11, color: "var(--warn, #f59e0b)" }}>
                  ⚡ Build mode — skips web research, faster + cheaper. Produces scaffold + brief.
                </div>
              )}
              <div className="prompt-guide">
                <span className="pg-label">great prompt =</span>
                <span className="pg-item"><em>raw idea</em> what you want to build</span>
                <span className="pg-dot">·</span>
                <span className="pg-item"><em>ideal outcome</em> what "done" looks like</span>
                <span className="pg-dot">·</span>
                <span className="pg-item"><em>domain / stack</em> language, infra, constraints</span>
                <span className="pg-dot">·</span>
                <span className="pg-item"><em>hard parts</em> auth, rate limits, perf, edge cases</span>
              </div>
              <textarea
                id="idea-input"
                className="idea-textarea"
                value={idea}
                onChange={(e) => setIdea(e.target.value)}
                placeholder="What do you want to build? Be specific about constraints, data, and what 'done' looks like."
                spellCheck={false}
              />
              <div style={{ padding: "6px 12px 0", display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: 11, color: "var(--muted-2)", whiteSpace: "nowrap" }}>resume id</span>
                <input
                  type="text"
                  value={resumeId}
                  onChange={e => setResumeId(e.target.value)}
                  placeholder="(optional) skip decomposer — paste seeded run id"
                  style={{ flex: 1, fontSize: 11, background: "var(--bg-2)", border: "1px solid var(--border)", borderRadius: 4, padding: "3px 8px", color: "var(--fg)", fontFamily: "monospace" }}
                />
              </div>
              <div className="idea-footer">
                <div className="idea-flags">
                  <button className={`chip ${deep ? "on" : ""}`} onClick={() => setDeep(!deep)}>
                    --deep · qwen 7b
                  </button>
                  {focusOptions.map(f => (
                    <button key={f} className={`chip ${focus.has(f) ? "on" : ""}`} onClick={() => toggleFocus(f)}>
                      {f}
                    </button>
                  ))}
                </div>
                <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 4 }}>
                  {idea.trim().length < 10 && (
                    <span style={{ fontSize: 11, color: "var(--muted-2)" }}>
                      {10 - idea.trim().length} more chars needed
                    </span>
                  )}
                  <button className="btn accent lg" disabled={idea.trim().length < 10}
                          onClick={() => onStart(idea, { ...cfg, mode, resume_id: resumeId.trim() })}>
                    <Ic.play /> {mode === "build" ? "Start build" : "Start research"}
                    <span className="kbd">⌘ ↵</span>
                  </button>
                </div>
              </div>
            </div>

            <div className="suggestions">
              {D.suggestions.map(s => (
                <button key={s.text} className="suggestion" onClick={() => setIdea(s.text)}>
                  <span className="lbl">{s.lbl}</span>{s.text}
                </button>
              ))}
            </div>

            {/* Core problems preview — shows after intake agent runs */}
            {D.ideal_outcome ? (
              <div className="panel" style={{ marginTop: 26 }}>
                <div className="panel-head">
                  <h3>Intake analysis</h3>
                  <span className="meta">agent · completed</span>
                </div>
                <div className="panel-pad" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
                  <div>
                    <div className="page-sub" style={{ marginBottom: 8, fontSize: 11, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                      ideal outcome
                    </div>
                    <div style={{ fontSize: 13, color: "var(--ink-2)", lineHeight: 1.55 }}>
                      {D.ideal_outcome}
                    </div>
                  </div>
                  <div>
                    <div className="page-sub" style={{ marginBottom: 8, fontSize: 11, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                      core problems · {D.core_problems.length}
                    </div>
                    <ul style={{ margin: 0, paddingLeft: 16, fontSize: 12.5, color: "var(--ink-2)", lineHeight: 1.6 }}>
                      {D.core_problems.slice(0, 4).map((c, i) => <li key={i}>{c}</li>)}
                    </ul>
                  </div>
                </div>
                <div className="panel-pad" style={{ display: "flex", gap: 8, paddingTop: 0, flexWrap: "wrap" }}>
                  <span className="chip mono">domain · {D.domain.join(" + ")}</span>
                  <span className="chip mono">lang · {D.primary_language}</span>
                  <span className="chip mono">complexity · {D.complexity}</span>
                </div>
              </div>
            ) : (
              <div className="panel" style={{ marginTop: 26, opacity: 0.5 }}>
                <div className="panel-pad" style={{ textAlign: "center", padding: "20px 0" }}>
                  <div className="page-sub">Submit an idea and the intake agent will analyze it here</div>
                </div>
              </div>
            )}
          </div>

          {/* ─── Right: dry-run + providers ─── */}
          <aside className="dryrun">
            <div className="panel panel-pad">
              <h4>Dry-run estimate</h4>
              <div className="estimate-grid">
                <div className="est">
                  <div className="num">{est.sub_problems ?? est.subs ?? "—"}</div>
                  <div className="lbl">sub-problems</div>
                </div>
                <div className="est">
                  <div className="num">{est.total ?? "—"}</div>
                  <div className="lbl">api calls</div>
                </div>
                <div className="est">
                  <div className="num">~{est.minutes ?? "—"}m</div>
                  <div className="lbl">runtime</div>
                </div>
                <div className="est">
                  <div className="num" style={{ textTransform: "uppercase", fontSize: 14, paddingTop: 6 }}>{est.risk ?? "—"}</div>
                  <div className="lbl">rate-limit risk</div>
                </div>
              </div>
              {mode === "build" && est.savings_pct > 0 && (
                <div style={{ marginTop: 10, padding: "6px 10px", background: "var(--bg-2)", borderRadius: 6, fontSize: 11, color: "var(--ok)" }}>
                  ⚡ Build mode saves ~{est.savings_calls} calls ({est.savings_pct}% fewer) vs research
                </div>
              )}
              <div className={`risk-bar ${est.risk}`}><div /><div /><div /></div>

              <div className="divider" style={{ margin: "14px -16px 12px" }} />
              <h4>Breakdown</h4>
              <div className="row" style={{ display: "block" }}>
                {[
                  ["groq", est.groq, "intake · decompose · judge"],
                  ["deepseek", est.deepseek, "deep dives"],
                  ["nvidia", est.nvidia, "web research · synthesis"],
                  ["gemini", est.gemini, "large files"],
                  ["github api", est.githubApi ?? est.github_api, "search + fetch"],
                  ["jina reader", est.jina, "web pages"],
                ].map(([k, v, note]) => (
                  <div className="row" key={k} style={{ justifyContent: "space-between", padding: "5px 0", fontSize: 12 }}>
                    <span style={{ color: "var(--muted)" }}>{k} <span style={{ color: "var(--muted-2)", marginLeft: 4 }}>· {note}</span></span>
                    <span className="mono" style={{ color: "var(--ink)" }}>{v}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="panel">
              <div className="panel-head">
                <h3>Providers</h3>
                <span className="meta">{D.providers.filter(p => p.ui_status === "ok" || p.status === "ok").length} ready</span>
              </div>
              <div className="panel-pad" style={{ paddingTop: 6 }}>
                <div className="provider-list">
                  {D.providers.map(p => {
                    const dotClass = p.ui_color === "ok" ? "ok"
                                   : p.ui_color === "err" ? "err"
                                   : p.ui_color === "warn" ? "warn"
                                   : p.status;
                    const errHint = p.last_error ? p.last_error.msg : null;
                    return (
                      <div className="provider-row" key={p.name} title={errHint || ""}>
                        <div className={`status-dot ${dotClass}`} />
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div className="name">{p.name}</div>
                          {errHint
                            ? <div className="model" style={{ color: dotClass === "err" ? "var(--err)" : "var(--warn, #f59e0b)", fontSize: 10 }}>{p.status_text}</div>
                            : <div className="model">{p.model}</div>
                          }
                        </div>
                        <div className="rpm" style={{ fontSize: 10 }}>{p.keys > 0 ? `${p.keys}×` : "—"}</div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            <div className="panel panel-pad">
              <h4>Research settings</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 8 }}>
                <div className="cfg-row">
                  <span className="cfg-label">max repos / sub-problem</span>
                  <div className="cfg-seg">
                    {[5, 10, 15, 20].map(v => (
                      <button key={v} className={cfg.max_repos === v ? "on" : ""} onClick={() => setCfg(c => ({ ...c, max_repos: v }))}>{v}</button>
                    ))}
                  </div>
                </div>
                <div className="cfg-row">
                  <span className="cfg-label">concurrent agents</span>
                  <div className="cfg-seg">
                    {[1, 2, 3, 5].map(v => (
                      <button key={v} className={cfg.max_concurrent === v ? "on" : ""} onClick={() => setCfg(c => ({ ...c, max_concurrent: v }))}>{v}</button>
                    ))}
                  </div>
                </div>
                <div className="cfg-row">
                  <span className="cfg-label">web research</span>
                  <div className="cfg-seg">
                    <button className={cfg.enable_web ? "on" : ""} onClick={() => setCfg(c => ({ ...c, enable_web: true }))}>on</button>
                    <button className={!cfg.enable_web ? "on" : ""} onClick={() => setCfg(c => ({ ...c, enable_web: false }))}>off</button>
                  </div>
                </div>
                <div className="cfg-row">
                  <span className="cfg-label">research loops</span>
                  <div className="cfg-seg">
                    {[0, 1, 2, 3].map(v => (
                      <button key={v} className={cfg.max_loops === v ? "on" : ""} onClick={() => setCfg(c => ({ ...c, max_loops: v }))}>{v}</button>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            <div className="panel panel-pad" style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <h4>Hardware</h4>
              {(() => {
                const hw = D.hardware || {};
                const loaded = hw.total_ram_gb > 0;
                const rowStyle = { justifyContent: "space-between", fontSize: 12 };
                return (<>
                  <div className="row" style={rowStyle}>
                    <span style={{ color: "var(--muted)" }}>total ram</span>
                    <span className="mono">{loaded ? `${hw.total_ram_gb} GB` : "—"}</span>
                  </div>
                  <div className="row" style={rowStyle}>
                    <span style={{ color: "var(--muted)" }}>headroom · qwen 3b</span>
                    <span className="mono" style={{ color: hw.can_run_qwen3b ? "var(--ok)" : "var(--err)" }}>
                      {loaded ? `${hw.headroom_qwen3b_gb} GB ${hw.can_run_qwen3b ? "✓" : "✗"}` : "—"}
                    </span>
                  </div>
                  <div className="row" style={rowStyle}>
                    <span style={{ color: "var(--muted)" }}>headroom · qwen 7b</span>
                    <span className="mono" style={{ color: hw.can_run_qwen7b ? "var(--ok)" : "var(--warn)" }}>
                      {deep && loaded ? `${hw.headroom_qwen7b_gb} GB ${hw.can_run_qwen7b ? "✓" : "⚠"}` : "—"}
                    </span>
                  </div>
                  <div className="row" style={rowStyle}>
                    <span style={{ color: "var(--muted)" }}>max concurrent</span>
                    <span className="mono">{hw.max_concurrent_agents || 3} agents</span>
                  </div>
                  <div className="row" style={rowStyle}>
                    <span style={{ color: "var(--muted)" }}>ollama</span>
                    <span className="mono" style={{ color: hw.ollama_running ? "var(--ok)" : "var(--muted-2)" }}>
                      {hw.ollama_running
                        ? `${(hw.ollama_models || []).length} model${(hw.ollama_models || []).length !== 1 ? "s" : ""} ✓`
                        : "not running"}
                    </span>
                  </div>
                  {hw.ollama_running && (hw.ollama_models || []).map(m => (
                    <div key={m} style={{ paddingLeft: 12, fontSize: 11, color: "var(--muted)" }} className="mono">{m}</div>
                  ))}
                </>);
              })()}
            </div>
          </aside>
        </div>
      </div>
    );
  }
  window.IntakeScreen = IntakeScreen;

  /* ───────── Pipeline screen (live run) ───────── */
  function PipelineScreen({ runState, simRef, onView }) {
    const D = window.ARIA_DATA;
    const { agents, sps, logs, phase, paused, elapsed, tokens } = runState;
    const currentAgent = D.current_agent || "";
    const currentProvider = D.current_provider || "";
    const agentTimings = D.agent_timings || {};

    // phase labels
    const PHASES = [
      ["intake", "Intake"],
      ["decomposer", "Decomposer"],
      ["github_research", "Github"],
      ["web_research", "Web"],
      ["pattern_extractor", "Pattern"],
      ["synthesizer", "Synth"],
      ["quality_judge", "Judge"],
      ["knowledge_package", "Package"],
      ["done", "Done"],
    ];
    const phaseIdx = PHASES.findIndex(p => p[0] === phase);

    return (
      <div className="page fade-in" style={{ maxWidth: 1400 }}>
        <div className="page-header">
          <div>
            <h1 className="page-title">{D.idea}</h1>
            <div className="page-sub mono" style={{ fontSize: 11 }}>
              {D.short_id} · started {D.started_at}
            </div>
          </div>
          <div className="row">
            <div className="sep" />
            <span className="chip mono">elapsed · {Math.floor(elapsed/60)}m {String(Math.floor(elapsed%60)).padStart(2,"0")}s</span>
          </div>
        </div>

        <div className="pipeline">
          <div>
            {/* Swarm */}
            <div className="swarm-panel">
              <div className="head">
                <div>
                  <div className="title">Agent swarm</div>
                  <div className="sub mono">7 agents · {sps.length} parallel researchers</div>
                </div>
                <div className="row">
                  <span className="chip mono">{phase}</span>
                </div>
              </div>
              <div className="swarm-stage">
                <window.AgentSwarm
                  agents={agents}
                  sps={sps}
                  idea={D.idea}
                  subtitle="intake → decompose → research → synthesize → ship"
                />
              </div>
              <div className="phase-timeline">
                {PHASES.slice(0, 8).map(([k, label], i) => {
                  const done = i < phaseIdx || phase === "done";
                  const active = i === phaseIdx && phase !== "done";
                  const fill = done ? 100 : (active ? 60 : 0);
                  return (
                    <div className={`phase-cell ${done ? "done" : active ? "active" : ""}`} key={k}>
                      <div className="nm">{String(i + 1).padStart(2, "0")} · {label}</div>
                      <div className="bar"><div className="fill" style={{ width: `${fill}%` }} /></div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Sub-problem cards under the swarm */}
            <div style={{ marginTop: 16, marginBottom: 8 }}>
              <div className="row" style={{ marginBottom: 8 }}>
                <h3 style={{ margin: 0, fontSize: 13 }}>Sub-problems</h3>
                <span className="mono" style={{ color: "var(--muted)", fontSize: 11 }}>· {D.sub_problems.length} · parallel · max 3 concurrent</span>
              </div>
              <div className="sp-cards">
                {D.sub_problems.map((sp, i) => {
                  const st = sps[i] || { status: "idle" };
                  const pct = st.status === "done" ? 100 : st.status === "active" ? 55 : 0;
                  return (
                    <div className={`sp-card ${st.status}`} key={sp.id}>
                      <div className="row" style={{ justifyContent: "space-between" }}>
                        <span className="id mono">{sp.id}</span>
                        <span className="id mono" style={{ color: st.status === "done" ? "var(--ok)" : st.status === "active" ? "var(--accent)" : "var(--muted-2)" }}>
                          {st.status === "done" ? "✓ done" : st.status === "active" ? "● running" : "○ queued"}
                        </span>
                      </div>
                      <div className="ttl">{sp.title}</div>
                      <div className="stats">
                        <span>gh · {sp.repos_found || 0}</span>
                        <span>web · {sp.pages_read || 0}</span>
                        <span>q · {(sp.github_queries || []).length + (sp.web_queries || []).length}</span>
                      </div>
                      <div className="progress"><div style={{ width: `${pct}%` }} /></div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Right rail: logs + kpis */}
          <div className="logstream">
            <div className="kpi-row">
              <div className="kpi">
                <span className="lbl">llm calls</span>
                <span className="val">{tokens.toLocaleString()}</span>
                <span className="delta">{currentProvider ? `via ${currentProvider}` : "—"}</span>
              </div>
              <div className="kpi">
                <span className="lbl">active agent</span>
                <span className="val" style={{ fontSize: 12, fontWeight: 600 }}>{currentAgent || phase || "—"}</span>
                <span className="delta">{elapsed > 0 ? `${Math.floor(elapsed/60)}m ${String(Math.floor(elapsed%60)).padStart(2,"0")}s` : "—"}</span>
              </div>
              <div className="kpi">
                <span className="lbl">cost</span>
                <span className="val">$0.00</span>
                <span className="delta">free tier</span>
              </div>
            </div>
            {Object.keys(agentTimings).length > 0 && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: "4px 12px", padding: "6px 0 2px", fontSize: 10, color: "var(--muted)" }}>
                {Object.entries(agentTimings).map(([k, v]) => (
                  <span key={k} className="mono">{k} · {v}s</span>
                ))}
              </div>
            )}

            <div className="panel">
              <div className="panel-head">
                <h3>Live feed</h3>
                <span className="meta mono">stream · ws</span>
              </div>
              <div className="log-feed">
                {logs.length === 0 && (
                  <div style={{ color: "var(--muted-2)" }}>waiting for first agent…</div>
                )}
                {logs.slice(-22).map((l, i) => (
                  <div className={`log-line ${l.kind || ""}`} key={l.id}>
                    <span className="t">{l.t}</span>
                    <span className="src">{l.src}</span>
                    <span>{l.msg}</span>
                  </div>
                ))}
              </div>
            </div>

            {phase === "done" && (
              <div className="panel panel-pad" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <div className="row" style={{ justifyContent: "space-between" }}>
                  <span className="mono" style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                    quality judge
                  </span>
                  <span className={`verdict ${D.quality.verdict === "RE_RESEARCH" ? "err" : D.quality.verdict === "NEEDS_GAPS_FILLED" ? "warn" : ""}`}>
                    <Ic.check /> {D.quality.verdict || "SHIP"}
                  </span>
                </div>
                <div className="row" style={{ gap: 14, marginTop: 2 }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 28, fontWeight: 600, letterSpacing: "-0.02em", fontFamily: "var(--mono)" }}>
                      {D.quality.overall_score.toFixed(1)} <span style={{ color: "var(--muted)", fontSize: 14 }}>/ 10</span>
                    </div>
                    <div style={{ fontSize: 11, color: "var(--muted)" }}>overall</div>
                  </div>
                  <div style={{ flex: 1 }}>
                    <div className="mono" style={{ fontSize: 12 }}>cov · {(D.quality.coverage*100).toFixed(0)}%</div>
                    <div className="mono" style={{ fontSize: 12 }}>nov · {(D.quality.novelty*100).toFixed(0)}%</div>
                    <div className="mono" style={{ fontSize: 12 }}>act · {(D.quality.actionability*100).toFixed(0)}%</div>
                  </div>
                </div>
                <button className="btn accent" onClick={onView}>
                  <Ic.folder /> Open knowledge package
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }
  window.PipelineScreen = PipelineScreen;

  /* ───────── Package browser ───────── */

  // syntax-highlight tiny JSON
  function highlightJson(obj) {
    const s = JSON.stringify(obj, null, 2);
    return s
      .replace(/("[^"]+"):/g, '<span class="k">$1</span>:')
      .replace(/: ("[^"]*")/g, ': <span class="s">$1</span>')
      .replace(/: (\d+(\.\d+)?)/g, ': <span class="n">$1</span>')
      .replace(/: (true|false)/g, ': <span class="bool">$1</span>');
  }

  // tiny markdown → html for the brief
  function renderMd(md) {
    let out = md;
    // code blocks
    out = out.replace(/```([\s\S]*?)```/g, (_, code) => `<pre>${escapeHtml(code.trim())}</pre>`);
    // headings
    out = out.replace(/^### (.*)$/gm, "<h3>$1</h3>")
             .replace(/^## (.*)$/gm, "<h2>$1</h2>")
             .replace(/^# (.*)$/gm, "<h1>$1</h1>");
    // inline code
    out = out.replace(/`([^`]+)`/g, '<span class="inline-code">$1</span>');
    // bold
    out = out.replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>");
    // tables (very basic)
    out = out.replace(/^(\|.*\|)$/gm, (line) => {
      const cells = line.slice(1, -1).split("|").map(c => c.trim());
      return `<tr>${cells.map(c => `<td style="padding:6px 10px;border-bottom:1px solid var(--line);font-size:12px;">${c}</td>`).join("")}</tr>`;
    });
    out = out.replace(/(<tr>.*<\/tr>(\n<tr>.*<\/tr>)+)/gs, '<table style="border-collapse:collapse;width:100%;margin:12px 0;border:1px solid var(--line);border-radius:6px;overflow:hidden;">$1</table>');
    // lists
    out = out.replace(/^(- .*(\n- .*)+)/gm, (block) => {
      const items = block.split("\n").map(l => `<li>${l.replace(/^- /, "")}</li>`).join("");
      return `<ul>${items}</ul>`;
    });
    // paragraphs
    out = out.split(/\n{2,}/).map(p => {
      if (p.startsWith("<h") || p.startsWith("<pre") || p.startsWith("<ul") || p.startsWith("<table")) return p;
      return `<p>${p.replace(/\n/g, "<br>")}</p>`;
    }).join("\n");
    return out;
  }
  function escapeHtml(s) { return s.replace(/[&<>]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;"}[c])); }

  function PackageScreen({ onNewRun, onRerun }) {
    const D = window.ARIA_DATA;
    const [tab, setTab] = useState("summary");
    // Pick the first available file as default instead of hardcoding a filename.
    const [selectedFile, setSelectedFile] = useState(() => (D.package_files[0] || {}).name || "");
    const [fileContent, setFileContent] = useState(null);
    const [fileLoading, setFileLoading] = useState(false);
    const [fileError, setFileError] = useState(null);

    useEffect(() => {
      if (!selectedFile) return;
      const files = window.ARIA_DATA.package_files;  // read live — not captured closure
      const f = files.find(x => x.name === selectedFile);
      if (!f) {
        // Auto-advance to first available file if selection is stale.
        const first = files[0];
        if (first) { setSelectedFile(first.name); }
        else { setFileContent(null); }
        return;
      }
      setFileLoading(true);
      setFileContent(null);
      setFileError(null);
      fetch(`/api/file?name=${encodeURIComponent(f.name)}&folder=${encodeURIComponent(f.folder || "")}`)
        .then(r => r.json())
        .then(d => {
          if (d.error) { setFileError(d.error); setFileContent(null); }
          else { setFileContent(d.content ?? null); }
          setFileLoading(false);
        })
        .catch(err => { setFileError(String(err)); setFileContent(null); setFileLoading(false); });
    }, [selectedFile]);

    const tabs = [
      { id: "summary",  label: "Summary",       count: null },
      { id: "brief",    label: "Brief",          count: 1 },
      { id: "sub",      label: "Sub-problems",   count: D.sub_problems.length },
      { id: "patterns", label: "Patterns",       count: (D.patterns.libraries_to_use || []).length },
      { id: "repos",    label: "Repos",          count: D.extracted_repos.length },
      { id: "raw",      label: "Raw artifacts",  count: D.package_files.length },
    ];

    const packageFiles = D.package_files || [];
    const folders = useMemo(() => {
      const m = {};
      for (const f of window.ARIA_DATA.package_files || []) {
        const key = f.folder || "root";
        (m[key] = m[key] || []).push(f);
      }
      return m;
    }, [packageFiles.length, selectedFile]);

    return (
      <div className="page fade-in" style={{ maxWidth: 1400 }}>
        <div className="page-header">
          <div>
            <h1 className="page-title">Knowledge package</h1>
            <div className="page-sub">
              Build-ready bundle for your coding agent. Brief + raw artifacts + extracted source from the top repos.
            </div>
          </div>
          <div className="row">
            <span className={`verdict ${D.quality.verdict === "RE_RESEARCH" ? "err" : D.quality.verdict === "NEEDS_GAPS_FILLED" ? "warn" : ""}`}>
              <Ic.check /> {D.quality.verdict || "SHIP"} · {D.quality.overall_score.toFixed(1)}/10
            </span>
            <div className="sep" />
            <button className="btn" onClick={onRerun} disabled={!window.ARIA_DATA.idea}>
              <Ic.refresh /> Re-research gaps
            </button>
            <button className="btn primary"><Ic.arrow /> Hand off to Claude Code</button>
          </div>
        </div>

        <div className="tab-row">
          {tabs.map(t => (
            <div key={t.id} className={`tab ${tab === t.id ? "on" : ""}`} onClick={() => setTab(t.id)}>
              {t.label} {t.count != null && <span className="cnt">{t.count}</span>}
            </div>
          ))}
        </div>

        {tab === "summary" && (() => {
          const score = D.quality.overall_score || 0;
          const verdict = D.quality.verdict || "";
          const topRepos = D.extracted_repos.slice(0, 5);
          const topPatterns = (D.patterns.architectural_patterns || []).slice(0, 3);
          const topLibs = (D.patterns.libraries_to_use || []).slice(0, 5);
          const topGotchas = (D.patterns.gotchas || []).slice(0, 3);
          const lang = D.primary_language;
          const pkgBase = lang === "python" ? "https://pypi.org/project/" : lang === "go" ? "https://pkg.go.dev/" : "https://www.npmjs.com/package/";

          return (
            <div style={{ marginTop: 16, display: "grid", gap: 16 }}>

              {/* ── Quality strip ── */}
              <div className="panel panel-pad summary-quality-strip">
                <div className="summary-score-circle">
                  <span className="summary-score-num">{score.toFixed(1)}</span>
                  <span className="summary-score-denom">/10</span>
                </div>
                <div style={{ flex: 1 }}>
                  <div className="row" style={{ gap: 10, marginBottom: 10, flexWrap: "wrap" }}>
                    {verdict && <span className="verdict"><Ic.check /> {verdict}</span>}
                    {D.domain.map(d => <span key={d} className="chip mono">{d}</span>)}
                    {lang && <span className="chip mono">lang · {lang}</span>}
                    {D.complexity && <span className="chip mono">complexity · {D.complexity}</span>}
                    {D.sub_problems.length > 0 && <span className="chip mono">{D.sub_problems.length} sub-problems</span>}
                  </div>
                  {D.quality.coverage > 0 && (
                    <div className="summary-score-bars">
                      {[["coverage", D.quality.coverage], ["novelty", D.quality.novelty], ["actionability", D.quality.actionability]].map(([k, v]) => (
                        <div key={k} className="summary-bar-row">
                          <span className="summary-bar-label">{k}</span>
                          <div className="summary-bar-track">
                            <div className="summary-bar-fill" style={{ width: `${Math.round(v * 100)}%` }} />
                          </div>
                          <span className="summary-bar-pct">{Math.round(v * 100)}%</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* ── Ideal outcome + core problems + top repos ── */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                <div className="panel panel-pad">
                  <div className="panel-section-label">ideal outcome</div>
                  <div style={{ fontSize: 13.5, color: "var(--ink-2)", lineHeight: 1.6, marginBottom: 16 }}>
                    {D.ideal_outcome || "—"}
                  </div>
                  {D.core_problems.length > 0 && <>
                    <div className="panel-section-label">core problems solved</div>
                    <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "grid", gap: 6 }}>
                      {D.core_problems.map((p, i) => (
                        <li key={i} style={{ display: "flex", gap: 8, fontSize: 12.5, color: "var(--ink-2)", lineHeight: 1.5 }}>
                          <span style={{ color: "var(--ok)", marginTop: 1 }}>✓</span>{p}
                        </li>
                      ))}
                    </ul>
                  </>}
                </div>

                <div className="panel panel-pad">
                  <div className="panel-section-label">top repos found · {topRepos.length}</div>
                  <div style={{ display: "grid", gap: 10 }}>
                    {topRepos.map(r => (
                      <a key={r.full_name} href={`https://github.com/${r.full_name}`} target="_blank" rel="noreferrer"
                         className="summary-repo-card">
                        <div className="row" style={{ justifyContent: "space-between" }}>
                          <span className="mono" style={{ fontSize: 12.5, fontWeight: 600, color: "var(--accent)" }}>{r.full_name}</span>
                          <span className="mono" style={{ fontSize: 11, color: "var(--muted)" }}>★ {(r.stars || 0).toLocaleString()}</span>
                        </div>
                        <div style={{ fontSize: 11.5, color: "var(--ink-2)", marginTop: 3, lineHeight: 1.4 }}>{r.why}</div>
                        <div style={{ marginTop: 5 }}><span className="chip mono">{r.language}</span></div>
                      </a>
                    ))}
                    {topRepos.length === 0 && <div style={{ color: "var(--muted)", fontSize: 12 }}>Run a pipeline to see repos</div>}
                  </div>
                </div>
              </div>

              {/* ── Key findings ── */}
              {(topPatterns.length > 0 || topLibs.length > 0 || topGotchas.length > 0) && (
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 }}>
                  {topPatterns.length > 0 && (
                    <div className="panel panel-pad">
                      <div className="panel-section-label">architectural patterns</div>
                      <div style={{ display: "grid", gap: 8 }}>
                        {topPatterns.map((p, i) => (
                          <div key={i} style={{ fontSize: 12.5, lineHeight: 1.5 }}>
                            <div style={{ fontWeight: 600, color: "var(--ink)", marginBottom: 2 }}>
                              {typeof p === "string" ? p : safeStr(p.name) || safeStr(p.pattern) || safeStr(p.title)}
                            </div>
                            {p.description && <div style={{ color: "var(--ink-2)", fontSize: 12 }}>{p.description}</div>}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {topLibs.length > 0 && (
                    <div className="panel panel-pad">
                      <div className="panel-section-label">key libraries</div>
                      <div style={{ display: "grid", gap: 7 }}>
                        {topLibs.map((l, i) => (
                          <div key={i}>
                            <a href={`${pkgBase}${l.library}`} target="_blank" rel="noreferrer"
                               className="mono" style={{ fontSize: 12.5, fontWeight: 500, color: "var(--accent)", textDecoration: "none" }}>
                              {l.library}
                            </a>
                            {l.version && <span className="mono" style={{ fontSize: 11, color: "var(--muted-2)", marginLeft: 4 }}>{l.version}</span>}
                            {l.reason && <div style={{ fontSize: 11.5, color: "var(--ink-2)", marginTop: 1 }}>{l.reason}</div>}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {topGotchas.length > 0 && (
                    <div className="panel panel-pad">
                      <div className="panel-section-label">gotchas to watch</div>
                      <div style={{ display: "grid", gap: 8 }}>
                        {topGotchas.map((g, i) => (
                          <div key={i} style={{ fontSize: 12.5, lineHeight: 1.5 }}>
                            <div style={{ fontWeight: 600, color: "var(--ink)", marginBottom: 2 }}>
                              ⚠ {typeof g === "string" ? g : safeStr(g.name) || safeStr(g.issue) || safeStr(g.title)}
                            </div>
                            {(g.description || g.solution) && (
                              <div style={{ color: "var(--ink-2)", fontSize: 12 }}>{g.description || g.solution}</div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })()}

        {tab === "brief" && (
          <div className="pkg" style={{ marginTop: 16 }}>
            <div className="pkg-tree">
              {Object.entries(folders).map(([folder, files]) => (
                <div key={folder} style={{ marginBottom: 10 }}>
                  <div className="pkg-folder">
                    <Ic.folder_sm /> {folder === "root" ? "/" : folder + "/"}
                  </div>
                  {files.map(f => (
                    <div key={f.name}
                         className={`pkg-file ${selectedFile === f.name ? "active" : ""}`}
                         onClick={() => setSelectedFile(f.name)}>
                      {f.kind === "dir" ? <Ic.folder_sm /> : <Ic.file />}
                      <span>{f.name}</span>
                      <span className="ext">{f.kind === "dir" ? "—" : (f.size > 1000 ? Math.round(f.size/1024)+"k" : f.size+"b")}</span>
                    </div>
                  ))}
                </div>
              ))}
            </div>
            <div className="pkg-viewer">
              <div className="vhead">
                <div className="breadcrumb">
                  <span>knowledge_package</span> / <b>{selectedFile}</b>
                </div>
                <span className="meta mono" style={{ fontSize: 11, color: "var(--muted)" }}>
                  {(() => {
                    const f = D.package_files.find(x => x.name === selectedFile);
                    if (!f) return "";
                    return `${f.kind} · ${f.size > 1000 ? Math.round(f.size/1024)+" KB" : f.size+" B"}`;
                  })()}
                </span>
              </div>
              <div className="vbody">
                {fileLoading && <div style={{ padding: 24, color: "var(--muted)", fontSize: 13 }}>Loading…</div>}
                {!fileLoading && fileContent !== null && selectedFile.endsWith(".md") && (
                  <div className="brief" dangerouslySetInnerHTML={{ __html: renderMd(fileContent) }} />
                )}
                {!fileLoading && fileContent !== null && selectedFile.endsWith(".json") && (
                  <pre className="json-view" dangerouslySetInnerHTML={{
                    __html: highlightJson((() => { try { return JSON.parse(fileContent); } catch (_) { return fileContent; } })())
                  }} />
                )}
                {!fileLoading && fileContent !== null && !selectedFile.endsWith(".md") && !selectedFile.endsWith(".json") && (
                  <pre className="json-view" style={{ whiteSpace: "pre-wrap" }}>{fileContent}</pre>
                )}
                {!fileLoading && fileError && (
                  <div style={{ padding: 24, fontFamily: "var(--mono)", fontSize: 12 }}>
                    <div style={{ color: "var(--err)", marginBottom: 8 }}>Failed to load file</div>
                    <div style={{ color: "var(--muted)" }}>{fileError}</div>
                  </div>
                )}
                {!fileLoading && !fileError && fileContent === null && (
                  <div style={{ padding: 24, color: "var(--muted)", fontSize: 13 }}>Select a file to view its contents.</div>
                )}
              </div>
            </div>
          </div>
        )}

        {tab === "sub" && (
          <div style={{ marginTop: 16, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
            {D.sub_problems.map(sp => (
              <div key={sp.id} className="panel panel-pad">
                <div className="row" style={{ justifyContent: "space-between", marginBottom: 6 }}>
                  <span className="mono" style={{ fontSize: 11, color: "var(--accent)" }}>{sp.id}</span>
                  <span className="mono" style={{ fontSize: 11, color: "var(--muted)" }}>
                    gh · {sp.repos_found} · web · {sp.pages_read}
                  </span>
                </div>
                {sp.core_problem_ref && sp.core_problem_ref !== "supplementary" && (
                  <div style={{ fontSize: 10.5, color: "var(--muted)", marginBottom: 6, fontFamily: "var(--mono)" }}>
                    maps to → <span style={{ color: "var(--ink-2)" }}>{sp.core_problem_ref}</span>
                  </div>
                )}
                <div style={{ fontSize: 15, fontWeight: 600, letterSpacing: "-0.005em", marginBottom: 6 }}>{sp.title}</div>
                <div style={{ fontSize: 12.5, color: "var(--ink-2)", lineHeight: 1.55 }}>{sp.description}</div>
                <div style={{ borderTop: "1px dashed var(--line)", marginTop: 12, paddingTop: 10 }}>
                  <div style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--muted)", marginBottom: 6 }}>
                    why it's critical
                  </div>
                  <div style={{ fontSize: 12, color: "var(--ink-2)" }}>{sp.why_critical}</div>
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 10 }}>
                  {(sp.github_queries || []).map(q => (
                    <a key={q} href={`https://github.com/search?q=${encodeURIComponent(q)}&type=repositories`}
                       target="_blank" rel="noreferrer"
                       className="chip mono" style={{ textDecoration: "none", cursor: "pointer" }}>
                      gh: {q}
                    </a>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {tab === "patterns" && (() => {
          const lang = D.primary_language;
          const pkgBase = lang === "python" ? "https://pypi.org/project/" : lang === "go" ? "https://pkg.go.dev/" : "https://www.npmjs.com/package/";
          return (
            <div style={{ marginTop: 16, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
              <PatternBlock title="Architectural patterns" items={D.patterns.architectural_patterns || []} keyA="name" keyB="description" />
              <PatternBlock title="Libraries · pick" items={D.patterns.libraries_to_use || []}
                renderRow={(l) => (
                  <div className="row" style={{ justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid var(--line)" }}>
                    <div>
                      <div className="mono" style={{ fontSize: 12.5, fontWeight: 500 }}>
                        <a href={`${pkgBase}${l.library}`} target="_blank" rel="noreferrer"
                           style={{ color: "var(--accent)", textDecoration: "none" }}>{l.library}</a>
                        {l.version && <span style={{ color: "var(--muted-2)", fontWeight: 400, marginLeft: 4 }}>{l.version}</span>}
                      </div>
                      <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 2 }}>{l.reason}</div>
                    </div>
                    {l.source_repo && <span className="chip mono" style={{ marginLeft: 12 }}>{l.source_repo}</span>}
                  </div>
                )} />
              <PatternBlock title="⚠ Gotchas" items={D.patterns.gotchas || []} keyA="name" keyB="description" />
              <PatternBlock title="✗ Anti-patterns to avoid" items={D.patterns.anti_patterns || []} keyA="name" keyB="description" tone="err" />
              <PatternBlock title="Performance" items={D.patterns.performance || []} keyA="name" keyB="description" />
              <PatternBlock title="Security" items={D.patterns.security || []} keyA="name" keyB="description" />
              {(D.patterns.repos_to_fork || []).length > 0 && (
                <PatternBlock title="Repos to fork / reference" items={D.patterns.repos_to_fork}
                  renderRow={(r) => (
                    <div className="row" style={{ justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid var(--line)" }}>
                      <div>
                        <a href={`https://github.com/${safeStr(r.repo) || safeStr(r.name) || safeStr(r.full_name) || ""}`} target="_blank" rel="noreferrer"
                           className="mono" style={{ fontSize: 12.5, fontWeight: 500, color: "var(--accent)", textDecoration: "none" }}>
                          {safeStr(r.repo) || safeStr(r.name) || safeStr(r.full_name) || "—"}
                        </a>
                        {r.reason && <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 2 }}>{r.reason}</div>}
                      </div>
                      {r.stars != null && <span className="mono" style={{ fontSize: 11, color: "var(--muted)" }}>★ {r.stars.toLocaleString()}</span>}
                    </div>
                  )} />
              )}
            </div>
          );
        })()}

        {tab === "repos" && (
          <div style={{ marginTop: 16 }}>
            <div className="panel">
              <div className="panel-head">
                <h3>Extracted source · code/</h3>
                <span className="meta mono">{D.extracted_repos.length} repos</span>
              </div>
              <div className="panel-pad" style={{ paddingBottom: 0 }}>
                <div className="row" style={{ justifyContent: "space-between", padding: "0 0 8px", borderBottom: "1px solid var(--line)" }}>
                  <span className="mono" style={{ fontSize: 10, color: "var(--muted-2)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Repository</span>
                  <div className="row" style={{ gap: 48 }}>
                    {["Lang", "Stars", "Files", ""].map(h => (
                      <span key={h} className="mono" style={{ fontSize: 10, color: "var(--muted-2)", textTransform: "uppercase", letterSpacing: "0.05em", minWidth: h === "" ? 28 : "auto" }}>{h}</span>
                    ))}
                  </div>
                </div>
              </div>
              <div className="panel-pad" style={{ display: "grid", gap: 0 }}>
                {D.extracted_repos.map(r => (
                  <div key={r.full_name} className="row" style={{ justifyContent: "space-between", padding: "10px 0", borderBottom: "1px solid var(--line)" }}>
                    <div>
                      <div className="mono" style={{ fontWeight: 500, fontSize: 13 }}>{r.full_name}</div>
                      {r.description && <div style={{ fontSize: 11.5, color: "var(--muted)", marginTop: 2 }}>{r.description}</div>}
                      <div style={{ fontSize: 12, color: "var(--ink-2)", marginTop: r.description ? 2 : 2 }}>{r.why}</div>
                    </div>
                    <div className="row" style={{ gap: 14 }}>
                      <span className="chip mono">{r.language}</span>
                      <span className="mono" style={{ fontSize: 11, color: "var(--muted)", minWidth: 60, textAlign: "right" }}>★ {(r.stars || 0).toLocaleString()}</span>
                      <span className="mono" style={{ fontSize: 11, color: "var(--muted)", minWidth: 48, textAlign: "right" }}>{r.files} files</span>
                      <button className="btn ghost" onClick={() => window.open(`https://github.com/${r.full_name}`, "_blank")}><Ic.arrow /></button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {tab === "raw" && (
          <div style={{ marginTop: 16 }}>
            <div className="panel">
              <div className="panel-head">
                <h3>Raw artifacts</h3>
                <span className="meta mono">checkpoint per agent · resumable</span>
              </div>
              <div className="panel-pad">
                {D.package_files.map(f => {
                  const fullPath = (f.folder ? f.folder + "/" : "") + f.name;
                  return (
                    <div key={f.name} className="row" style={{ justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid var(--line)" }}>
                      <div className="row" style={{ gap: 10 }}>
                        {f.kind === "dir" ? <Ic.folder_sm /> : <Ic.file />}
                        <span className="mono" style={{ fontSize: 12.5 }}>{fullPath}</span>
                      </div>
                      <div className="row" style={{ gap: 12 }}>
                        <span className="mono" style={{ fontSize: 11, color: "var(--muted)" }}>
                          {f.kind} · {f.size > 1000 ? Math.round(f.size/1024)+" KB" : f.size+" B"}
                        </span>
                        <button className="btn ghost" title="Copy path"
                                onClick={() => navigator.clipboard.writeText(fullPath)}
                                style={{ padding: "2px 6px", fontSize: 10 }}>
                          copy
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }
  window.PackageScreen = PackageScreen;

  function PatternBlock({ title, items, keyA, keyB, tone, renderRow }) {
    return (
      <div className="panel">
        <div className="panel-head">
          <h3>{title}</h3>
          <span className="meta mono">{items.length}</span>
        </div>
        <div className="panel-pad">
          {items.map((it, i) => renderRow ? renderRow(it) : (
            <div key={i} style={{ padding: "8px 0", borderBottom: i === items.length - 1 ? "0" : "1px solid var(--line)" }}>
              <div style={{ fontSize: 12.5, fontWeight: 600, color: tone === "err" ? "var(--err)" : "var(--ink)" }}>
                {safeStr(it[keyA]) || safeStr(it.name) || safeStr(it.issue) || safeStr(it.title) || safeStr(it.pattern)}
              </div>
              <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 2 }}>
                {safeStr(it[keyB]) || safeStr(it.description) || safeStr(it.detail) || safeStr(it.solution)}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }


  /* ───────── Past Runs screen ───────── */
  function PastRunsScreen({ onNewRun, onOpen }) {
    const [runs, setRuns] = useState(window.ARIA_DATA.runs || []);
    const [loading, setLoading] = useState(false);
    const [opening, setOpening] = useState(null);
    const [deleting, setDeleting] = useState(null);
    const Ic = window.Ic;

    const refresh = async () => {
      setLoading(true);
      if (window.ariaFetchRuns) await window.ariaFetchRuns();
      setRuns([...(window.ARIA_DATA.runs || [])]);
      setLoading(false);
    };

    useEffect(() => { setRuns([...(window.ARIA_DATA.runs || [])]); }, []);

    const openRun = async (run_id) => {
      setOpening(run_id);
      if (onOpen) await onOpen(run_id);
      setOpening(null);
    };

    const deleteRun = async (run_id) => {
      setDeleting(run_id);
      try {
        const res = await fetch("/api/delete_run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ run_id }),
        });
        if (res.ok) {
          setRuns(prev => prev.filter(r => r.run_id !== run_id));
          if (window.ARIA_DATA) {
            window.ARIA_DATA.runs = (window.ARIA_DATA.runs || []).filter(r => r.run_id !== run_id);
            window.dispatchEvent(new CustomEvent("aria:runs_updated"));
          }
        }
      } catch (_) {}
      setDeleting(null);
    };

    const clearAll = async () => {
      if (!window.confirm("Delete all past runs? This cannot be undone.")) return;
      setLoading(true);
      try {
        await fetch("/api/clear_runs", { method: "POST" });
        setRuns([]);
        if (window.ARIA_DATA) {
          window.ARIA_DATA.runs = [];
          window.dispatchEvent(new CustomEvent("aria:runs_updated"));
        }
      } catch (_) {}
      setLoading(false);
    };

    const statusColor = s => s === "complete" ? "var(--ok)" : s === "failed" ? "var(--err)" : "var(--warn)";
    const statusLabel = s => s === "complete" ? "complete" : s === "failed" ? "failed" : "partial";

    const completeRuns = runs.filter(r => r.status === "complete");
    const otherRuns = runs.filter(r => r.status !== "complete");

    return (
      <div className="page fade-in">
        <div className="page-header">
          <div>
            <h1 className="page-title">Past runs</h1>
            <div className="page-sub">{runs.length} research pipeline{runs.length !== 1 ? "s" : ""} in the output directory.</div>
          </div>
          <div className="row" style={{ gap: 8 }}>
            {runs.length > 0 && (
              <button className="btn sm" style={{ color: "var(--err)" }} onClick={clearAll} disabled={loading}>
                clear all
              </button>
            )}
            <button className="btn sm" onClick={refresh} disabled={loading}>
              <Ic.refresh /> {loading ? "refreshing…" : "refresh"}
            </button>
            <button className="btn accent sm" onClick={onNewRun}>
              <Ic.plus /> New run
            </button>
          </div>
        </div>

        {runs.length === 0 ? (
          <div className="panel panel-pad" style={{ textAlign: "center", padding: "48px 24px" }}>
            <div style={{ fontSize: 13, color: "var(--muted)" }}>No past runs found in the output directory.</div>
            <button className="btn accent" style={{ marginTop: 16 }} onClick={onNewRun}>
              <Ic.play /> Start your first research run
            </button>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {[...completeRuns, ...otherRuns].map(r => (
              <div key={r.run_id} className="panel panel-pad past-run-row">
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                    <span className="mono" style={{ fontSize: 11, color: "var(--muted-2)" }}>{r.date || r.run_id.slice(0, 15)}</span>
                    <span style={{ fontSize: 11, color: statusColor(r.status), fontWeight: 600 }}>
                      {statusLabel(r.status)}
                    </span>
                    {r.quality_score != null && (
                      <span className="chip mono" style={{ fontSize: 10 }}>★ {r.quality_score}/10</span>
                    )}
                    {r.has_brief && (
                      <span className="chip" style={{ fontSize: 10 }}>brief</span>
                    )}
                  </div>
                  <div style={{ fontSize: 13, color: "var(--ink)", fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {r.idea || r.run_id}
                  </div>
                  <div className="mono" style={{ fontSize: 10, color: "var(--muted-2)", marginTop: 3 }}>{r.run_id}</div>
                </div>
                <div className="past-run-actions">
                  <button className="btn accent sm" onClick={() => openRun(r.run_id)}
                          disabled={opening === r.run_id}>
                    {opening === r.run_id ? "loading…" : <><Ic.arrow /> open</>}
                  </button>
                  <button className="btn-delete" onClick={() => deleteRun(r.run_id)}
                          disabled={deleting === r.run_id} title="Delete run">
                    {deleting === r.run_id ? "…" : "✕"}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }
  window.PastRunsScreen = PastRunsScreen;

  /* ───────── Providers screen ───────── */
  function ProvidersScreen() {
    const D = window.ARIA_DATA;
    const providers = D.providers || [];
    const hw = D.hardware || {};

    const cloudProviders = providers.filter(p => p.name !== "ollama");
    const ready = cloudProviders.filter(p => p.ui_status === "ok" || p.status === "ok").length;
    const degraded = cloudProviders.filter(p => p.ui_color === "warn").length;
    const failed = cloudProviders.filter(p => p.ui_color === "err" || (p.keys === 0 && p.ui_status !== "ok")).length;

    const statusColor = uiColor => {
      if (uiColor === "ok") return "var(--ok)";
      if (uiColor === "warn") return "var(--warn, #f59e0b)";
      if (uiColor === "err") return "var(--err)";
      return "var(--muted-2)";
    };

    const ERROR_ACTIONS = {
      invalid_key: "Regenerate your API key and update .env",
      no_credits: "Add credits on the provider dashboard",
      model_error: "Update the model name in config.py",
      rate_limited: "ARIA will retry automatically — or add more keys",
      circuit_open: "Provider will auto-recover in ~60s",
      degraded: "Intermittent — ARIA is routing around it",
      unconfigured: "Add key to .env to enable this provider",
    };

    const statusBadge = p => {
      const us = p.ui_status;
      const label = p.status_text || p.ui_label || (p.status === "ok" ? "ready" : "—");
      const color = statusColor(p.ui_color || (p.status === "ok" ? "ok" : p.keys === 0 ? "muted" : "err"));
      const icons = {
        ok: "●",
        unconfigured: "○",
        invalid_key: "⚠",
        no_credits: "💸",
        model_error: "⚠",
        rate_limited: "⏳",
        circuit_open: "✕",
        degraded: "⚠",
      };
      const icon = icons[us] || "●";
      const action = ERROR_ACTIONS[us];
      return (
        <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <span style={{ color, fontWeight: 600, fontSize: 11 }}>
            {icon} {label}
          </span>
          {p.last_error && (
            <span style={{ color: "var(--muted-2)", fontSize: 10, maxWidth: 220, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
                  title={p.last_error.msg}>
              {p.last_error.msg}
            </span>
          )}
          {action && us !== "ok" && (
            <span style={{ color: "var(--muted-2)", fontSize: 10, fontStyle: "italic", maxWidth: 220 }}>
              → {action}
            </span>
          )}
          {p.circuit_failures > 0 && (
            <span style={{ color: "var(--muted-2)", fontSize: 10 }}>
              {p.circuit_failures} consecutive fail{p.circuit_failures !== 1 ? "s" : ""}
            </span>
          )}
        </div>
      );
    };

    return (
      <div className="page fade-in">
        <div className="page-header">
          <div>
            <h1 className="page-title">Providers</h1>
            <div className="page-sub">
              Live status — updates on every API call. Errors persist until the provider recovers.
            </div>
          </div>
          <div className="row" style={{ gap: 8 }}>
            <span className="chip mono" style={{ color: "var(--ok)" }}>{ready} ready</span>
            {degraded > 0 && <span className="chip mono" style={{ color: "var(--warn, #f59e0b)" }}>{degraded} degraded</span>}
            {failed > 0 && <span className="chip mono" style={{ color: "var(--err)" }}>{failed} failed</span>}
          </div>
        </div>

        <div className="panel" style={{ marginBottom: 16 }}>
          <div className="panel-head">
            <h3>Cloud providers</h3>
            <span className="meta">{ready}/{cloudProviders.length} active</span>
          </div>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12.5 }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--line)" }}>
                  {["provider","model","keys","rpm","status / last error"].map(h => (
                    <th key={h} style={{ textAlign: "left", padding: "8px 16px", color: "var(--muted)", fontWeight: 500, fontSize: 11, textTransform: "uppercase", letterSpacing: "0.05em" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {cloudProviders.map(p => {
                  const rowBg = p.ui_color === "err" ? "rgba(239,68,68,0.04)"
                              : p.ui_color === "warn" ? "rgba(245,158,11,0.04)"
                              : "transparent";
                  return (
                    <tr key={p.name} style={{ borderBottom: "1px solid var(--line-soft, var(--line))", background: rowBg }}>
                      <td style={{ padding: "10px 16px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          <div className={`status-dot ${p.status}`} />
                          <span style={{ fontWeight: 600 }}>{p.name}</span>
                        </div>
                      </td>
                      <td style={{ padding: "10px 16px", color: "var(--muted)", fontSize: 11 }} className="mono">{p.model}</td>
                      <td style={{ padding: "10px 16px" }} className="mono">{p.keys > 0 ? `${p.keys}×` : "—"}</td>
                      <td style={{ padding: "10px 16px" }} className="mono">{p.rpm > 0 ? `${p.rpm}` : "—"}</td>
                      <td style={{ padding: "10px 16px" }}>{statusBadge(p)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        <div className="panel panel-pad">
          <div className="panel-head" style={{ marginBottom: 12 }}>
            <h3>Local · Ollama</h3>
            <span className="meta" style={{ color: hw.ollama_running ? "var(--ok)" : "var(--muted-2)" }}>
              {hw.ollama_running ? "running" : "not running"}
            </span>
          </div>
          {hw.ollama_running ? (
            <>
              <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 10 }}>
                {(hw.ollama_models || []).length} model{(hw.ollama_models || []).length !== 1 ? "s" : ""} installed
              </div>
              {(hw.ollama_models || []).map(m => (
                <div key={m} className="provider-row" style={{ padding: "8px 0", borderBottom: "1px solid var(--line)" }}>
                  <div className="status-dot ok" />
                  <div>
                    <div className="name mono">{m}</div>
                    <div className="model">{m.includes("7b") || m.includes("7B") ? "~5.5 GB RAM" : "~2.2 GB RAM"}</div>
                  </div>
                  <div className="rpm" style={{ marginLeft: "auto" }}>
                    {(hw.can_run_qwen7b && (m.includes("7b") || m.includes("7B"))) || (!m.includes("7b") && !m.includes("7B") && hw.can_run_qwen3b)
                      ? <span style={{ color: "var(--ok)", fontSize: 11 }}>✓ fits RAM</span>
                      : <span style={{ color: "var(--warn)", fontSize: 11 }}>⚠ tight</span>}
                  </div>
                </div>
              ))}
            </>
          ) : (
            <div style={{ fontSize: 12, color: "var(--muted)", padding: "12px 0" }}>
              Ollama is not running. Start it with <span className="mono" style={{ background: "var(--bg-2)", padding: "1px 5px", borderRadius: 4 }}>ollama serve</span> to use local models.
            </div>
          )}
          {hw.total_ram_gb > 0 && (
            <div style={{ marginTop: 12, paddingTop: 12, borderTop: "1px solid var(--line)", display: "flex", gap: 16, fontSize: 12 }}>
              <div><span style={{ color: "var(--muted)" }}>total ram · </span><span className="mono">{hw.total_ram_gb} GB</span></div>
              <div><span style={{ color: "var(--muted)" }}>available · </span><span className="mono">{hw.available_ram_gb} GB</span></div>
              <div><span style={{ color: "var(--muted)" }}>3b headroom · </span><span className="mono" style={{ color: hw.can_run_qwen3b ? "var(--ok)" : "var(--err)" }}>{hw.headroom_qwen3b_gb} GB</span></div>
            </div>
          )}
        </div>
      </div>
    );
  }
  window.ProvidersScreen = ProvidersScreen;

  /* ───────── Prompts screen ───────── */
  function PromptsScreen() {
    const [prompts, setPrompts] = useState(window.ARIA_DATA.prompts || []);
    const [expanded, setExpanded] = useState(null);
    const [copied, setCopied] = useState(null);

    useEffect(() => { setPrompts([...(window.ARIA_DATA.prompts || [])]); }, []);

    const copy = (p) => {
      navigator.clipboard.writeText(p.content).then(() => {
        setCopied(p.name);
        setTimeout(() => setCopied(null), 1500);
      });
    };

    const agentColor = {
      "Intake Agent": "#C26A3D", "Decomposer": "#3858B5",
      "GitHub Researcher": "#3D7A4E", "Web Researcher": "#8A3F8C",
      "Pattern Extractor": "#C26A3D", "Synthesizer": "#3858B5",
      "Quality Judge": "#3D7A4E",
    };

    return (
      <div className="page fade-in">
        <div className="page-header">
          <div>
            <h1 className="page-title">System prompts</h1>
            <div className="page-sub">Agent system prompts — the instructions each agent follows during a research run.</div>
          </div>
          <span className="chip mono">{prompts.length} prompts</span>
        </div>

        {prompts.length === 0 ? (
          <div className="panel panel-pad" style={{ textAlign: "center", padding: "48px 24px", color: "var(--muted)" }}>
            No prompts loaded. Make sure the server is running.
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {prompts.map(p => {
              const isOpen = expanded === p.name;
              const color = agentColor[p.agent] || "var(--accent)";
              return (
                <div key={p.name} className="panel">
                  <div
                    className="panel-head"
                    style={{ cursor: "pointer", userSelect: "none" }}
                    onClick={() => setExpanded(isOpen ? null : p.name)}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <div style={{ width: 8, height: 8, borderRadius: "50%", background: color, flexShrink: 0 }} />
                      <h3 style={{ margin: 0 }}>{p.agent}</h3>
                      <span className="mono" style={{ fontSize: 10, color: "var(--muted-2)" }}>{p.name}.txt</span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span className="meta mono">{(p.chars / 1000).toFixed(1)}k chars</span>
                      <span style={{ color: "var(--muted-2)", fontSize: 11 }}>{isOpen ? "▲" : "▼"}</span>
                    </div>
                  </div>
                  {isOpen && (
                    <div className="panel-pad" style={{ paddingTop: 0 }}>
                      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 8 }}>
                        <button className="btn sm" onClick={() => copy(p)}>
                          {copied === p.name ? "✓ copied" : "copy"}
                        </button>
                      </div>
                      <pre style={{
                        margin: 0, padding: "12px 14px", background: "var(--bg-2, var(--bg))",
                        borderRadius: 8, fontSize: 11.5, lineHeight: 1.6,
                        overflowX: "auto", maxHeight: 420, overflowY: "auto",
                        color: "var(--ink)", border: "1px solid var(--line)",
                        whiteSpace: "pre-wrap", wordBreak: "break-word",
                      }}>{p.content}</pre>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  }
  window.PromptsScreen = PromptsScreen;

})();
