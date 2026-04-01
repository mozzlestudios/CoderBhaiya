"""Skill system types."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SkillMeta:
    """Lightweight skill metadata for listing."""
    name: str
    description: str
    source_path: Path


@dataclass(frozen=True)
class Skill:
    """A loaded skill with full instructions."""
    name: str
    description: str
    instructions: str  # The markdown body after frontmatter
    source_path: Path
    tags: tuple[str, ...] = ()
