"""Interactive REPL for CoderBhaiya.

Provides a readline-enabled chat interface with streaming output,
slash commands, conversation history, and session persistence.
"""
from __future__ import annotations

import os
import sys
import readline
from dataclasses import asdict

from .config import Config, load_config, save_config, set_config_value, history_path
from .streaming import (
    Colors, render_stream_event, render_welcome, render_help,
)


def run_repl(
    provider: str | None = None,
    model: str | None = None,
    skill_name: str | None = None,
    max_turns: int | None = None,
    max_budget: int | None = None,
) -> int:
    """Run the interactive REPL. Returns exit code."""
    config = load_config()

    # CLI flags override config
    if provider:
        config.provider = provider
    if model:
        config.model = model
    if skill_name:
        config.default_skill = skill_name
    if max_turns is not None:
        config.max_turns = max_turns
    if max_budget is not None:
        config.max_budget = max_budget

    # Apply config to environment so LLM clients pick up API keys
    for k, v in config.to_env().items():
        os.environ.setdefault(k, v)

    # Setup readline history
    hist_path = history_path()
    try:
        readline.read_history_file(str(hist_path))
    except FileNotFoundError:
        pass
    readline.set_history_length(1000)

    # Lazy imports — only load LLM/tools when entering the REPL
    from ..llm.registry import build_llm_client
    from ..live_tools.registry import build_live_tool_registry
    from ..hooks_lifecycle.loader import build_hook_registry
    from ..skill_system.loader import SkillLoader
    from ..skill_system.injector import inject_skill_into_system_prompt
    from ..system_init import build_system_init_message
    from ..turn_loop import TurnLoopRunner, TurnLoopConfig
    from ..llm.types import LLMMessage, Usage

    # Build components
    effective_model = config.effective_model()

    try:
        llm = build_llm_client(provider=config.provider, model=effective_model)
    except (ImportError, ConnectionError, ValueError) as e:
        print(f'\n{Colors.RED}Error initializing LLM: {e}{Colors.RESET}')
        print(f'{Colors.DIM}Run "cb config set provider <name>" and "cb config set api_key <key>" to configure.{Colors.RESET}\n')
        return 1

    hook_registry = build_hook_registry()
    tools = build_live_tool_registry(llm_client=llm, hook_registry=hook_registry)

    # Build system prompt (with optional skill injection)
    system_prompt = build_system_init_message(trusted=True)
    if config.default_skill:
        loader = SkillLoader()
        skill = loader.load_skill(config.default_skill)
        if skill:
            system_prompt = inject_skill_into_system_prompt(system_prompt, skill)

    render_welcome(config.provider, effective_model)

    # Conversation state — persists across turns within the REPL session
    conversation: list[LLMMessage] = []
    session_usage = Usage()
    turn_count = 0

    while True:
        try:
            prompt = input(f'{Colors.GREEN}{Colors.BOLD}> {Colors.RESET}').strip()
        except (EOFError, KeyboardInterrupt):
            print(f'\n{Colors.DIM}Goodbye!{Colors.RESET}')
            break

        if not prompt:
            continue

        # Save readline history
        try:
            readline.write_history_file(str(hist_path))
        except OSError:
            pass

        # Handle slash commands
        if prompt.startswith('/'):
            handled = _handle_slash_command(
                prompt, config, llm, effective_model,
            )
            if handled == 'exit':
                break
            if handled == 'clear':
                conversation.clear()
                session_usage = Usage()
                turn_count = 0
                print(f'{Colors.DIM}Conversation cleared.{Colors.RESET}\n')
                continue
            if handled == 'reload':
                # Rebuild LLM client after provider/model change
                effective_model = config.effective_model()
                try:
                    llm = build_llm_client(provider=config.provider, model=effective_model)
                    tools = build_live_tool_registry(llm_client=llm, hook_registry=hook_registry)
                    print(f'{Colors.GREEN}Switched to {config.provider}/{effective_model}{Colors.RESET}\n')
                except (ImportError, ConnectionError, ValueError) as e:
                    print(f'{Colors.RED}Error: {e}{Colors.RESET}\n')
                continue
            if handled:
                continue

        # Build the runner for this turn
        loop_config = TurnLoopConfig(
            max_turns=config.max_turns,
            max_budget_tokens=config.max_budget,
            system_prompt=system_prompt,
        )
        runner = TurnLoopRunner(
            llm=llm,
            tools=tools,
            config=loop_config,
            hook_registry=hook_registry,
        )

        # Stream the response
        try:
            for event in runner.stream_run(prompt):
                render_stream_event(event)
                # Track usage from session_end event
                if event.get('type') == 'session_end':
                    usage = event.get('usage')
                    if usage and hasattr(usage, 'add'):
                        session_usage = session_usage.add(usage)
                    turn_count += event.get('turns', 0)
        except KeyboardInterrupt:
            print(f'\n{Colors.YELLOW}Interrupted.{Colors.RESET}\n')
            continue

    # Final summary
    print(f'\n{Colors.DIM}Session: {turn_count} turns, {session_usage.total_tokens:,} tokens{Colors.RESET}')
    return 0


