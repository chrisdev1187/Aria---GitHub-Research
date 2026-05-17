/* Aria — root app, real API engine, and tweaks integration. */

const { useState, useEffect, useRef, useCallback } = React;

/* ───────── Tweak defaults (editable by host) ───────── */
const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "accent": "#C26A3D",
  "theme": "light"
}/*EDITMODE-END*/;

const ACCENT_PALETTES = {
  "#C26A3D": { light: "oklch(58% 0.16 32)",  dark: "oklch(72% 0.16 32)",  ink: "oklch(28% 0.12 32)" },
  "#3858B5": { light: "oklch(45% 0.17 250)", dark: "oklch(70% 0.16 250)", ink: "oklch(22% 0.14 250)" },
  "#3D7A4E": { light: "oklch(46% 0.14 150)", dark: "oklch(70% 0.14 150)", ink: "oklch(22% 0.10 150)" },
  "#8A3F8C": { light: "oklch(48% 0.16 320)", dark: "oklch(72% 0.14 320)", ink: "oklch(24% 0.12 320)" },
};

/* ───────── Phase order for deriving agent statuses ───────── */
const PHASE_ORDER = ["intake", "decomposer", "github_research", "web_research", "pattern_extractor", "synthesizer", "quality_judge", "knowledge_package"];
const AGENT_KEYS = ["intake", "decomposer", "pattern_extractor", "synthesizer", "quality_judge", "knowledge_package"];

function buildRunState(api) {
  const phase = api.phase || "idle";
  const phaseIdx = PHASE_ORDER.indexOf(phase);

  // Derive agent statuses from current phase
  const agents = {};
  for (const k of AGENT_KEYS) {
    const idx = PHASE_ORDER.indexOf(k);
    if (phase === "done" || phase === "idle") {
      agents[k] = phase === "done" ? "done" : "idle";
    } else if (idx < 0) {
      agents[k] = "idle";
    } else if (idx < phaseIdx) {
      agents[k] = "done";
    } else if (idx === phaseIdx) {
      agents[k] = "active";
    } else {
      agents[k] = "idle";
    }
  }

  // Derive sub-problem statuses — use per-sub-problem research_statuses if available
  const rs = api.research_statuses || {};
  const sps = (api.sub_problems || []).map((sp, i) => {
    const spId = sp.id || `SP-${i + 1}`;
    const gStatus = (rs.github || {})[spId];
    const wStatus = (rs.web || {})[spId];
    const isResearching = phaseIdx >= 2 && phaseIdx <= 3;  // github_research or web_research
    const isDone = phaseIdx > 3 || phase === "done";  // past research phases
    // Individual status from research_statuses beats phase-based derivation
    let status;
    if (isDone) {
      status = "done";  // Overall pipeline past research phase — all done
    } else if (gStatus === "done" && wStatus === "done") {
      status = "done";  // Both researchers finished for this sub-problem
    } else if (gStatus === "done" || wStatus === "done" || gStatus === "active" || wStatus === "active" || isResearching) {
      status = "active";
    } else {
      status = "idle";
    }
    return {
      id: spId,
      title: sp.title || "",
      status,
      github: gStatus || (isDone ? "done" : (isResearching ? "active" : "idle")),
      web: wStatus || (isDone ? "done" : (isResearching ? "active" : "idle")),
      repos_found: sp.repos_found || 0,
      pages_read: sp.pages_read || 0,
      github_queries: sp.github_queries || [],
      web_queries: sp.web_queries || [],
    };
  });

  // Transform logs
  const logs = (api.logs || []).map((l, i) => ({
    id: i + 1,
    t: (l.time || "").slice(11, 19),
    src: l.level || "info",
    msg: l.message || "",
    kind: l.level === "error" ? "err" : l.level === "success" ? "ok" : "",
  }));

  return {
    phase,
    paused: false,
    elapsed: api.progress_pct || 0,
    tokens: 0,
    agents,
    sps,
    logs,
  };
}

