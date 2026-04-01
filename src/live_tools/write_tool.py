"""Write tool — writes files to disk."""
from __future__ import annotations
from pathlib import Path
from .base import BaseTool, ToolDefinition


class WriteTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name='Write',
            description='Write content to a file. Creates parent directories if needed. Overwrites existing files.',
            input_schema={
                'type': 'object',
                'properties': {
                    'file_path': {'type': 'string', 'description': 'Absolute path to the file'},
                    'content': {'type': 'string', 'description': 'The content to write'},
                },
                'required': ['file_path', 'content'],
            },
        )

    def execute(self, input: dict[str, object]) -> str:
        path = Path(str(input['file_path']))
        content = str(input.get('content', ''))

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')
            return f'Successfully wrote {len(content)} bytes to {path}'
        except Exception as e:
            return f'Error writing file: {e}'
