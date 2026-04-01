"""Edit tool — performs string replacement in files."""
from __future__ import annotations
from pathlib import Path
from .base import BaseTool, ToolDefinition


class EditTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name='Edit',
            description='Edit a file by replacing an exact string with new text. The old_string must be unique in the file.',
            input_schema={
                'type': 'object',
                'properties': {
                    'file_path': {'type': 'string', 'description': 'Absolute path to the file'},
                    'old_string': {'type': 'string', 'description': 'The exact text to find and replace'},
                    'new_string': {'type': 'string', 'description': 'The replacement text'},
                },
                'required': ['file_path', 'old_string', 'new_string'],
            },
        )

    def execute(self, input: dict[str, object]) -> str:
        path = Path(str(input['file_path']))
        old = str(input['old_string'])
        new = str(input['new_string'])

        if not path.exists():
            return f'Error: File not found: {path}'

        try:
            content = path.read_text(encoding='utf-8')
        except Exception as e:
            return f'Error reading file: {e}'

        count = content.count(old)
        if count == 0:
            return f'Error: old_string not found in {path}'
        if count > 1:
            return f'Error: old_string found {count} times in {path}. Must be unique. Provide more context.'

        updated = content.replace(old, new, 1)
        try:
            path.write_text(updated, encoding='utf-8')
        except Exception as e:
            return f'Error writing file: {e}'

        old_lines = len(old.splitlines())
        new_lines = len(new.splitlines())
        return f'Successfully edited {path}: replaced {old_lines} lines with {new_lines} lines'