def _handle_slash_command(
    prompt: str,
    config: Config,
    llm: object,
    effective_model: str,
) -> str | None:
    """Handle a slash command. Returns 'exit', 'clear', 'reload', True (handled), or None (not a command)."""
    parts = prompt.split(None, 2)
    cmd = parts[0].lower()

    if cmd in ('/exit', '/quit', '/q'):
        print(f'{Colors.DIM}Goodbye!{Colors.RESET}')
        return 'exit'

    if cmd == '/help':
        render_help()
        return True

    if cmd == '/clear':
        return 'clear'

    if cmd == '/config':
        if len(parts) >= 3 and parts[1].lower() == 'set':
            # /config set key value
            rest = prompt.split(None, 3)
            if len(rest) >= 4:
                key, value = rest[2], rest[3]
                try:
                    path = set_config_value(key, value)
                    # Update in-memory config too
                    current = getattr(config, key, None)
                    if isinstance(current, int):
                        value = int(value)
                    object.__setattr__(config, key, value)
                    print(f'{Colors.GREEN}Set {key} = {value}{Colors.RESET}')
                    print(f'{Colors.DIM}Saved to {path}{Colors.RESET}\n')
                    # Signal reload if provider/model changed
                    if key in ('provider', 'model', 'api_key'):
                        return 'reload'
                except (KeyError, ValueError) as e:
                    print(f'{Colors.RED}{e}{Colors.RESET}\n')
            else:
                print(f'{Colors.DIM}Usage: /config set <key> <value>{Colors.RESET}\n')
            return True
        else:
            # Show current config
            from dataclasses import asdict
            print(f'\n{Colors.BOLD}Current Configuration:{Colors.RESET}')
            for k, v in asdict(config).items():
                display = '***' if k == 'api_key' and v else v
                print(f'  {Colors.CYAN}{k}{Colors.RESET} = {display}')
            print()
            return True

    if cmd == '/model':
        if len(parts) >= 2:
            config.model = parts[1]
            return 'reload'
        else:
            print(f'{Colors.DIM}Current model: {effective_model}{Colors.RESET}')
            print(f'{Colors.DIM}Usage: /model <name>{Colors.RESET}\n')
            return True

    if cmd == '/provider':
        if len(parts) >= 2:
            config.provider = parts[1]
            return 'reload'
        else:
            print(f'{Colors.DIM}Current provider: {config.provider}{Colors.RESET}')
            print(f'{Colors.DIM}Usage: /provider <name>{Colors.RESET}\n')
            return True

    if cmd == '/skill':
        if len(parts) >= 2:
            config.default_skill = parts[1]
            print(f'{Colors.GREEN}Skill set to: {parts[1]}{Colors.RESET}')
            print(f'{Colors.DIM}Will be applied on next message.{Colors.RESET}\n')
            return True
        else:
            print(f'{Colors.DIM}Current skill: {config.default_skill or "(none)"}{Colors.RESET}')
            print(f'{Colors.DIM}Usage: /skill <name>{Colors.RESET}\n')
            return True

    # Unknown slash command
    print(f'{Colors.DIM}Unknown command: {cmd}. Type /help for available commands.{Colors.RESET}\n')
    return True
