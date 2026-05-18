/* Aria — data layer: fetches real API data and populates window.ARIA_DATA */

(function () {
  const _defaultHardware = {
    total_ram_gb: 0, available_ram_gb: 0,
    headroom_qwen3b_gb: 0, headroom_qwen7b_gb: 0,
    can_run_qwen3b: false, can_run_qwen7b: false,
    max_concurrent_agents: 3,
    ollama_running: false, ollama_models: [],
  };

  const _suggestions = [
    { lbl: "cli",     text: "Build a CLI tool that monitors GitHub releases and sends Slack notifications" },
    { lbl: "api",     text: "Design a rate-limited API gateway with circuit breaker patterns" },
    { lbl: "site",    text: "Create a static site generator from markdown with live preview" },
    { lbl: "scraper", text: "Build a parallel web scraper that extracts structured data from documentation sites" },
    { lbl: "agent",   text: "Build an AI coding agent that can autonomously fix test failures in a monorepo" },
  ];

  // Default structure — screens degrade gracefully when values are empty
  window.ARIA_DATA = {
    idea: "",
    suggestions: _suggestions,
    // Filled in from API as the pipeline runs
    ideal_outcome: "",
    core_problems: [],
    domain: [],
    primary_language: "",
    complexity: "",
    research_statuses: {},
    providers: [],
    short_id: "",
    started_at: "",
    finished_at: "",
    sub_problems: [],
    patterns: {
      architectural_patterns: [], libraries_to_use: [],
      repos_to_fork: [], anti_patterns: [],
      gotchas: [], performance: [], security: [],
    },
    quality: { overall_score: 0, coverage: 0, novelty: 0, actionability: 0, verdict: "" },
    package_files: [],
    extracted_repos: [],
    hardware: { ..._defaultHardware },
    runs: [],
    prompts: [],
  };

  window.ARIA_BRIEF_MD = "";

  // Fetch /api/status and merge real values into ARIA_DATA
  async function fetchStatus() {
    try {
      const res = await fetch("/api/status");
      if (!res.ok) return null;
      const d = await res.json();
      const D = window.ARIA_DATA;

      // Providers — always update (backend now refreshes on every call)
      if (d.providers && d.providers.length > 0) D.providers = d.providers;

      // Hardware
      if (d.hardware) D.hardware = d.hardware;

      // Run metadata
      if (d.idea) D.idea = d.idea;
      if (d.run_id) D.short_id = d.run_id;
      if (d.started_at) D.started_at = d.started_at;
      if (d.finished_at) D.finished_at = d.finished_at;

      // Intake analysis
      if (d.ideal_outcome) D.ideal_outcome = d.ideal_outcome;
      if (d.core_problems && d.core_problems.length > 0) D.core_problems = d.core_problems;
      if (d.domain && d.domain.length > 0) D.domain = d.domain;
      if (d.primary_language) D.primary_language = d.primary_language;
      if (d.complexity_estimate) D.complexity = d.complexity_estimate;

      // Sub-problems
      if (d.sub_problems && d.sub_problems.length > 0) D.sub_problems = d.sub_problems;
      if (d.research_statuses) D.research_statuses = d.research_statuses;

      // Patterns
      if (d.patterns && d.patterns.architectural_patterns) D.patterns = d.patterns;

      // Package
      if (d.package_files && d.package_files.length > 0) D.package_files = d.package_files;
      if (d.extracted_repos && d.extracted_repos.length > 0) D.extracted_repos = d.extracted_repos;
      if (d.brief_md) window.ARIA_BRIEF_MD = d.brief_md;

      // Quality
      if (d.result) {
        if (d.result.quality_score != null) D.quality.overall_score = d.result.quality_score;
        if (d.result.verdict) D.quality.verdict = d.result.verdict;
      }
      if (d.overall_score != null) D.quality.overall_score = d.overall_score;
      if (d.verdict) D.quality.verdict = d.verdict;
      if (d.quality_coverage != null) D.quality.coverage = d.quality_coverage;
      if (d.quality_novelty != null) D.quality.novelty = d.quality_novelty;
      if (d.quality_actionability != null) D.quality.actionability = d.quality_actionability;

      return d;
    } catch (_) {
      return null;
    }
  }

  async function fetchRuns() {
    try {
      const res = await fetch("/api/runs");
      if (!res.ok) return;
      const d = await res.json();
      window.ARIA_DATA.runs = d.runs || [];
    } catch (_) {}
  }

  async function fetchPrompts() {
    try {
      const res = await fetch("/api/prompts");
      if (!res.ok) return;
      const d = await res.json();
      window.ARIA_DATA.prompts = d.prompts || [];
    } catch (_) {}
  }

  function resetData() {
    window.ARIA_DATA = {
      idea: "",
      suggestions: _suggestions,
      ideal_outcome: "",
      core_problems: [],
      domain: [],
      primary_language: "",
      complexity: "",
      research_statuses: {},
      providers: [],
      short_id: "",
      started_at: "",
      finished_at: "",
      sub_problems: [],
      patterns: {
        architectural_patterns: [], libraries_to_use: [],
        repos_to_fork: [], anti_patterns: [],
        gotchas: [], performance: [], security: [],
      },
      quality: { overall_score: 0, coverage: 0, novelty: 0, actionability: 0, verdict: "" },
      package_files: [],
      extracted_repos: [],
      hardware: { ..._defaultHardware },
      runs: window.ARIA_DATA.runs,    // preserve past-runs list across resets
      prompts: window.ARIA_DATA.prompts,
    };
    window.ARIA_BRIEF_MD = "";
  }

  // Fetch everything on load
  fetchStatus();
  fetchRuns();
  fetchPrompts();

  // Export for use by app.jsx / screens.jsx
  window.ariaFetchStatus  = fetchStatus;
  window.ariaFetchRuns    = fetchRuns;
  window.ariaFetchPrompts = fetchPrompts;
  window.ariaResetData    = resetData;
})();
