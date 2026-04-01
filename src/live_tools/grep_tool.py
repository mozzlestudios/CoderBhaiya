"""Grep tool — searches file contents with regex."""
from __future__ import annotations
import re
import subprocess
import shutil
from pathlib import Path
from .base import BaseTool, ToolDefinition


class GrepTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name='Grep',
            description='Search file contents using regex. Returns matching lines with file paths and line numbers.',
            input_schema={
                'type': 'object',
                'properties': {
                    'pattern': {'type': 'string', 'description': 'Regex pattern to search for'},
                    'path': {'type': 'string', 'description': 'Directory or file to search in', 'default': '.'},
                    'glob': {'type': 'string', 'description': 'Glob pattern to filter files (e.g. "*.py")'},
                    'max_results': {'type': 'integer', 'description': 'Max matches to return', 'default': 50},
                },
                'required': ['pattern'],
            },
        )

    def execute(self, input: dict[str, object]) -> str:
        pattern = str(input['pattern'])
        search_path = str(input.get('path', '.'))
        file_glob = input.get('glob')
        max_results = int(input.get('max_results', 50))

        # Try ripgrep first (much faster)
        if shutil.which('rg'):
            return self._rg_search(pattern, search_path, file_glob, max_results)

        # Fallback to pure Python
        return self._py_search(pattern, search_path, file_glob, max_results)

    def _rg_search(self, pattern: str, path: str, file_glob: str | None, max_results: int) -> str:
        cmd = ['rg', '--no-heading', '--line-number', '--max-count', str(max_results), pattern, path]
        if file_glob:
            cmd.extend(['--glob', file_glob])
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.stdout:
                lines = result.stdout.strip().splitlines()[:max_results]
                return '\n'.join(lines)
            return 'No matches found.'
        except Exception as e:
            return f'Error: {e}'

    def _py_search(self, pattern: str, path: str, file_glob: str | None, max_results: int) -> str:
        try:
            regex = re.compile(pattern)
        except re.error as e:
            return f'Error: Invalid regex: {e}'

        root = Path(path)
        if root.is_file():
            files = [root]
        else:
            glob_pat = file_glob or '**/*'
            files = sorted(f for f in root.glob(glob_pat) if f.is_file())

        matches = []
        for fpath in files:
            try:
                text = fpath.read_text(encoding='utf-8', errors='replace')
                for i, line in enumerate(text.splitlines(), 1):
                    if regex.search(line):
                        matches.append(f'{fpath}:{i}:{line}')
                        if len(matches) >= max_results:
                            break
            except (PermissionError, OSError):
                continue
            if len(matches) >= max_results:
                break

        return '\n'.join(matches) if matches else 'No matches found.'
