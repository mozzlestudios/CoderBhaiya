"""Skill loader — finds and parses skill markdown files."""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
from .types import Skill, SkillMeta


class SkillLoader:
    """Loads skills from markdown files in search paths.

    Skill files have YAML-like frontmatter between --- delimiters:
        ---
        name: commit
        description: Create a well-structured git commit
        tags: git, workflow
        ---
        # Instructions
        When the user asks to commit...
    """

    def __init__(self, search_paths: tuple[Path, ...] | None = None) -> None:
        if search_paths is None:
            search_paths = (
                Path.home() / '.claude' / 'skills',
                Path.cwd() / 'skills',
            )
        self.search_paths = search_paths

    def list_skills(self) -> tuple[SkillMeta, ...]:
        """Find all available skills across search paths."""
        skills = []
        seen = set()
        for search_dir in self.search_paths:
            if not search_dir.is_dir():
                continue
            for path in sorted(search_dir.glob('*.md')):
                name = path.stem
                if name in seen:
                    continue
                seen.add(name)
                meta = self._parse_frontmatter_only(path)
                if meta:
                    skills.append(meta)
        return tuple(skills)

    def load_skill(self, name: str) -> Skill | None:
        """Load a skill by name from search paths."""
        for search_dir in self.search_paths:
            path = search_dir / f'{name}.md'
            if path.exists():
                return self._parse_skill_file(path)
        return None

    def _parse_skill_file(self, path: Path) -> Skill | None:
        """Parse a skill markdown file with frontmatter."""
        try:
            text = path.read_text(encoding='utf-8')
        except OSError:
            return None

        frontmatter, body = self._split_frontmatter(text)
        if frontmatter is None:
            # No frontmatter — use filename as name, entire file as instructions
            return Skill(
                name=path.stem,
                description='',
                instructions=text.strip(),
                source_path=path,
            )

        props = self._parse_yaml_simple(frontmatter)
        tags_str = props.get('tags', '')
        tags = tuple(t.strip() for t in tags_str.split(',') if t.strip()) if tags_str else ()

        return Skill(
            name=props.get('name', path.stem),
            description=props.get('description', ''),
            instructions=body.strip(),
            source_path=path,
            tags=tags,
        )

    def _parse_frontmatter_only(self, path: Path) -> SkillMeta | None:
        """Quick parse — only reads frontmatter, skips body."""
        try:
            text = path.read_text(encoding='utf-8')
        except OSError:
            return None

        frontmatter, _ = self._split_frontmatter(text)
        if frontmatter is None:
            return SkillMeta(name=path.stem, description='', source_path=path)

        props = self._parse_yaml_simple(frontmatter)
        return SkillMeta(
            name=props.get('name', path.stem),
            description=props.get('description', ''),
            source_path=path,
        )

    @staticmethod
    def _split_frontmatter(text: str) -> tuple[str | None, str]:
        """Split text into frontmatter and body. Returns (None, text) if no frontmatter."""
        if not text.startswith('---'):
            return None, text
        parts = text.split('---', 2)
        if len(parts) < 3:
            return None, text
        return parts[1].strip(), parts[2]

    @staticmethod
    def _parse_yaml_simple(text: str) -> dict[str, str]:
        """Parse simple key: value YAML (stdlib only, no pyyaml dependency)."""
        result = {}
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if ':' in line:
                key, _, value = line.partition(':')
                result[key.strip()] = value.strip()
        return result
