# Contributing to ARIA

Thank you for your interest in contributing to ARIA! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating, you agree to maintain a respectful and inclusive environment for everyone.

## How to Contribute

### Reporting Issues

- **Bug Reports**: Include the full error message, steps to reproduce, and your configuration (OS, Python version, provider keys used)
- **Feature Requests**: Describe the use case and how it fits into the research pipeline
- **Provider Issues**: Note which provider failed and include the circuit breaker/fallback chain state

### Setting Up Development Environment

```bash
# Clone the repo
git clone https://github.com/chrisdev1187/Aria---GitHub-Research.git
cd Aria---GitHub-Research/aria

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Development Workflow

1. **Pick an area** — Agents, tools, UI, or infrastructure
2. **Understand the pattern** — Read the relevant agent/tool code and its tests
3. **Make focused changes** — One logical change per commit
4. **Test locally** — Run `python main.py run "Your test idea" --dry-run` to verify
5. **Submit a PR** — Include a clear description of what changed and why

### Code Style

- **Python**: Follow PEP 8. Use type hints for all function signatures
- **JavaScript/JSX**: Use modern ES2020+ syntax. Prefer functional components
- **Prompts**: Keep system prompts concise and task-specific. Use the `_default_prompt()` fallback pattern

### Adding a New Provider

1. Create a new client in `tools/` following the existing client pattern (e.g., `groq_client.py`)
2. Add endpoint and model config in `config.py`
3. Add rate limits in `config.py`
4. Add key loading support in the provider pool
5. Wire it into the desired agent's fallback chain

### Adding a New Agent

1. Create the agent in `agents/` following the existing pattern
2. Add a system prompt in `prompts/`
3. Register the agent in `orchestrator.py`'s pipeline
4. Add checkpoint handling in `main.py`'s `_checkpoint_with_context`
5. Add the agent key and phase order in `UI/app.jsx`

### Testing

```bash
# Dry run to estimate cost & runtime
python main.py run "Your idea" --dry-run

# Quick pipeline (requires API keys)
python main.py run "Build a simple CLI tool" --mode research

# Test UI
python main.py serve --port 8080
```

### Pull Request Process

1. Ensure your code follows the existing patterns and style
2. Update documentation if you're changing behavior or adding features
3. Test with a dry run before submitting
4. Reference any related issues in your PR description

## Architecture Decisions

- **Checkpoint-first**: Every agent saves state before proceeding. This enables resume and debugging
- **Provider agnosticism**: No hard dependencies on specific LLM APIs. Fallback chains are the norm
- **Minimal dependencies**: Keep the dependency footprint small. Prefer stdlib or well-established packages
- **UI independence**: The frontend is a thin client. All logic lives in Python
