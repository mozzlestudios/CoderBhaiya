# CoderBhaiya

<p align="center">
  <strong>A fully functional AI agent harness with multi-provider LLM support, real tool execution, and agent sub-spawning</strong>
</p>

<p align="center">
  <a href="#quickstart"><img src="https://img.shields.io/badge/Get%20Started-blue?style=for-the-badge" alt="Get Started" /></a>
  <a href="#live-mode"><img src="https://img.shields.io/badge/Live%20Mode-green?style=for-the-badge" alt="Live Mode" /></a>
  <a href="#providers"><img src="https://img.shields.io/badge/5%20LLM%20Providers-purple?style=for-the-badge" alt="5 Providers" /></a>
</p>

---

## What is this?

CoderBhaiya is a Python agent harness that can connect to **any LLM provider** and execute real developer tools — file reads, writes, edits, bash commands, grep, glob, and even spawn sub-agents. Think of it as a from-scratch implementation of the agentic coding pattern: the LLM thinks, decides which tools to call, gets results back, and keeps going until the task is done.

### Key capabilities

- **`pip install` + `cb chat`** — Installable CLI with interactive REPL, streaming output, readline history
- **Multi-provider LLM support** — Anthropic (Claude), OpenAI (GPT-4o), Google Gemini, Ollama (local), LMStudio (local)
- **7 real tools** — Read, Write, Edit, Bash, Grep, Glob, Agent (sub-spawning)
- **Hook lifecycle** — 7 hook events (pre/post tool execution, session start/end, turn start/end, pre-compaction) with shell hook support
- **Skill injection** — Load skill files from `~/.claude/skills/` or `./skills/` and inject into system prompts
- **Agent sub-spawning** — Agents can spawn sub-agents with isolated tool sets and budgets (no infinite recursion)
- **Reactive turn loop** — LLM responds with text or tool calls; harness executes tools, sends results back, repeats
- **JSON server mode** — stdin/stdout protocol for VS Code extensions and IDE integrations
- **Interactive dashboard** — D3.js codebase explorer with animated flow diagrams, 4 view modes, zoom/pan

---

## Architecture

```
                          User Prompt
                              |
                        [PortRuntime]
                         /    |    \
                   Route   Bootstrap  Live Session
                    |         |           |
              Token Match   Setup    [TurnLoopRunner]
              Commands +    Report      |
              Tools          |     LLM.send() <---> Tool.execute()
                             |          |               |
                       [QueryEngine]    |        Read/Write/Edit/
                                        |        Bash/Grep/Glob/Agent
                                        |
                                   Hook Lifecycle
                                   (pre/post tool, session, turn)
```

**Two-layer design:**
- **Harness layer** — Intent routing, registry, lifecycle, permissions, session persistence
- **Engine layer** — LLM turn loop, token management, tool execution, agent spawning

---

## Quickstart

### Install

```bash
# From PyPI (when published)
pip install coderbhaiya

# Or from source
git clone https://github.com/mozzlestudios/CoderBhaiya.git
cd CoderBhaiya
pip install -e .

# With a specific LLM provider
pip install -e ".[anthropic]"    # Claude
pip install -e ".[openai]"       # GPT-4o
pip install -e ".[all]"          # All cloud providers
```

### Configure

```bash
# Set your provider and API key (saved to ~/.coderbhaiya/config.json)
cb config set provider anthropic
cb config set api_key sk-ant-your-key-here
cb config set model claude-sonnet-4-20250514

# Or use local models (no API key needed)
cb config set provider ollama

# View config
cb config show
```

### Start chatting

```bash
# Interactive REPL with streaming output
cb chat

# Override provider/model for a session
cb chat --provider openai --model gpt-4o
cb chat --provider ollama --model llama3.1

# One-shot mode
cb live "list all python files in src/" --provider anthropic
```

### Explore the codebase (no LLM needed)

```bash
# Render the workspace summary
cb summary

# List mirrored commands and tools
cb commands --limit 10
cb tools --limit 10

# Route a prompt to matching commands/tools
cb route "read the readme file"

# Run verification tests
python3 -m unittest discover -s tests -v
```

### Open the interactive dashboard

```bash
open dashboard.html
# Or just double-click dashboard.html in your file browser
```

---

## Interactive Chat (REPL)

<a name="live-mode"></a>

