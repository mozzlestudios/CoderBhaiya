"""Glob tool — finds files by pattern."""
from __future__ import annotations
from pathlib import Path
from .base import BaseTool, ToolDefinition


class GlobTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name='Glob',
            description='Find files matching a glob pattern. Returns matching file paths.',
            input_schema={
                'type': 'object',
                'properties': {
                    'pattern': {'type': 'string', 'description': 'Glob pattern (e.g. "**/*.py", "src/**/*.ts")'},
                    'path': {'type': 'string', 'description': 'Base directory to search from', 'default': '.'},
                },
                'required': ['pattern'],
            },
        )

    def execute(self, input: dict[str, object]) -> str:
        pattern = str(input['pattern'])
        base = Path(str(input.get('path', '.')))

        if not base.exists():
            return f'Error: Path not found: {base}'

        try:
            matches = sorted(str(p) for p in base.glob(pattern) if p.is_file())
        except Exception as e:
            return f'Error: {e}'

        if not matches:
            return 'No files matched the pattern.'

        result = '\n'.join(matches[:200])
        if len(matches) > 200:
            result += f'\n... and {len(matches) - 200} more'
        return result
