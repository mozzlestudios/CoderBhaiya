"""Hook lifecycle types."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class HookEvent(str, Enum):
    """Lifecycle events that hooks can subscribe to."""
    PRE_TOOL_EXECUTION = 'pre_tool_execution'
    POST_TOOL_EXECUTION = 'post_tool_execution'
    SESSION_START = 'session_start'
    SESSION_END = 'session_end'
    TURN_START = 'turn_start'
    TURN_END = 'turn_end'
    PRE_COMPACTION = 'pre_compaction'


@dataclass
class HookContext:
    """Mutable context passed through hook handlers.

    Hooks can modify `data` to transform tool inputs/outputs.
    Setting `cancelled=True` in a PreToolExecution hook blocks the tool.
    """
    event: HookEvent
    data: dict[str, object] = field(default_factory=dict)
    cancelled: bool = False
    cancel_reason: str = ''

    def cancel(self, reason: str = '') -> None:
        self.cancelled = True
        self.cancel_reason = reason
