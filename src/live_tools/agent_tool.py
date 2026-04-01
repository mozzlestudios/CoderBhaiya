"""Agent tool — spawns a sub-agent with its own turn loop.

The sub-agent gets all tools EXCEPT Agent (no recursion).
It runs a full turn loop independently and returns a compressed result.
"""
from __future__ import annotations
from typing import Callable
from .base import BaseTool, ToolDefinition


class AgentTool(BaseTool):
    """Spawns a sub-conversation with a separate turn loop and tool set."""

    def __init__(
        self,
        llm_client,  # BaseLLMClient — not typed to avoid circular import
        tool_registry_factory: Callable[[], dict[str, BaseTool]],
        hook_registry=None,  # HookRegistry | None
        max_turns: int = 15,
        max_budget_tokens: int = 50_000,
    ) -> None:
        self._llm = llm_client
        self._tool_factory = tool_registry_factory
        self._hooks = hook_registry
        self._max_turns = max_turns
        self._max_budget = max_budget_tokens

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name='Agent',
            description=(
                'Launch a sub-agent to handle a complex, multi-step task autonomously. '
                'The sub-agent gets access to Read, Write, Edit, Bash, Grep, Glob tools '
                'but cannot spawn further agents. Use for tasks that require multiple '
                'tool calls or deep investigation.'
            ),
            input_schema={
                'type': 'object',
                'properties': {
                    'prompt': {
                        'type': 'string',
                        'description': 'The task for the sub-agent to perform',
                    },
                },
                'required': ['prompt'],
            },
        )

    def execute(self, input: dict[str, object]) -> str:
        # Import here to avoid circular dependency
        from ..turn_loop import TurnLoopRunner, TurnLoopConfig

        prompt = str(input.get('prompt', ''))
        if not prompt:
            return 'Error: prompt is required'

        # Build sub-agent tools: everything EXCEPT Agent (no recursion)
        all_tools = self._tool_factory()
        sub_tools = {name: tool for name, tool in all_tools.items() if name != 'Agent'}

        config = TurnLoopConfig(
            max_turns=self._max_turns,
            max_budget_tokens=self._max_budget,
            system_prompt=(
                'You are a sub-agent handling a specific task. '
                'Use the available tools to complete the task thoroughly, '
                'then provide a clear summary of what you found or did.'
            ),
        )

        runner = TurnLoopRunner(
            llm=self._llm,
            tools=sub_tools,
            config=config,
            hook_registry=self._hooks,
        )

        result = runner.run(prompt)
        return self._compress_result(result)

    def _compress_result(self, result) -> str:
        """Compress the sub-agent's result into a concise string."""
        lines = [result.final_output]
        lines.append('')
        lines.append(
            f'[Sub-agent: {result.turns_used} turns, '
            f'{result.total_usage.total_tokens} tokens, '
            f'stop={result.stop_reason}]'
        )
        if result.tool_calls_made:
            lines.append(f'[Tools used: {", ".join(result.tool_calls_made)}]')
        return '\n'.join(lines)
