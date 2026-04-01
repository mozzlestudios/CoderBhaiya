"""Terminal streaming renderer for CoderBhaiya.

Renders turn loop events as colored, formatted terminal output with
real-time streaming of LLM text and tool execution status.
"""
from __future__ import annotations

import sys
import shutil
from typing import Iterator


# ANSI color codes
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    ITALIC = '\033[3m'

    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'

    BG_BLACK = '\033[40m'
    BG_BLUE = '\033[44m'


def _term_width() -> int:
    return shutil.get_terminal_size((80, 24)).columns


def _hrule(char: str = '─') -> str:
    return char * min(_term_width(), 80)


def _badge(label: str, color: str = Colors.BLUE) -> str:
    return f'{color}{Colors.BOLD}[{label}]{Colors.RESET}'


def render_stream_event(event: dict) -> None:
    """Render a single stream event to the terminal."""
    etype = event.get('type', '')

    if etype == 'session_start':
        prompt = event.get('prompt', '')
        print(f'\n{Colors.CYAN}{_hrule("═")}{Colors.RESET}')
        print(f'{_badge("CoderBhaiya", Colors.CYAN)} Starting session...')
        print(f'{Colors.DIM}Prompt: {prompt[:100]}{"..." if len(prompt) > 100 else ""}{Colors.RESET}')
        print(f'{Colors.CYAN}{_hrule("─")}{Colors.RESET}\n')

    elif etype == 'turn_start':
        turn = event.get('turn', '?')
        print(f'{_badge(f"Turn {turn}", Colors.MAGENTA)}')

    elif etype == 'text':
        content = event.get('content', '')
        if content:
            print(f'\n{content}\n')

    elif etype == 'text_delta':
        # Real-time streaming — write without newline
        content = event.get('content', '')
        sys.stdout.write(content)
        sys.stdout.flush()

    elif etype == 'tool_call':
        name = event.get('name', '?')
        tool_input = event.get('input', {})
        print(f'\n  {_badge(name, Colors.YELLOW)} ', end='')
        # Show a compact summary of the input
        _print_tool_input_summary(name, tool_input)

    elif etype == 'tool_result':
        name = event.get('name', '?')
        output = event.get('output', '')
        lines = output.strip().split('\n')
        if len(lines) <= 5:
            for line in lines:
                print(f'  {Colors.DIM}  {line}{Colors.RESET}')
        else:
            for line in lines[:3]:
                print(f'  {Colors.DIM}  {line}{Colors.RESET}')
            print(f'  {Colors.DIM}  ... ({len(lines) - 3} more lines){Colors.RESET}')

    elif etype == 'session_end':
        turns = event.get('turns', '?')
        usage = event.get('usage', None)
        print(f'\n{Colors.CYAN}{_hrule("─")}{Colors.RESET}')
        parts = [f'Turns: {turns}']
        if usage:
            if hasattr(usage, 'total_tokens'):
                parts.append(f'Tokens: {usage.total_tokens:,}')
            elif isinstance(usage, dict):
                total = usage.get('input_tokens', 0) + usage.get('output_tokens', 0)
                parts.append(f'Tokens: {total:,}')
        print(f'{_badge("Done", Colors.GREEN)} {" | ".join(parts)}')
        print(f'{Colors.CYAN}{_hrule("═")}{Colors.RESET}\n')

    elif etype == 'error':
        error = event.get('error', 'Unknown error')
        print(f'\n  {_badge("Error", Colors.RED)} {Colors.RED}{error}{Colors.RESET}\n')

    elif etype == 'max_turns':
        turns = event.get('turns', '?')
        print(f'\n  {_badge("Limit", Colors.YELLOW)} Max turns ({turns}) reached\n')

    elif etype == 'cancelled':
        reason = event.get('reason', '')
        print(f'\n  {_badge("Cancelled", Colors.YELLOW)} {reason}\n')


def _print_tool_input_summary(name: str, tool_input: dict) -> None:
    """Print a one-line summary of tool input based on the tool type."""
    if name == 'Read':
        path = tool_input.get('file_path', '?')
        print(f'{Colors.DIM}{path}{Colors.RESET}')
    elif name == 'Write':
        path = tool_input.get('file_path', '?')
        content = tool_input.get('content', '')
        print(f'{Colors.DIM}{path} ({len(content)} chars){Colors.RESET}')
    elif name == 'Edit':
        path = tool_input.get('file_path', '?')
        old = tool_input.get('old_string', '')[:40]
        print(f'{Colors.DIM}{path} (replace: "{old}..."){Colors.RESET}')
    elif name == 'Bash':
        cmd = tool_input.get('command', '?')
        print(f'{Colors.DIM}$ {cmd[:60]}{"..." if len(cmd) > 60 else ""}{Colors.RESET}')
    elif name == 'Grep':
        pattern = tool_input.get('pattern', '?')
        path = tool_input.get('path', '.')
        print(f'{Colors.DIM}/{pattern}/ in {path}{Colors.RESET}')
    elif name == 'Glob':
        pattern = tool_input.get('pattern', '?')
        print(f'{Colors.DIM}{pattern}{Colors.RESET}')
    elif name == 'Agent':
        prompt = tool_input.get('prompt', '?')
        print(f'{Colors.DIM}"{prompt[:50]}{"..." if len(prompt) > 50 else ""}"{Colors.RESET}')
    else:
        keys = ', '.join(f'{k}={str(v)[:20]}' for k, v in list(tool_input.items())[:3])
        print(f'{Colors.DIM}{keys}{Colors.RESET}')


def render_welcome(config_provider: str, config_model: str) -> None:
    """Print the welcome banner for interactive chat."""
    print(f"""
{Colors.CYAN}{Colors.BOLD}╔══════════════════════════════════════════╗
║          CoderBhaiya CLI v0.1.0          ║
╚══════════════════════════════════════════╝{Colors.RESET}

  Provider: {Colors.GREEN}{config_provider}{Colors.RESET}
  Model:    {Colors.GREEN}{config_model}{Colors.RESET}

  Type your message and press Enter.
  Commands: {Colors.DIM}/help  /config  /model  /clear  /exit{Colors.RESET}
""")


def render_help() -> None:
    """Print REPL help."""
    print(f"""
{Colors.BOLD}Commands:{Colors.RESET}
  {Colors.CYAN}/help{Colors.RESET}              Show this help
  {Colors.CYAN}/config{Colors.RESET}            Show current configuration
  {Colors.CYAN}/config set K V{Colors.RESET}    Set a config value
  {Colors.CYAN}/model NAME{Colors.RESET}        Switch model for this session
  {Colors.CYAN}/provider NAME{Colors.RESET}     Switch provider for this session
  {Colors.CYAN}/skill NAME{Colors.RESET}        Load a skill for this session
  {Colors.CYAN}/clear{Colors.RESET}             Clear conversation history
  {Colors.CYAN}/exit{Colors.RESET}              Exit the REPL (or Ctrl+C)

{Colors.BOLD}Examples:{Colors.RESET}
  {Colors.DIM}read the README.md and summarize it{Colors.RESET}
  {Colors.DIM}find all TODO comments in the codebase{Colors.RESET}
  {Colors.DIM}write a function that parses CSV files{Colors.RESET}
  {Colors.DIM}/model gpt-4o{Colors.RESET}
  {Colors.DIM}/provider ollama{Colors.RESET}
""")