The `cb chat` command starts an interactive session with streaming output, colored tool execution, and slash commands:

```
╔══════════════════════════════════════════╗
║          CoderBhaiya CLI v0.1.0          ║
╚══════════════════════════════════════════╝

  Provider: anthropic
  Model:    claude-sonnet-4-20250514

> read the README.md and summarize it

  [Read] /path/to/README.md
    1  # CoderBhaiya
    2  ...

  This project is an AI agent harness that...

> /model gpt-4o
  Switched to anthropic/gpt-4o

> /provider ollama
  Switched to ollama/llama3.1

> /help
> /clear
> /exit
```

### REPL Slash Commands

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/config` | Show current configuration |
| `/config set KEY VALUE` | Update a config value |
| `/model NAME` | Switch model for this session |
| `/provider NAME` | Switch provider for this session |
| `/skill NAME` | Load a skill for this session |
| `/clear` | Clear conversation history |
| `/exit` | Exit (or Ctrl+C) |

---

## One-Shot Mode

For non-interactive use, `cb live` runs a single prompt:

```bash
# Anthropic
cb live "list all python files in src/" --provider anthropic

# OpenAI
cb live "read README.md and summarize it" --provider openai --model gpt-4o

# Gemini
cb live "find all dataclass definitions" --provider gemini

# Ollama (local, free — no API key)
cb live "what files are in this project?" --provider ollama --model llama3.1

# LMStudio (local, free — no API key)
cb live "explain the project structure" --provider lmstudio
```

| Flag | Default | Description |
|------|---------|-------------|
| `--provider` | `anthropic` | LLM provider |
| `--model` | provider default | Model name |
| `--skill` | none | Skill to inject into system prompt |
| `--max-turns` | `15` | Max turn loop iterations |
| `--max-budget` | `100000` | Max total tokens |

---

## Server Mode (IDE Integration)

For VS Code extensions or other editors, `cb server` runs a JSON-over-stdin/stdout protocol:

```bash
cb server
```

**Protocol:**

```jsonc
// → Send to stdin:
{"type": "prompt", "text": "read README.md", "provider": "anthropic"}
{"type": "config", "key": "model", "value": "gpt-4o"}
{"type": "shutdown"}

// ← Receive from stdout:
{"type": "ready", "provider": "anthropic", "model": "claude-sonnet-4-20250514"}
{"type": "session_start", "prompt": "read README.md"}
{"type": "turn_start", "turn": 1}
{"type": "tool_call", "name": "Read", "input": {"file_path": "README.md"}}
{"type": "tool_result", "name": "Read", "output": "# CoderBhaiya..."}
{"type": "text", "content": "The README contains..."}
{"type": "session_end", "turns": 1, "usage": {"input_tokens": 500, "output_tokens": 200}}
```

This makes it easy to build IDE plugins — just spawn `cb server` as a subprocess and communicate via JSON lines.

---

<a name="providers"></a>

## Supported Providers

| Provider | SDK Required | Default Model | Local? |
|----------|-------------|---------------|--------|
| **Anthropic** | `pip install anthropic` | claude-sonnet-4-20250514 | No |
| **OpenAI** | `pip install openai` | gpt-4o | No |
| **Gemini** | `pip install google-generativeai` | gemini-2.0-flash | No |
| **Ollama** | None (stdlib only) | llama3.1 | Yes |
| **LMStudio** | None (stdlib only) | local-model | Yes |

Ollama and LMStudio use pure `urllib.request` — zero external dependencies.

---

## Project Structure

```
src/
  llm/                          # Multi-provider LLM client
    base.py                     # BaseLLMClient ABC
    types.py                    # LLMMessage, ToolCall, LLMResponse, Usage
    anthropic_client.py         # Anthropic adapter
    openai_client.py            # OpenAI adapter
    gemini_client.py            # Google Gemini adapter
    ollama_client.py            # Ollama (localhost, no SDK)
    lmstudio_client.py          # LMStudio (localhost, no SDK)
    registry.py                 # build_llm_client() factory

  live_tools/                   # Real tool implementations
    base.py                     # BaseTool ABC + ToolDefinition
    read_tool.py                # Read files with line numbers
    write_tool.py               # Write/create files
    edit_tool.py                # String-replace edits
    bash_tool.py                # Shell command execution
    grep_tool.py                # Regex search (rg fallback to re)
    glob_tool.py                # File pattern matching
    agent_tool.py               # Agent sub-spawning
    registry.py                 # build_live_tool_registry()

  hooks_lifecycle/              # Hook system
    types.py                    # HookEvent enum, HookContext
    registry.py                 # HookRegistry (register + fire)
    shell_hook.py               # Shell command hooks
    loader.py                   # Load hooks from settings

  skill_system/                 # Skill loading + injection
    types.py                    # Skill, SkillMeta
    loader.py                   # SkillLoader (YAML frontmatter)
    injector.py                 # System prompt injection

  cli_app/                      # CLI application layer
    config.py                   # ~/.coderbhaiya/config.json management
    repl.py                     # Interactive REPL with streaming
    streaming.py                # Terminal renderer (colors, badges, tool summaries)
    server.py                   # JSON-over-stdin/stdout server for IDEs

  turn_loop.py                  # TurnLoopRunner (core agent loop)
  runtime.py                    # PortRuntime orchestrator
  main.py                       # CLI entrypoint (chat, config, server, live, ...)

  # Harness infrastructure (routing, registry, bootstrap)
  commands.py                   # Command registry (150+ entries)
  tools.py                      # Tool registry (100+ entries)
  context.py                    # Workspace context builder
  setup.py                      # Environment setup/prefetch
  query_engine.py               # Query engine with turn management
  session_store.py              # Session persistence
  permissions.py                # Tool permission gating
  ...

