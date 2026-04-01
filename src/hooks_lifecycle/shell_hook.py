"""Shell-based hook handler — runs a shell command on hook events."""
from __future__ import annotations
import json
import os
import subprocess
from .types import HookContext


class ShellHookHandler:
    """Hook handler that runs a shell command, passing context via env vars."""

    def __init__(self, command: str, timeout: int = 10) -> None:
        self.command = command
        self.timeout = timeout

    def __call__(self, context: HookContext) -> HookContext:
        env = os.environ.copy()
        env['HOOK_EVENT'] = context.event.value
        env['HOOK_DATA'] = json.dumps(context.data, default=str)

        try:
            result = subprocess.run(
                self.command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=env,
            )
            if result.stdout.strip():
                context.data['hook_output'] = result.stdout.strip()
        except subprocess.TimeoutExpired:
            context.data.setdefault('hook_errors', [])
            context.data['hook_errors'].append(f'Shell hook timed out: {self.command}')
        except Exception as e:
            context.data.setdefault('hook_errors', [])
            context.data['hook_errors'].append(f'Shell hook error: {e}')

        return context
