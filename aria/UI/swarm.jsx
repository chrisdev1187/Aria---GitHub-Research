/* Aria — Agent Swarm DAG
   Horizontal flow: Intake → Decompose → fanout(5 sub-problems) → Pattern → Synth → Judge → Package
   Each node has status: idle | active | done.
   Edges flow when transitioning. */

(function () {
  const { useMemo } = React;

  // viewBox is the design space; SVG scales responsively.
  const VW = 1200;
  const VH = 460;

  // Static layout: x per column, y per row.
  const COLS = {
    intake:     { x:  80,  label: "Intake",            short: "intake",            glyph: "I"  },
    decompose:  { x: 230,  label: "Decomposer",        short: "decomposer",         glyph: "D"  },
    sp:         { x: 480,  label: "Researchers",       short: "research",           glyph: "R"  },
    pattern:    { x: 780,  label: "Pattern Extractor",  short: "pattern_extractor",  glyph: "P"  },
    synth:      { x: 920,  label: "Synthesizer",       short: "synthesizer",        glyph: "S"  },
    judge:      { x: 1050, label: "Quality Judge",     short: "quality_judge",      glyph: "J"  },
    package:    { x: 1150, label: "Knowledge Package", short: "knowledge_package",  glyph: "K"  },
  };

  const SP_IDS = ["SP-1", "SP-2", "SP-3", "SP-4", "SP-5"];
  // y positions for sub-problem nodes, centered around VH/2
  const spY = (i) => 90 + i * 60;

  const NODE_R = 16;        // primary node radius
  const SP_R   = 11;        // sub-problem node radius

  function statusColor(s) {
    if (s === "done") return "var(--ok)";
    if (s === "active") return "var(--accent)";
    if (s === "error") return "var(--err)";
    return "var(--muted-2)";
  }
  function statusFill(s) {
    if (s === "done") return "oklch(from var(--ok) l c h / 0.18)";
    if (s === "active") return "var(--accent-soft)";
    if (s === "error") return "oklch(from var(--err) l c h / 0.18)";
    return "var(--panel)";
  }

  /* Main node (circular badge with label) */
  function Node({ cx, cy, status, label, glyph, sub, big = true }) {
    const r = big ? NODE_R : SP_R;
    const stroke = statusColor(status);
    const fill = statusFill(status);
    const labelY = cy + r + 18;
    return (
      <g style={{ transition: "opacity 200ms" }}>
        {/* halo for active */}
        {status === "active" && (
          <circle cx={cx} cy={cy} r={r + 8}
                  fill="none" stroke={stroke} strokeOpacity="0.35"
                  strokeWidth="1.2">
            <animate attributeName="r" values={`${r+4};${r+12};${r+4}`} dur="2s" repeatCount="indefinite" />
            <animate attributeName="stroke-opacity" values="0.6;0.05;0.6" dur="2s" repeatCount="indefinite" />
          </circle>
        )}
        {status === "done" && (
          <circle cx={cx} cy={cy} r={r + 5}
                  fill="none" stroke={stroke} strokeOpacity="0.2" strokeWidth="1" />
        )}
        <circle cx={cx} cy={cy} r={r}
                fill={fill} stroke={stroke} strokeWidth="1.25" />
        <text x={cx} y={cy + 1} textAnchor="middle" dominantBaseline="central"
              fontSize={big ? 11 : 9}
              fontWeight={600}
              fill={status === "idle" ? "var(--muted)" : (status === "done" ? "var(--ok)" : "var(--accent-ink)")}
              fontFamily="var(--mono)"
              style={{ pointerEvents: "none" }}>
          {glyph}
        </text>
        {label && (
          <text x={cx} y={labelY} textAnchor="middle"
                fontSize="10.5" fontWeight="500"
                fill={status === "idle" ? "var(--muted)" : "var(--ink-2)"}
                style={{ letterSpacing: "0.01em" }}>
            {label}
          </text>
        )}
        {sub && (
          <text x={cx} y={labelY + 12} textAnchor="middle"
                fontSize="9" fill="var(--muted-2)"
                fontFamily="var(--mono)" style={{ letterSpacing: "0.04em" }}>
            {sub}
          </text>
        )}
      </g>
    );
  }

  /* Bezier edge between two points, with optional flowing dashes */
  function Edge({ x1, y1, x2, y2, status }) {
    const dx = (x2 - x1) * 0.45;
    const d = `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`;
    const flowing = status === "active";
    const done = status === "done";
    return (
      <g>
        <path d={d}
              fill="none"
              stroke={done ? "var(--ok)" : "var(--line-strong)"}
              strokeOpacity={done ? 0.55 : 0.8}
              strokeWidth="1" />
        {flowing && (
          <path d={d}
                fill="none"
                stroke="var(--accent)"
                strokeWidth="1.2"
                strokeDasharray="6 8"
                style={{ animation: "flow 0.9s linear infinite" }} />
        )}
      </g>
    );
  }

  /* Compute "stage" of each edge from agents map */
  function edgeStatus(fromS, toS) {
    if (fromS === "done" && toS === "done") return "done";
    if (fromS === "done" && (toS === "active")) return "active";
    if (fromS === "active") return "active";
    return "idle";
  }

  function AgentSwarm({ agents, sps, idea, subtitle }) {
    // agents: {intake, decompose, pattern_extractor, synthesizer, quality_judge, knowledge_package} → status
    // sps: [{ id, status, github: status, web: status }]
    const cIntake = COLS.intake.x;
    const cDecom = COLS.decompose.x;
    const cSp = COLS.sp.x;
    const cPat = COLS.pattern.x;
    const cSyn = COLS.synth.x;
    const cJud = COLS.judge.x;
    const cPkg = COLS.package.x;
    const cyMain = VH / 2;

    // Group max status across all SPs to determine inbound edge stage
    const allSpsDone = sps.every(s => s.status === "done");
    const anySpActive = sps.some(s => s.status === "active");
    const groupStatus = allSpsDone ? "done" : (anySpActive ? "active" : "idle");

    return (
      <svg viewBox={`0 0 ${VW} ${VH}`} preserveAspectRatio="xMidYMid meet" style={{ width: "100%", height: "auto", maxHeight: 460 }}>
        {/* faint grid baseline */}
        <line x1="0" y1={cyMain} x2={VW} y2={cyMain}
              stroke="var(--line)" strokeDasharray="2 6" strokeOpacity="0.5" />

        {/* idea anchor at far left */}
        <g>
          <rect x={cIntake - 60} y={cyMain - 86} width="120" height="42" rx="8"
                fill="var(--panel-2)" stroke="var(--line)" />
          <text x={cIntake} y={cyMain - 70} textAnchor="middle"
                fontSize="9" fill="var(--muted)" fontFamily="var(--mono)"
                style={{ letterSpacing: "0.05em", textTransform: "uppercase" }}>
            idea
          </text>
          <text x={cIntake} y={cyMain - 56} textAnchor="middle"
                fontSize="10.5" fill="var(--ink-2)"
                fontWeight="500">
            {(idea || "").slice(0, 28)}{idea && idea.length > 28 ? "…" : ""}
          </text>
          <line x1={cIntake} y1={cyMain - 44} x2={cIntake} y2={cyMain - NODE_R}
                stroke="var(--line-strong)" strokeWidth="1" strokeDasharray="2 4" />
        </g>

        {/* main spine: intake → decompose */}
        <Edge x1={cIntake} y1={cyMain} x2={cDecom} y2={cyMain}
              status={edgeStatus(agents.intake, agents.decomposer)} />

        {/* fanout from decompose to each SP */}
        {sps.map((sp, i) => (
          <Edge key={"in-" + sp.id}
                x1={cDecom} y1={cyMain}
                x2={cSp - 30} y2={spY(i)}
                status={edgeStatus(agents.decomposer, sp.status)} />
        ))}

        {/* fan-in from each SP to pattern */}
        {sps.map((sp, i) => (
          <Edge key={"out-" + sp.id}
                x1={cSp + 30} y1={spY(i)}
                x2={cPat} y2={cyMain}
                status={edgeStatus(sp.status, agents.pattern_extractor)} />
        ))}

        {/* pattern → synth → judge → package */}
        <Edge x1={cPat} y1={cyMain} x2={cSyn} y2={cyMain}
              status={edgeStatus(agents.pattern_extractor, agents.synthesizer)} />
        <Edge x1={cSyn} y1={cyMain} x2={cJud} y2={cyMain}
              status={edgeStatus(agents.synthesizer, agents.quality_judge)} />
        <Edge x1={cJud} y1={cyMain} x2={cPkg} y2={cyMain}
              status={edgeStatus(agents.quality_judge, agents.knowledge_package)} />

        {/* main nodes */}
        <Node cx={cIntake} cy={cyMain} status={agents.intake}
              label="Intake" glyph="01" sub="parse · scope" />
        <Node cx={cDecom} cy={cyMain} status={agents.decomposer}
              label="Decompose" glyph="02" sub={`${sps.length} sub-problems`} />

        {/* sub-problem cluster: framing rect */}
        <rect x={cSp - 56} y={spY(0) - 22} width="112"
              height={Math.max(0, spY(Math.max(0, sps.length - 1)) - spY(0) + 44)}
              rx="10"
              fill="var(--panel-2)"
              fillOpacity="0.55"
              stroke="var(--line)"
              strokeDasharray="3 4" />
        <text x={cSp} y={spY(0) - 28} textAnchor="middle"
              fontSize="9" fill="var(--muted)" fontFamily="var(--mono)"
              style={{ letterSpacing: "0.05em", textTransform: "uppercase" }}>
          parallel research
        </text>

        {/* sub-problem nodes (smaller) */}
        {sps.map((sp, i) => (
          <g key={"sp-" + sp.id}>
            <Node cx={cSp} cy={spY(i)} status={sp.status}
                  glyph={sp.id.replace("SP-", "")} big={false} />
            {/* per-sp source dots: github (left) and web (right) */}
            <circle cx={cSp - 22} cy={spY(i)} r="3"
                    fill={sp.github === "done" ? "var(--ok)" : sp.github === "active" ? "var(--accent)" : "var(--muted-2)"}>
              {sp.github === "active" && <animate attributeName="opacity" values="1;0.3;1" dur="1.2s" repeatCount="indefinite" />}
            </circle>
            <circle cx={cSp + 22} cy={spY(i)} r="3"
                    fill={sp.web === "done" ? "var(--ok)" : sp.web === "active" ? "var(--accent)" : "var(--muted-2)"}>
              {sp.web === "active" && <animate attributeName="opacity" values="1;0.3;1" dur="1.2s" repeatCount="indefinite" />}
            </circle>
            <text x={cSp - 42} y={spY(i) + 3} textAnchor="end"
                  fontSize="8" fontFamily="var(--mono)"
                  fill="var(--muted-2)" style={{ letterSpacing: "0.04em" }}>
              gh
            </text>
            <text x={cSp + 42} y={spY(i) + 3} textAnchor="start"
                  fontSize="8" fontFamily="var(--mono)"
                  fill="var(--muted-2)" style={{ letterSpacing: "0.04em" }}>
              web
            </text>
          </g>
        ))}

        {/* trailing nodes */}
        <Node cx={cPat} cy={cyMain} status={agents.pattern_extractor}
              label="Pattern Extractor" glyph="03" sub="extract" />
        <Node cx={cSyn} cy={cyMain} status={agents.synthesizer}
              label="Synthesizer" glyph="04" sub="outline-first" />
        <Node cx={cJud} cy={cyMain} status={agents.quality_judge}
              label="Quality Judge" glyph="05" sub="gap-detect" />
        <Node cx={cPkg} cy={cyMain} status={agents.knowledge_package}
              label="Knowledge Package" glyph="06" sub="export" />

        {/* small caption above to anchor the diagram */}
        {subtitle && (
          <text x={VW / 2} y={28} textAnchor="middle"
                fontSize="10" fontFamily="var(--mono)"
                fill="var(--muted)"
                style={{ letterSpacing: "0.06em", textTransform: "uppercase" }}>
            {subtitle}
          </text>
        )}
      </svg>
    );
  }

  window.AgentSwarm = AgentSwarm;
})();