tests/                          # Test suite
dashboard.html                  # Interactive D3.js codebase explorer
```

---

## How It Works

### The Turn Loop

```
1. User sends prompt
2. LLM receives: system prompt + messages + tool definitions
3. LLM responds with text OR tool_use requests
4. If tool_use:
   a. Fire PRE_TOOL_EXECUTION hook (can cancel)
   b. Execute the tool (Read/Write/Edit/Bash/Grep/Glob/Agent)
   c. Fire POST_TOOL_EXECUTION hook (can modify output)
   d. Send tool results back to LLM
   e. Go to step 3
5. If text (end_turn): return final output
6. Check budget — stop if tokens exhausted
```

### Agent Sub-Spawning

When the LLM calls the `Agent` tool, a new `TurnLoopRunner` is created with:
- Its own tool registry (all tools **except** Agent — no infinite recursion)
- Its own token budget (50K default, deducted from parent)
- Its own conversation history

The sub-agent runs independently and returns a compressed result to the parent.

### Hooks

Register hooks that fire at key lifecycle points:

```python
from src.hooks_lifecycle.registry import HookRegistry
from src.hooks_lifecycle.types import HookEvent

registry = HookRegistry()
registry.register(HookEvent.PRE_TOOL_EXECUTION, "logger", my_handler)
registry.register(HookEvent.POST_TOOL_EXECUTION, "modifier", my_handler)
```

Shell hooks can be configured in `~/.claude/settings.json`:
```json
{
  "hooks": [
    {
      "event": "PRE_TOOL_EXECUTION",
      "command": "echo 'Tool about to run' >> /tmp/hook.log"
    }
  ]
}
```

### Skills

Drop a Markdown file in `~/.claude/skills/` or `./skills/`:

```markdown
---
name: python-expert
description: Expert Python coding assistant
tags: python, coding
---

You are an expert Python developer. Follow PEP 8, use type hints,
write comprehensive docstrings, and prefer dataclasses over dicts.
```

Then use it:
```bash
python3 -m src.main live "refactor this module" --skill python-expert
```

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `OPENAI_API_KEY` | OpenAI API key |
| `GOOGLE_API_KEY` | Google/Gemini API key |
| `CLAW_PROVIDER` | Default provider (overrides `--provider`) |
| `CLAW_MODEL` | Default model (overrides `--model`) |
| `OLLAMA_BASE_URL` | Ollama server URL (default: `http://localhost:11434`) |
| `LMSTUDIO_BASE_URL` | LMStudio server URL (default: `http://localhost:1234`) |

---

## Credits

Built on top of the [claw-code](https://github.com/instructkr/claw-code) Python harness by [@instructkr](https://github.com/instructkr). The live agent system (multi-provider LLM, real tools, hooks, skills, agent sub-spawning, turn loop, and interactive dashboard) was designed and implemented as an extension to the original mirrored harness architecture.

---

## License

This project follows the same license terms as the upstream repository.
