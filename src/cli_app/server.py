"""JSON server mode for CoderBhaiya.

Reads JSON requests from stdin, writes JSON events to stdout.
Designed to be spawned as a subprocess by VS Code extensions,
editor plugins, or other IDE integrations.

Protocol:
  → stdin:  {"type": "prompt", "text": "...", "provider": "...", "model": "..."}
  → stdin:  {"type": "config", "key": "...", "value": "..."}
  → stdin:  {"type": "shutdown"}

  ← stdout: {"type": "session_start", "prompt": "..."}
  ← stdout: {"type": "turn_start", "turn": 1}
  ← stdout: {"type": "tool_call", "name": "Read", "input": {...}}
  ← stdout: {"type": "tool_result", "name": "Read", "output": "..."}
  ← stdout: {"type": "text", "content": "..."}
  ← stdout: {"type": "session_end", "turns": 3, "usage": {...}}
  ← stdout: {"type": "error", "error": "..."}
  ← stdout: {"type": "ready"}
"""
from __future__ import annotations

import json
import os
import sys
from typing import TextIO

from .config import load_config


def run_server(
    input_stream: TextIO | None = None,
    output_stream: TextIO | None = None,
) -> int:
    """Run the JSON server. Returns exit code."""
    inp = input_stream or sys.stdin
    out = output_stream or sys.stdout

    config = load_config()

    # Apply config env vars
    for k, v in config.to_env().items():
        os.environ.setdefault(k, v)

    # Lazy imports
    from ..llm.registry import build_llm_client
    from ..live_tools.registry import build_live_tool_registry
    from ..hooks_lifecycle.loader import build_hook_registry
    from ..skill_system.loader import SkillLoader
    from ..skill_system.injector import inject_skill_into_system_prompt
    from ..system_init import build_system_init_message
    from ..turn_loop import TurnLoopRunner, TurnLoopConfig

    hook_registry = build_hook_registry()
    llm = None
    tools = None

    def _emit(event: dict) -> None:
        """Write a JSON event to output."""
        # Convert non-serializable objects
        serializable = {}
        for k, v in event.items():
            if hasattr(v, '__dataclass_fields__'):
                from dataclasses import asdict
                serializable[k] = asdict(v)
            else:
                serializable[k] = v
        out.write(json.dumps(serializable) + '\n')
        out.flush()

    def _ensure_llm():
        nonlocal llm, tools
        if llm is None:
            llm = build_llm_client(
                provider=config.provider,
                model=config.effective_model(),
            )
            tools = build_live_tool_registry(llm_client=llm, hook_registry=hook_registry)

    _emit({'type': 'ready', 'provider': config.provider, 'model': config.effective_model()})

    for line in inp:
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
        except json.JSONDecodeError as e:
            _emit({'type': 'error', 'error': f'Invalid JSON: {e}'})
            continue

        req_type = request.get('type', '')

        if req_type == 'shutdown':
            _emit({'type': 'shutdown_ack'})
            break

        elif req_type == 'config':
            key = request.get('key', '')
            value = request.get('value', '')
            if hasattr(config, key):
                current = getattr(config, key)
                if isinstance(current, int):
                    value = int(value)
                object.__setattr__(config, key, value)
                # Reset LLM client on provider/model change
                if key in ('provider', 'model', 'api_key'):
                    llm = None
                    tools = None
                _emit({'type': 'config_ack', 'key': key, 'value': str(value)})
            else:
                _emit({'type': 'error', 'error': f'Unknown config key: {key}'})

        elif req_type == 'prompt':
            text = request.get('text', '')
            if not text:
                _emit({'type': 'error', 'error': 'Empty prompt'})
                continue

            # Per-request overrides
            req_provider = request.get('provider', config.provider)
            req_model = request.get('model', config.effective_model())
            req_skill = request.get('skill')

            # Rebuild LLM if overrides differ
            if req_provider != config.provider or req_model != config.effective_model():
                config.provider = req_provider
                config.model = req_model
                llm = None
                tools = None

            try:
                _ensure_llm()
            except (ImportError, ConnectionError, ValueError) as e:
                _emit({'type': 'error', 'error': f'LLM init failed: {e}'})
                continue

            # System prompt
            system_prompt = build_system_init_message(trusted=True)
            if req_skill:
                loader = SkillLoader()
                skill = loader.load_skill(req_skill)
                if skill:
                    system_prompt = inject_skill_into_system_prompt(system_prompt, skill)

            loop_config = TurnLoopConfig(
                max_turns=request.get('max_turns', config.max_turns),
                max_budget_tokens=request.get('max_budget', config.max_budget),
                system_prompt=system_prompt,
            )
            runner = TurnLoopRunner(
                llm=llm,
                tools=tools,
                config=loop_config,
                hook_registry=hook_registry,
            )

            # Stream events
            try:
                for event in runner.stream_run(text):
                    # Serialize usage objects
                    if 'usage' in event and hasattr(event['usage'], 'total_tokens'):
                        from dataclasses import asdict
                        event = {**event, 'usage': asdict(event['usage'])}
                    _emit(event)
            except Exception as e:
                _emit({'type': 'error', 'error': str(e)})

        else:
            _emit({'type': 'error', 'error': f'Unknown request type: {req_type}'})

    return 0
