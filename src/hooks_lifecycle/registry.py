"""Hook registry — manages lifecycle callback registration and firing."""
from __future__ import annotations
from typing import Callable
from .types import HookEvent, HookContext

HookHandler = Callable[[HookContext], HookContext]


class HookRegistry:
    """Registry of lifecycle hooks. Handlers fire in registration order."""

    def __init__(self) -> None:
        self._hooks: dict[HookEvent, list[tuple[str, HookHandler]]] = {
            event: [] for event in HookEvent
        }

    def register(self, event: HookEvent, name: str, handler: HookHandler) -> None:
        """Register a hook handler for a lifecycle event."""
        self._hooks[event].append((name, handler))

    def fire(self, event: HookEvent, context: HookContext) -> HookContext:
        """Fire all handlers for an event. Stops if context.cancelled becomes True."""
        for name, handler in self._hooks[event]:
            try:
                context = handler(context)
            except Exception as e:
                # Hooks should not crash the harness
                context.data.setdefault('hook_errors', [])
                context.data['hook_errors'].append(f'{name}: {e}')
            if context.cancelled:
                break
        return context

    def handler_count(self, event: HookEvent) -> int:
        return len(self._hooks[event])

    @property
    def total_handlers(self) -> int:
        return sum(len(handlers) for handlers in self._hooks.values())
