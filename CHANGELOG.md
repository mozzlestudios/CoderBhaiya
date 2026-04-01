# Changelog

## v0.1.0 — Initial Release

### What We Started With

CoderBhaiya is built on top of [claw-code](https://github.com/instructkr/claw-code) by [@instructkr](https://github.com/instructkr) — a Python project that mirrors and documents the internal architecture of Claude Code. The original repo provided:

- **Command and tool registries** — 150+ commands and 100+ tools catalogued from Claude Code's surface area
- **Prompt routing** — Token-based matching to route user prompts to the right command/tool
- **Bootstrap mode** — Ability to build a session object and simulate routing without any LLM calls
- **Reference data** — JSON snapshots of Claude Code's subsystems (screens, hooks, schemas, etc.)
- **Project structure** — Clean Python package layout with `pyproject.toml`

This was a research/documentation project. No LLM was called. No files were read. No code was executed. It was a map — not the territory.

### What CoderBhaiya Adds

Everything below was designed and built from scratch as an extension to the original harness:

#### Live Agent Engine
- **Turn loop** (`src/turn_loop.py`) — The core agentic loop: send prompt to LLM, get response, if tool calls → execute tools → send results back → repeat. Configurable max turns, token budgets, and stop conditions. Both blocking (`run()`) and streaming (`stream_run()`) modes.
- **Real tool execution** — 7 tools that actually do things:
  - `Read` — Read files with line numbers, offset, and limit
  - `Write` — Create or overwrite files
  - `Edit` — In-place string replacement
  - `Bash` — Execute shell commands with timeout
  - `Grep` — Regex search (uses ripgrep if available, falls back to `re`)
  - `Glob` — File pattern matching
  - `Agent` — Spawn sub-agents (see below)
- **Tool abstraction** (`src/live_tools/base.py`) — `BaseTool` ABC with `definition()` (JSON schema for the LLM) and `execute()`. Adding a new tool = one file + registry entry.

#### Multi-Provider LLM Support
- **5 providers through a single interface** (`src/llm/`):
  - Anthropic (Claude) — full SDK integration
  - OpenAI (o3, GPT-4o, etc.) — full SDK integration
  - Google Gemini — full SDK integration
  - Ollama — pure `urllib.request`, zero dependencies, local models
  - LMStudio — pure `urllib.request`, zero dependencies, local models
- **Unified types** (`src/llm/types.py`) — `LLMMessage`, `LLMResponse`, `ToolCall`, `ToolResult`, `Usage` — same data structures regardless of provider
- **Factory registry** (`src/llm/registry.py`) — `build_llm_client(provider, model)` returns the right client

#### Agent Sub-Spawning
- **Agents that spawn agents** (`src/live_tools/agent_tool.py`) — When the LLM calls the Agent tool, a new `TurnLoopRunner` is created with its own conversation history, tool set, and token budget
- **Recursion safety** — Sub-agents get all tools except `Agent`, preventing infinite spawning
- **Budget isolation** — Sub-agent token budget (50K default) is deducted from the parent's budget

#### Hook Lifecycle System
- **7 hook events** (`src/hooks_lifecycle/types.py`) — `SESSION_START`, `SESSION_END`, `TURN_START`, `TURN_END`, `PRE_TOOL_EXECUTION`, `POST_TOOL_EXECUTION`, `PRE_COMPACTION`
- **Mutable hook context** — Handlers can inspect data, modify tool inputs/outputs, or cancel tool execution entirely
- **Shell hooks** (`src/hooks_lifecycle/shell_hook.py`) — Run arbitrary shell commands on hook events, configured via `settings.json`
- **Hook registry** (`src/hooks_lifecycle/registry.py`) — Register multiple handlers per event, fire in order

#### Skill Injection System
- **Drop-in skills** (`src/skill_system/`) — Markdown files with YAML frontmatter that modify agent behavior at runtime
- **Skill loader** — Scans `~/.claude/skills/` and `./skills/`, parses frontmatter, caches results
- **System prompt injection** — Skills are wrapped in `<skill>` XML tags and appended to the system prompt

#### Interactive CLI
- **REPL** (`src/cli_app/repl.py`) — Readline-enabled interactive chat with streaming output, slash commands (`/model`, `/provider`, `/skill`, `/config`, `/clear`), and persistent conversation state
- **Streaming renderer** (`src/cli_app/streaming.py`) — ANSI-colored terminal output with tool badges, compact input summaries, and multi-line truncation
- **JSON server** (`src/cli_app/server.py`) — stdin/stdout JSON protocol for IDE integration (VS Code extensions, etc.)
- **Config management** (`src/cli_app/config.py`) — Persistent config at `~/.coderbhaiya/config.json` with CLI flag > env var > config file priority

#### Infrastructure
- **Permission gating** (`src/permissions.py`) — Block specific tools by name or prefix
- **Session persistence** (`src/session_store.py`) — Save/load multi-turn conversations
- **Interactive dashboard** (`dashboard.html`) — D3.js codebase explorer with animated flow diagrams, 4 view modes, zoom/pan

### Credits

The original [claw-code](https://github.com/instructkr/claw-code) by [@instructkr](https://github.com/instructkr) provided the foundation — the harness architecture, command/tool registries, and routing system. CoderBhaiya builds the live agent engine on top of that foundation.