/* ───────── Real API engine ───────── */
function useApiRun(onDone) {
  const [state, setState] = useState({
    phase: "idle", paused: false, elapsed: 0, tokens: 0,
    agents: { intake: "idle", decomposer: "idle", pattern: "idle", synth: "idle", judge: "idle", package: "idle" },
    sps: [],
    logs: [],
  });

  const pollRef = useRef(null);
  const tickRef = useRef(null);
  const doneCalled = useRef(false);

  // Fetch status and refresh ARIA_DATA + local state
  const poll = useCallback(async () => {
    const data = await (window.ariaFetchStatus || (() => null))();
    if (!data) return;

    if (data.status === "running") {
      setState(buildRunState(data));
    } else if (data.status === "done") {
      setState(buildRunState({ ...data, phase: "done" }));
      if (!doneCalled.current) {
        doneCalled.current = true;
        if (onDone) onDone();
      }
    } else if (data.status === "error") {
      setState(s => ({
        ...s,
        phase: "done",
        logs: [...s.logs, { id: Date.now(), t: "—", src: "error", msg: data.error || "Pipeline failed", kind: "err" }],
      }));
    }
  }, [onDone]);

  const clearAll = () => {
    if (pollRef.current) clearInterval(pollRef.current);
    if (tickRef.current) clearInterval(tickRef.current);
    pollRef.current = null;
    tickRef.current = null;
  };

  const start = useCallback(async (idea) => {
    clearAll();
    doneCalled.current = false;
    if (window.ariaResetData) window.ariaResetData();
    setState({
      phase: "intake", paused: false, elapsed: 0, tokens: 0,
      agents: { intake: "active", decomposer: "idle", pattern_extractor: "idle", synthesizer: "idle", quality_judge: "idle", knowledge_package: "idle" },
      sps: [],
      logs: [{ id: 1, t: "00:00", src: "orchestrator", msg: "Starting pipeline...", kind: "ok" }],
    });

    try {
      await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ idea, mode: "research" }),
      });
    } catch (_) {
      setState(s => ({ ...s, logs: [...s.logs, { id: 2, t: "—", src: "error", msg: "Failed to start run", kind: "err" }] }));
      return;
    }

    // Start polling
    pollRef.current = setInterval(poll, 2000);
    tickRef.current = setInterval(() => {
      setState(s => ({ ...s, elapsed: s.elapsed + 2 }));
    }, 2000);

    // Initial fetch immediately
    await poll();
  }, [poll]);

  const reset = async () => {
    clearAll();
    try { await fetch("/api/reset"); } catch (_) {}
    // Re-fetch providers after reset
    setTimeout(poll, 500);
    setState({
      phase: "idle", paused: false, elapsed: 0, tokens: 0,
      agents: { intake: "idle", decomposer: "idle", pattern: "idle", synth: "idle", judge: "idle", package: "idle" },
      sps: [],
      logs: [],
    });
  };

  // Poll for initial data (providers) on mount
  useEffect(() => {
    const init = async () => {
      await poll();
    };
    init();
    // Set up background polling for data refreshes (not during a run)
    const bgPoll = setInterval(async () => {
      await (window.ariaFetchStatus || (() => null))();
    }, 10000);
    return () => {
      clearInterval(bgPoll);
      clearAll();
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return { state, start, reset };
}

/* ───────── App shell ───────── */
function App() {
  const [view, setView] = useState("intake"); // intake | running | done
  const tweaks = window.useTweaks(TWEAK_DEFAULTS);
  const [tw, setTweak] = tweaks;
  const simRef = useRef(null);

  // theme + accent application
  useEffect(() => {
    const html = document.documentElement;
    html.setAttribute("data-theme", tw.theme);
    const palette = ACCENT_PALETTES[tw.accent] || ACCENT_PALETTES["#C26A3D"];
    const color = tw.theme === "dark" ? palette.dark : palette.light;
    html.style.setProperty("--accent", color);
    html.style.setProperty("--accent-soft", `oklch(from ${color} l c h / 0.12)`);
    html.style.setProperty("--accent-line", `oklch(from ${color} l c h / 0.35)`);
    html.style.setProperty("--accent-ink", palette.ink);
  }, [tw.theme, tw.accent]);

  const sim = useApiRun(useCallback(() => {
    // Pipeline finished — switch to package view
    setView("done");
  }, []));

  // expose simulator imperatively
  simRef.current = sim;

  const start = (idea) => {
    setView("running");
    sim.start(idea);
  };

  const goPackage = () => setView("done");

  const newRun = () => {
    sim.reset();
    setView("intake");
  };

  const Ic = window.Ic;
  const D = window.ARIA_DATA;

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-glyph">
            {/* aria mark — three intersecting rings */}
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <circle cx="6.5" cy="9" r="5" stroke="currentColor" strokeWidth="1.5"/>
              <circle cx="11.5" cy="9" r="5" stroke="currentColor" strokeWidth="1.5" opacity="0.55"/>
              <circle cx="9" cy="9" r="1.6" fill="currentColor"/>
            </svg>
          </span>
          <span>aria</span>
          <span className="brand-tag">deep code research · v2</span>
        </div>

        <div className="topbar-center">
          {view !== "intake" && (
            <span className={`run-pill ${view === "running" && sim.state.phase !== "done" ? "running" : "done"}`}>
              <span className="dot" />
              <span>{D.short_id || "running"}</span>
              <span style={{ color: "var(--muted-2)" }}>·</span>
              <span style={{ color: "var(--muted)" }}>{sim.state.phase}</span>
            </span>
          )}
        </div>

        <div className="topbar-actions">
          <button className="icon-btn" title="Toggle theme"
                  onClick={() => setTweak("theme", tw.theme === "light" ? "dark" : "light")}>
            {tw.theme === "light" ? <Ic.moon /> : <Ic.sun />}
          </button>
          <button className="icon-btn active" title="Tweaks"
                  onClick={() => window.parent.postMessage({ type: "__edit_mode_available" }, "*")}>
            <Ic.spark />
          </button>
        </div>
      </header>

      <nav className="nav">
        <div className="nav-section">
          <div className="nav-label">workspace</div>
          <div className={`nav-item ${view === "intake" ? "active" : ""}`} onClick={newRun}>
            <span className="ic"><Ic.plus /></span> New run
          </div>
          <div className={`nav-item ${view === "running" ? "active" : ""}`}
               onClick={() => sim.state.phase !== "idle" && setView("running")}
               style={{ opacity: sim.state.phase === "idle" ? 0.5 : 1 }}>
            <span className="ic"><Ic.flask /></span> Active run
            {sim.state.phase !== "idle" && sim.state.phase !== "done" &&
              <span className="count" style={{ color: "var(--accent)" }}>● live</span>}
            {sim.state.phase === "done" && <span className="count">✓</span>}
          </div>
          <div className={`nav-item ${view === "done" ? "active" : ""}`}
               onClick={() => sim.state.phase === "done" && setView("done")}
               style={{ opacity: sim.state.phase === "done" ? 1 : 0.4 }}>
            <span className="ic"><Ic.folder /></span> Knowledge package
            {sim.state.phase === "done" && <span className="count">ready</span>}
          </div>
        </div>

        <div className="nav-section">
          <div className="nav-label">library</div>
          <div className="nav-item"><span className="ic"><Ic.layers /></span> Past runs <span className="count">—</span></div>
          <div className="nav-item"><span className="ic"><Ic.chip /></span> Providers</div>
          <div className="nav-item"><span className="ic"><Ic.folder /></span> Prompts</div>
        </div>

        <div className="nav-footer">
          <div className="page-sub" style={{ fontSize: 11, color: "var(--muted-2)" }}>
            <span className="mono">real pipeline · live data</span>
            <br />
            <span style={{ color: "var(--muted)" }}>api-driven</span>
          </div>
        </div>
      </nav>

      <main className="main">
        {view === "intake" && <window.IntakeScreen onStart={start} />}
        {view === "running" && <window.PipelineScreen runState={sim.state} simRef={simRef} onView={goPackage} />}
        {view === "done" && <window.PackageScreen onNewRun={newRun} />}
      </main>

      {/* Tweaks panel */}
      <window.TweaksPanel title="Tweaks">
        <window.TweakSection label="Theme">
          <window.TweakRadio
            label="Mode"
            value={tw.theme}
            options={[
              { value: "light", label: "Light" },
              { value: "dark",  label: "Dark"  },
            ]}
            onChange={(v) => setTweak("theme", v)}
          />
        </window.TweakSection>
        <window.TweakSection label="Accent palette">
          <window.TweakColor
            label="Accent"
            value={tw.accent}
            options={["#C26A3D", "#3858B5", "#3D7A4E", "#8A3F8C"]}
            onChange={(v) => setTweak("accent", v)}
          />
        </window.TweakSection>
        <window.TweakSection label="Pipeline">
          <window.TweakButton label="New run" onClick={() => { sim.reset(); setView("intake"); }} />
        </window.TweakSection>
      </window.TweaksPanel>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
