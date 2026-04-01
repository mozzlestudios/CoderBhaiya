"""Skill injector — injects skill instructions into system prompts."""
from __future__ import annotations
from .types import Skill


def inject_skill_into_system_prompt(base_prompt: str, skill: Skill) -> str:
    """Append skill instructions to the system prompt.

    The skill content is wrapped in XML tags so the LLM can
    distinguish it from the base system prompt.
    """
    skill_block = (
        f'\n\n<skill name="{skill.name}">\n'
        f'{skill.instructions}\n'
        f'</skill>'
    )
    return base_prompt + skill_block
