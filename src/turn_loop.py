"""TurnLoopRunner — the core agent loop that wires LLM + tools together.

This is the 'engine' that:
1. Sends the user prompt + tool definitions to an LLM
2. If the LLM responds with tool_use, executes the tools
3. Sends tool results back to the LLM
4. Repeats until the LLM says 'end_turn' or limits are hit
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Iterator

from .llm.types import LLMMessage, LLMResponse, ToolCall, ToolResult, Usage
from .llm.base import BaseLLMClient
from .live_tools.base import BaseTool
from .hooks_lifecycle.types import HookEvent, HookContext
from .hooks_lifecycle.registry import HookRegistry


@dataclass(frozen=True)
class TurnLoopConfig:
    max_turns: int = 15
    max_tokens_per_response: int = 4096
    max_budget_tokens: int = 100_000
    system_prompt: str = ''


@dataclass(frozen=True)
class TurnLoopResult:
    final_output: str
    turns_used: int
    total_usage: Usage
    stop_reason: str  # 'end_turn', 'max_turns', 'max_budget', 'error'
    tool_calls_made: tuple[str, ...] = ()  # names of tools called


class TurnLoopRunner:
    """Runs the agentic turn loop: LLM <-> tool execution."""

    def __init__(
        self,
        llm: BaseLLMClient,
        tools: dict[str, BaseTool],
        config: TurnLoopConfig | None = None,
        hook_registry: HookRegistry | None = None,
    ) -> None:
        self.llm = llm
        self.tools = tools
        self.config = config or TurnLoopConfig()
        self.hooks = hook_registry or HookRegistry()

    def _build_tool_definitions(self) -> tuple[dict[str, object], ...]:
        """Convert BaseTool instances to JSON schema dicts for the LLM."""
        defs = []
        for tool in self.tools.values():
            defn = tool.definition()
            defs.append({
                'name': defn.name,
                'description': defn.description,
                'input_schema': defn.input_schema,
            })
        return tuple(defs)

    def run(self, prompt: str) -> TurnLoopResult:
        """Run the full turn loop for a prompt. Returns when done."""
        messages: list[LLMMessage] = [LLMMessage.user(prompt)]
        tool_defs = self._build_tool_definitions()
        total_usage = Usage()
        all_tool_calls: list[str] = []
        turns = 0

        # Fire session start hook
        self.hooks.fire(HookEvent.SESSION_START, HookContext(
            event=HookEvent.SESSION_START,
            data={'prompt': prompt, 'provider': self.llm.provider, 'model': self.llm.model},
        ))

        while turns < self.config.max_turns:
            turns += 1

            # Fire turn start hook
            self.hooks.fire(HookEvent.TURN_START, HookContext(
                event=HookEvent.TURN_START,
                data={'turn': turns, 'message_count': len(messages)},
            ))

            # Call LLM
            try:
                response = self.llm.send(
                    messages=messages,
                    system_prompt=self.config.system_prompt,
                    tool_definitions=tool_defs,
                    max_tokens=self.config.max_tokens_per_response,
                )
            except Exception as e:
                return TurnLoopResult(
                    final_output=f'LLM error: {e}',
                    turns_used=turns,
                    total_usage=total_usage,
                    stop_reason='error',
                    tool_calls_made=tuple(all_tool_calls),
                )

            # Accumulate usage
            total_usage = total_usage.add(response.usage)

            # Check budget
            if total_usage.total_tokens >= self.config.max_budget_tokens:
                text = response.content or ''
                return TurnLoopResult(
                    final_output=text,
                    turns_used=turns,
                    total_usage=total_usage,
                    stop_reason='max_budget',
                    tool_calls_made=tuple(all_tool_calls),
                )

            # If LLM returned text (end_turn), we're done
            if response.stop_reason == 'end_turn' or not response.has_tool_calls:
                text = response.content or ''

                # Fire turn end + session end hooks
                self.hooks.fire(HookEvent.TURN_END, HookContext(
                    event=HookEvent.TURN_END,
                    data={'turn': turns, 'output': text},
                ))
                self.hooks.fire(HookEvent.SESSION_END, HookContext(
                    event=HookEvent.SESSION_END,
                    data={'turns': turns, 'usage': {'input': total_usage.input_tokens, 'output': total_usage.output_tokens}},
                ))

                return TurnLoopResult(
                    final_output=text,
                    turns_used=turns,
                    total_usage=total_usage,
                    stop_reason='end_turn',
                    tool_calls_made=tuple(all_tool_calls),
                )

            # LLM wants to use tools — append assistant message with tool calls
            messages.append(LLMMessage.assistant_tool_calls(list(response.tool_calls)))

            # Execute each tool
            tool_results = []
            for tc in response.tool_calls:
                all_tool_calls.append(tc.name)
                result_content = self._execute_tool(tc)
                tool_results.append(ToolResult(
                    tool_use_id=tc.id,
                    content=result_content,
                ))

            # Append tool results
            messages.append(LLMMessage.tool_results(tool_results))

            # Fire turn end hook
            self.hooks.fire(HookEvent.TURN_END, HookContext(
                event=HookEvent.TURN_END,
                data={'turn': turns, 'tool_calls': [tc.name for tc in response.tool_calls]},
            ))

        # Max turns reached
        self.hooks.fire(HookEvent.SESSION_END, HookContext(
            event=HookEvent.SESSION_END,
            data={'turns': turns, 'stop_reason': 'max_turns'},
        ))

        return TurnLoopResult(
            final_output='[Max turns reached]',
            turns_used=turns,
            total_usage=total_usage,
            stop_reason='max_turns',
            tool_calls_made=tuple(all_tool_calls),
        )

    def _execute_tool(self, tool_call: ToolCall) -> str:
        """Execute a single tool call with hook support."""
        tool = self.tools.get(tool_call.name)
        if tool is None:
            return f'Error: Unknown tool "{tool_call.name}". Available: {", ".join(self.tools.keys())}'

        # Fire pre-execution hook
        pre_ctx = self.hooks.fire(HookEvent.PRE_TOOL_EXECUTION, HookContext(
            event=HookEvent.PRE_TOOL_EXECUTION,
            data={'tool_name': tool_call.name, 'input': tool_call.input},
        ))

        if pre_ctx.cancelled:
            return f'Tool execution blocked by hook: {pre_ctx.cancel_reason}'

        # Use potentially modified input from hooks
        tool_input = pre_ctx.data.get('input', tool_call.input)

        # Execute
        try:
            result = tool.execute(tool_input)
        except Exception as e:
            result = f'Error executing {tool_call.name}: {e}'

        # Fire post-execution hook
        post_ctx = self.hooks.fire(HookEvent.POST_TOOL_EXECUTION, HookContext(
            event=HookEvent.POST_TOOL_EXECUTION,
            data={'tool_name': tool_call.name, 'input': tool_input, 'output': result},
        ))

        # Use potentially modified output from hooks
        return str(post_ctx.data.get('output', result))

    def stream_run(self, prompt: str) -> Iterator[dict[str, object]]:
        """Streaming version — yields events as the loop progresses."""
        messages: list[LLMMessage] = [LLMMessage.user(prompt)]
        tool_defs = self._build_tool_definitions()
        total_usage = Usage()
        turns = 0

        yield {'type': 'session_start', 'prompt': prompt}

        while turns < self.config.max_turns:
            turns += 1
            yield {'type': 'turn_start', 'turn': turns}

            try:
                response = self.llm.send(
                    messages=messages,
                    system_prompt=self.config.system_prompt,
                    tool_definitions=tool_defs,
                    max_tokens=self.config.max_tokens_per_response,
                )
            except Exception as e:
                yield {'type': 'error', 'error': str(e)}
                return

            total_usage = total_usage.add(response.usage)

            if response.stop_reason == 'end_turn' or not response.has_tool_calls:
                yield {'type': 'text', 'content': response.content or ''}
                yield {'type': 'session_end', 'turns': turns, 'usage': total_usage}
                return

            # Tool use
            messages.append(LLMMessage.assistant_tool_calls(list(response.tool_calls)))
            tool_results = []
            for tc in response.tool_calls:
                yield {'type': 'tool_call', 'name': tc.name, 'input': tc.input}
                result_content = self._execute_tool(tc)
                yield {'type': 'tool_result', 'name': tc.name, 'output': result_content[:500]}
                tool_results.append(ToolResult(tool_use_id=tc.id, content=result_content))

            messages.append(LLMMessage.tool_results(tool_results))

        yield {'type': 'max_turns', 'turns': turns}
