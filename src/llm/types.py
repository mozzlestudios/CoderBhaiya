"""Unified LLM message types shared across all providers."""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0

    def add(self, other: Usage) -> Usage:
        return Usage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
        )

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass(frozen=True)
class ToolCall:
    """A tool invocation requested by the LLM."""
    id: str
    name: str
    input: dict[str, object]


@dataclass(frozen=True)
class ToolResult:
    """The result of executing a tool, sent back to the LLM."""
    tool_use_id: str
    content: str
    is_error: bool = False


@dataclass(frozen=True)
class ContentBlock:
    """A single block of content in an LLM message."""
    type: str  # 'text', 'tool_use', 'tool_result'
    text: str | None = None
    tool_call: ToolCall | None = None
    tool_result: ToolResult | None = None


@dataclass(frozen=True)
class LLMMessage:
    """A message in the conversation history."""
    role: str  # 'user', 'assistant', 'tool'
    content: str | tuple[ContentBlock, ...]

    @staticmethod
    def user(text: str) -> LLMMessage:
        return LLMMessage(role='user', content=text)

    @staticmethod
    def assistant_text(text: str) -> LLMMessage:
        return LLMMessage(role='assistant', content=text)

    @staticmethod
    def assistant_tool_calls(tool_calls: list[ToolCall]) -> LLMMessage:
        blocks = tuple(
            ContentBlock(type='tool_use', tool_call=tc) for tc in tool_calls
        )
        return LLMMessage(role='assistant', content=blocks)

    @staticmethod
    def tool_results(results: list[ToolResult]) -> LLMMessage:
        blocks = tuple(
            ContentBlock(type='tool_result', tool_result=tr) for tr in results
        )
        return LLMMessage(role='tool', content=blocks)


@dataclass(frozen=True)
class LLMResponse:
    """Response from an LLM provider, normalized to a common format."""
    content: str | None
    tool_calls: tuple[ToolCall, ...]
    stop_reason: str  # 'end_turn', 'tool_use', 'max_tokens'
    usage: Usage
    model: str = ''

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0
