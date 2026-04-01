"""Read tool — reads files from disk."""
from __future__ import annotations
from pathlib import Path
from .base import BaseTool, ToolDefinition


class ReadTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name='Read',
            description='Read a file from disk. Returns contents with line numbers.',
            input_schema={
                'type': 'object',
                'properties': {
                    'file_path': {'type': 'string', 'description': 'Absolute path to the file'},
                    'offset': {'type': 'integer', 'description': 'Line number to start from (1-based)', 'default': 1},
                    'limit': {'type': 'integer', 'description': 'Number of lines to read', 'default': 2000},
                },
                'required': ['file_path'],
            },
        )

    def execute(self, input: dict[str, object]) -> str:
        path = Path(str(input['file_path']))
        offset = int(input.get('offset', 1))
        limit = int(input.get('limit', 2000))

        if not path.exists():
            return f'Error: File not found: {path}'
        if path.is_dir():
            return f'Error: {path} is a directory, not a file'

        try:
            text = path.read_text(encoding='utf-8', errors='replace')
        except Exception as e:
            return f'Error reading file: {e}'

        lines = text.splitlines()
        start = max(0, offset - 1)
        end = start + limit
        selected = lines[start:end]

        numbered = [f'{i + start + 1}\t{line}' for i, line in enumerate(selected)]
        return '\n'.join(numbered)
