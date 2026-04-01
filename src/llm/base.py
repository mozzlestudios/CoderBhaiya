"""Abstract base class for LLM clients."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Iterator

from .types import LLMMessage, LLMResponse


class BaseLLMClient(ABC):
    """Abstract LLM client that all providers implement."""

    provider: str
    model: str

    @abstractmethod
    def send(
        self,
        messages: list[LLMMessage],
        system_prompt: str = '',
        tool_definitions: tuple[dict[str, object], ...] = (),
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Send messages and get a complete response."""
        ...

    @abstractmethod
    def stream(
        self,
        messages: list[LLMMessage],
        system_prompt: str = '',
        tool_definitions: tuple[dict[str, object], ...] = (),
        max_tokens: int = 4096,
    ) -> Iterator[dict[str, object]]:
        """Stream response events. Yields dicts with 'type' key."""
        ...

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(provider={self.provider!r}, model={self.model!r})'
