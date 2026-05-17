/* Aria — data layer: fetches real API data and populates window.ARIA_DATA */

(function () {
  // Default structure — screens degrade gracefully when values are empty
  window.ARIA_DATA = {
    idea: "",
    suggestions: [
      { lbl: "cli", text: "Build a CLI tool that monitors GitHub releases and sends Slack notifications" },
      { lbl: "api", text: "Design a rate-limited API gateway with circuit breaker patterns" },
      { lbl: "site", text: "Create a static site generator from markdown with live preview" },
      { lbl: "scraper", text: "Build a parallel web scraper that extracts structured data from documentation sites" },
      { lbl: "agent", text: "Build an AI coding agent that can autonomously fix test failures in a monorepo" },
    ],
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
  };

  window.ARIA_BRIEF_MD = "";

  // Fetch /api/status and merge real values into ARIA_DATA
  async function fetchStatus() {
    try {
      const res = await fetch("/api/status");
      if (!res.ok) return null;
      const d = await res.json();
      const D = window.ARIA_DATA;

      // Providers — update from API
      if (d.providers && d.providers.length > 0) D.providers = d.providers;

      // Run metadata
      if (d.idea) D.idea = d.idea;
      if (d.run_id) D.short_id = d.run_id;
      if (d.started_at) D.started_at = d.started_at;
      if (d.finished_at) D.finished_at = d.finished_at;

      // Intake analysis — ideal outcome, core problems, domain, etc.
      if (d.ideal_outcome) D.ideal_outcome = d.ideal_outcome;
      if (d.core_problems && d.core_problems.length > 0) D.core_problems = d.core_problems;
      if (d.domain && d.domain.length > 0) D.domain = d.domain;
      if (d.primary_language) D.primary_language = d.primary_language;
      if (d.complexity_estimate) D.complexity = d.complexity_estimate;

      // Sub-problems from decomposition
      if (d.sub_problems && d.sub_problems.length > 0) D.sub_problems = d.sub_problems;

      // Per-sub-problem research status (github_SP-1, web_SP-2, etc.)
      if (d.research_statuses) D.research_statuses = d.research_statuses;

      // Patterns from extraction
      if (d.patterns && d.patterns.architectural_patterns) D.patterns = d.patterns;

      // Package browser data
      if (d.package_files && d.package_files.length > 0) D.package_files = d.package_files;
      if (d.extracted_repos && d.extracted_repos.length > 0) D.extracted_repos = d.extracted_repos;

      // Brief markdown
      if (d.brief_md) window.ARIA_BRIEF_MD = d.brief_md;

      // Quality / results
      if (d.result) {
        if (d.result.quality_score != null) D.quality.overall_score = d.result.quality_score;
        if (d.result.verdict) D.quality.verdict = d.result.verdict;
      }
      if (d.overall_score != null) D.quality.overall_score = d.overall_score;
      if (d.verdict) D.quality.verdict = d.verdict;

      return d;
    } catch (_) {
      return null;
    }
  }

  function resetData() {
    window.ARIA_DATA = {
      idea: "",
      suggestions: [
        { lbl: "cli", text: "Build a CLI tool that monitors GitHub releases and sends Slack notifications" },
        { lbl: "api", text: "Design a rate-limited API gateway with circuit breaker patterns" },
        { lbl: "site", text: "Create a static site generator from markdown with live preview" },
        { lbl: "scraper", text: "Build a parallel web scraper that extracts structured data from documentation sites" },
        { lbl: "agent", text: "Build an AI coding agent that can autonomously fix test failures in a monorepo" },
      ],
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
    };
    window.ARIA_BRIEF_MD = "";
  }

  // Poll on load
  fetchStatus();

  // Export for use by app.jsx
  window.ariaFetchStatus = fetchStatus;
  window.ariaResetData = resetData;
})();
