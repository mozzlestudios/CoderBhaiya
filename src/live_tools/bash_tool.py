"""Bash tool — executes shell commands."""
from __future__ import annotations
import subprocess
from .base import BaseTool, ToolDefinition


class BashTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name='Bash',
            description='Execute a shell command and return stdout + stderr.',
            input_schema={
                'type': 'object',
                'properties': {
                    'command': {'type': 'string', 'description': 'The shell command to execute'},
                    'timeout': {'type': 'integer', 'description': 'Timeout in seconds', 'default': 120},
                },
                'required': ['command'],
            },
        )

    def execute(self, input: dict[str, object]) -> str:
        command = str(input['command'])
        timeout = int(input.get('timeout', 120))

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            output_parts = []
            if result.stdout:
                output_parts.append(result.stdout)
            if result.stderr:
                output_parts.append(f'STDERR:\n{result.stderr}')
            if result.returncode != 0:
                output_parts.append(f'Exit code: {result.returncode}')

            return '\n'.join(output_parts) if output_parts else '(no output)'

        except subprocess.TimeoutExpired:
            return f'Error: Command timed out after {timeout} seconds'
        except Exception as e:
            return f'Error executing command: {e}'
