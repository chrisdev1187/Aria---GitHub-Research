# ARIA Dashboard — Screenshot Guide

This directory contains annotated screenshots of the ARIA web dashboard. Each
screenshot highlights a key screen or interaction state.

---

## 1. Intake Screen

![Intake Screen](01-intake-screen.png)

The **Intake Screen** is the landing page where users enter a software idea.

| # | Element | Description |
|---|---------|-------------|
| ① | Idea input | Text area or styled input for pasting the software idea to research |
| ② | Mode selector | Toggle between **research** (default) and **build** (with code extraction) |
| ③ | Start button | Triggers the 8-agent research pipeline |
| ④ | Theme toggle | Switch between light/dark themes |
| ⑤ | Status bar | Shows server status and active run information |

---

## 2. Pipeline Screen

![Pipeline Screen](02-pipeline-screen.png)

The **Pipeline Screen** appears after starting a research run. It shows real-time
progress through the 8-agent pipeline.

| # | Element | Description |
|---|---------|-------------|
| ① | Agent swarm | Visual timeline of all 8 agents (Intake through Knowledge Packager) with per-agent status |
| ② | Sub-problem cards | One card per sub-problem showing GitHub and Web research status |
| ③ | Research status | Per-sub-problem indicators: `queued` → `active` → `done` |
| ④ | Progress bar | Overall pipeline completion percentage |
| ⑤ | Log stream | Live scrolling log of agent actions and API calls |
| ⑥ | Phase indicator | Current active agent phase with elapsed time |

---

## 3. Knowledge Package Screen

![Knowledge Package Screen](03-package-screen.png)

The **Package Screen** shows the final structured research output with a tabbed
interface.

| # | Element | Description |
|---|---------|-------------|
| ① | Tab bar | Tabs: **Brief**, **Sub-problems**, **Patterns**, **Repos**, **Raw Artifacts** |
| ② | Navigation | Left sidebar with links to different sections of the package |
| ③ | Action buttons | "Re-research gaps", "Hand off to Claude Code" |
| ④ | Metadata | Pipeline summary (elapsed time, token usage, agents run) |

---

## 4. Brief Tab

![Brief Tab](04-brief-tab.png)

The **Brief tab** displays the full research brief as rendered markdown.

The brief includes:
- **Executive Summary** — High-level overview of findings
- **Ideal Outcome** — What a successful implementation looks like
- **Domain Analysis** — Classification and complexity assessment
- **Research Objectives** — Key questions addressed
- **Build Order** — Recommended implementation phases
- **Architecture Decision** — Chosen architectural approach with rationale

---

## 5. Sub-Problems Tab

![Sub-problems Tab](05-sub-problems-tab.png)

The **Sub-problems tab** lists each decomposed sub-problem with its research
findings.

Each sub-problem card shows:
- **Title** — e.g., "User Authentication & Account Management"
- **GitHub findings** — Top repos, stars, relevance
- **Web research** — Articles, documentation links
- **Patterns extracted** — Libraries, architectural approaches

---

## 6. Settings Panel

![Settings Panel](06-settings-panel.png)

The **Settings/Tweaks panel** provides runtime configuration:

| # | Element | Description |
|---|---------|-------------|
| ① | Theme toggle | Switch between light and dark mode |
| ② | Provider info | Currently active LLM providers and their fallback chains |
| ③ | Configuration | Research parameters (max repos, max sub-problems, etc.) |
| ④ | Server info | Pipeline status, uptime, API endpoint details |

---

## Screenshot Notes

- All screenshots were captured at **1440×900** viewport at **2× device scale**.
- The pipeline screenshots show an active research run for a Python CLI tool idea.
- UI is built with **React 18** and styled with **CSS oklch() color space** supporting
  automatic light/dark mode.
