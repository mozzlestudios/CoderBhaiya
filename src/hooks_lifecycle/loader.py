"""Hook registry loader — builds HookRegistry from settings."""
from __future__ import annotations
import json
from pathlib import Path
from .types import HookEvent
from .registry import HookRegistry
from .shell_hook import ShellHookHandler


def build_hook_registry(settings_path: Path | None = None) -> HookRegistry:
    """Build a HookRegistry from a settings JSON file.

    Expected format in settings JSON:
    {
      "hooks": {
        "pre_tool_execution": [
          {"name": "audit_log", "command": "echo $HOOK_DATA >> /tmp/audit.log"}
        ],
        "post_tool_execution": [...],
        ...
      }
    }
    """
    registry = HookRegistry()

    if settings_path is None:
        candidates = [
            Path.home() / '.claude' / 'settings.json',
            Path.cwd() / '.claude' / 'settings.json',
        ]
        for candidate in candidates:
            if candidate.exists():
                settings_path = candidate
                break

    if settings_path is None or not settings_path.exists():
        return registry

    try:
        data = json.loads(settings_path.read_text())
    except (json.JSONDecodeError, OSError):
        return registry

    hooks_config = data.get('hooks', {})

    for event in HookEvent:
        event_hooks = hooks_config.get(event.value, [])
        for hook_def in event_hooks:
            name = hook_def.get('name', 'unnamed')
            command = hook_def.get('command', '')
            timeout = hook_def.get('timeout', 10)
            if command:
                handler = ShellHookHandler(command=command, timeout=timeout)
                registry.register(event, name, handler)

    return registry
