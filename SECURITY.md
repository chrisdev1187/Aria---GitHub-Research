# Security Policy

## Supported Versions

ARIA is under active development. The latest release on the `main` branch
receives security updates. Older tags are supported on a best-effort basis.

| Version | Supported          |
|---------|--------------------|
| main    | :white_check_mark: |
| < main  | :x:                |

---

## Reporting a Vulnerability

ARIA handles API keys for multiple LLM providers (Groq, DeepSeek, NVIDIA,
SambaNova, etc.) and may process user-submitted ideas that include proprietary
or sensitive information. We take security seriously.

### How to Report

**Do not open a public GitHub issue.** Instead, use GitHub's private
vulnerability reporting:

- Navigate to the repository's **Security** tab
- Click **"Report a vulnerability"**
  (`https://github.com/chrisdev1187/Aria---GitHub-Research/security/advisories`)
- Fill in the advisory form with the details listed below

### What to Include

Please provide as much of the following as possible:

- **Type of vulnerability** (e.g., API key leakage, command injection,
  SSRF due to uncontrolled URLs, insufficient rate limiting)
- **Steps to reproduce** — include the exact command, input, or configuration
  that triggers the issue
- **Impact** — what an attacker could achieve
- **Suggested fix** (optional)
- **Affected versions** — commit hash, tag, or branch

### What to Expect

- **Acknowledgment** within 72 hours of submission
- **Initial assessment** within 5 business days — we will confirm the
  vulnerability and prioritise a fix
- **Disclosure coordination** — we will work with you on a timeline for
  public disclosure after a fix is released

We aim to release a fix for confirmed vulnerabilities within 14 days of
verification, depending on complexity.

---

## Scope

The following are **in scope**:

- ARIA source code in the `aria/` directory
- CLI behaviour (`python main.py run ...`, `python main.py serve`)
- The web dashboard served by the built-in HTTP server
- API credential handling (`.env`, provider client libraries)
- Output file generation in `aria/output/`

The following are **out of scope**:

- Third-party LLM provider APIs themselves (report issues to the provider)
- Python standard library vulnerabilities
- Operating system or dependency-level issues covered by existing CVEs
- Social engineering attacks against maintainers

---

## Security Considerations for Users

### API Keys

- ARIA stores provider API keys in a `.env` file. **Never commit `.env` to
  version control.** The project's `.gitignore` already excludes `.env` and
  `*.env.local` files.
- API keys are loaded into memory at runtime and used only for outbound HTTP
  requests to the respective providers.
- ARIA supports key rotation (multiple keys per provider used in round-robin)
  and circuit breakers that stop calling a provider after repeated failures.

### Network Access

- ARIA makes outbound HTTPS calls to LLM providers (Groq, DeepSeek, etc.),
  GitHub API (`api.github.com`), DuckDuckGo, and Jina Reader.
- In **offline mode** (`--offline`), all external API calls are disabled and
  only local Ollama models are used.
- The built-in HTTP server binds to `127.0.0.1` by default. Do not expose it
  to untrusted networks.

### Input Handling

- User-supplied software ideas are passed as LLM prompts. ARIA does not
  execute arbitrary code from user input.
- Extracted code from GitHub repos is written to disk for analysis. In
  **build mode**, generated project scaffolds are also written to disk. Both
  are confined to the `aria/output/` directory.

---

## Acknowledgements

We appreciate the community's help in keeping ARIA safe. If you report a
confirmed vulnerability, we will credit you in release notes (unless you
prefer to remain anonymous).
