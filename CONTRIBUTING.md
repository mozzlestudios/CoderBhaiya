# Contributing to CoderBhaiya

Thanks for your interest in contributing! CoderBhaiya is a Python agent harness with multi-provider LLM support, real tool execution, and agent sub-spawning.

## Getting Started

```bash
git clone https://github.com/mozzlestudios/CoderBhaiya.git
cd CoderBhaiya
pip install -e ".[all]"
```

## What You Can Work On

**Good first issues:**
- Add a new LLM provider client (see `src/llm/` for existing examples)
- Add a new tool (see `src/live_tools/` for the pattern)
- Write tests for existing modules
- Improve documentation or examples

**Bigger contributions:**
- Token budget optimization in the turn loop
- New hook event types
- Streaming improvements
- IDE integration (VS Code extension using the JSON server)

## How to Contribute

1. Fork the repo
2. Create a branch (`git checkout -b feature/your-feature`)
3. Make your changes
4. Run the tests: `python3 -m unittest discover -s tests -v`
5. Commit with a clear message
6. Open a PR against `main`

## Code Structure

```
src/
  llm/           # LLM provider clients (add new providers here)
  live_tools/    # Tool implementations (add new tools here)
  hooks_lifecycle/  # Hook system
  skill_system/  # Skill loading and injection
  cli_app/       # REPL, server, config, streaming
  turn_loop.py   # Core agent loop
  runtime.py     # Session orchestrator
  main.py        # CLI entrypoint
```

## Adding a New LLM Provider

1. Create `src/llm/your_provider_client.py`
2. Extend `BaseLLMClient` from `src/llm/base.py`
3. Implement `send()` and `stream()` methods
4. Register it in `src/llm/registry.py`
5. Add optional dependency in `pyproject.toml`

> **Note:** For local/self-hosted providers, prefer pure `urllib.request` over external SDKs — this is how Ollama and LMStudio clients work, keeping the core zero-dependency.

## Adding a New Tool

1. Create `src/live_tools/your_tool.py`
2. Extend `BaseTool` from `src/live_tools/base.py`
3. Implement `definition()` (JSON schema) and `execute()`
4. Register it in `src/live_tools/registry.py`

## Style

- Python 3.11+
- Type hints everywhere
- Dataclasses over dicts
- Keep modules focused — one responsibility per file

## Questions?

Open an issue or reach out via the repo discussions.
