# Changelog

All notable changes to ARIA are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Versions before 1.0.0 are considered pre-release. Breaking changes may occur
between minor versions.

---

## [Unreleased]

### Added

- GitHub Actions CI workflow with ruff linting and pytest testing
  (`.github/workflows/ci.yml`)
- `pyproject.toml` with ruff and pytest configuration (line-length 120,
  rules E/F/W/I/N, target Python 3.11)
- Screenshot capture script (`.github/scripts/capture_screenshots.py`)
- `docs/screenshots/` directory with 6 annotated UI screenshots and a
  companion guide
- Dashboard Screenshots section in README with HTML thumbnail table
- `SECURITY.md` with vulnerability reporting guidelines
- `CHANGELOG.md` (this file)

### Fixed

- 85 ruff lint violations across the codebase: auto-fixed import sorting,
  unused imports, and whitespace; manually renamed ambiguous `l` variables
  to `lib`, added `# noqa` to intentional re-exports, and removed trailing
  whitespace
- Pipeline error handling now captures full traceback in `run_context.error`
  for easier debugging
- Stale `window.ARIA_DATA` from previous pipeline runs is now cleared on new
  run start
- `extracted_repos` and `package_files` are now properly populated from the
  knowledge packager result for the PackageScreen UI
- Pipeline checkpoint names aligned across backend, frontend, and UI handler
  to use orchestrator's actual phase names

---

## [0.1.0] — 2026-05-17

### Added

- Initial ARIA v2 release: Agentic Research Intelligence Architecture
- **8-agent research pipeline**: Intake, Decomposer, GitHub Researcher,
  Web Researcher, Pattern Extractor, Synthesizer, Quality Judge,
  Knowledge Packager
- **Multi-provider LLM pool** with circuit breakers, rate limiting, key
  rotation, and automatic fallback chains
- Parallel GitHub + Web research per sub-problem
- Quality evaluation with automatic re-research loops (up to 2 cycles)
- Structured knowledge package output (README, decomposition, patterns,
  libraries, build plan, web research, risks)
- Build mode with code extraction and project scaffold generation
- Checkpoint/recovery system for resumable pipelines
- React-based live dashboard with swarm visualization, sub-problem cards,
  log stream, and tabbed Knowledge Package viewer
- CLI interface with `run`, `serve`, `status`, `providers`, and `health`
  commands
- Provider clients: Groq, DeepSeek, Gemini, NVIDIA NIM, SambaNova,
  Cerebras, SiliconFlow, Zhipu, Ollama
- GitHub API wrapper with search, scoring, and code extraction
- Web research via DuckDuckGo + Jina Reader
- Comprehensive documentation (README, ARCHITECTURE.md, CONTRIBUTING.md)

[unreleased]: https://github.com/chrisdev1187/Aria---GitHub-Research/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/chrisdev1187/Aria---GitHub-Research/releases/tag/v0.1.0
