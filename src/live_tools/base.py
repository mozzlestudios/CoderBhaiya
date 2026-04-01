"""Base classes for live tool implementations."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ToolDefinition:
    """Schema definition for a tool that the LLM can call."""
    name: str
    description: str
    input_schema: dict[str, object]


class BaseTool(ABC):
    """Abstract base for all executable tools."""

    @abstractmethod
    def definition(self) -> ToolDefinition:
        """Return the tool's name, description, and JSON schema."""
        ...

    @abstractmethod
    def execute(self, input: dict[str, object]) -> str:
        """Execute the tool and return a string result."""
        ...

    @property
    def name(self) -> str:
        return self.definition().name
