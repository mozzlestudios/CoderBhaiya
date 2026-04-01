"""Anthropic (Claude) LLM adapter."""
from __future__ import annotations
import os
from typing import Iterator
from .base import BaseLLMClient
from .types import LLMMessage, LLMResponse, ToolCall, Usage


class AnthropicClient(BaseLLMClient):
    provider = 'anthropic'

    def __init__(self, model: str = 'claude-sonnet-4-20250514', api_key: str | None = None) -> None:
        self.model = model
        self._api_key = api_key or os.environ.get('ANTHROPIC_API_KEY', '')

        try:
            import anthropic
            self._client = anthropic.Anthropic(api_key=self._api_key)
        except ImportError:
            raise ImportError(
                'anthropic package required. Install with: pip install anthropic'
            )

    def send(self, messages, system_prompt='', tool_definitions=(), max_tokens=4096) -> LLMResponse:
        kwargs = {
            'model': self.model,
            'max_tokens': max_tokens,
            'messages': self._format_messages(messages),
        }
        if system_prompt:
            kwargs['system'] = system_prompt
        if tool_definitions:
            kwargs['tools'] = [self._format_tool(t) for t in tool_definitions]

        response = self._client.messages.create(**kwargs)
        return self._parse_response(response)

    def stream(self, messages, system_prompt='', tool_definitions=(), max_tokens=4096) -> Iterator[dict]:
        kwargs = {
            'model': self.model,
            'max_tokens': max_tokens,
            'messages': self._format_messages(messages),
        }
        if system_prompt:
            kwargs['system'] = system_prompt
        if tool_definitions:
            kwargs['tools'] = [self._format_tool(t) for t in tool_definitions]

        with self._client.messages.stream(**kwargs) as stream:
            for event in stream:
                yield {'type': 'stream_event', 'event': str(event)}

    def _format_messages(self, messages: list[LLMMessage]) -> list[dict]:
        result = []
        for msg in messages:
            if isinstance(msg.content, str):
                result.append({'role': msg.role if msg.role != 'tool' else 'user', 'content': msg.content})
            else:
                blocks = []
                for block in msg.content:
                    if block.type == 'tool_use' and block.tool_call:
                        blocks.append({
                            'type': 'tool_use',
                            'id': block.tool_call.id,
                            'name': block.tool_call.name,
                            'input': block.tool_call.input,
                        })
                    elif block.type == 'tool_result' and block.tool_result:
                        blocks.append({
                            'type': 'tool_result',
                            'tool_use_id': block.tool_result.tool_use_id,
                            'content': block.tool_result.content,
                            'is_error': block.tool_result.is_error,
                        })
                    elif block.type == 'text' and block.text:
                        blocks.append({'type': 'text', 'text': block.text})
                result.append({'role': msg.role if msg.role != 'tool' else 'user', 'content': blocks})
        return result

    def _format_tool(self, tool_def: dict) -> dict:
        return {
            'name': tool_def['name'],
            'description': tool_def.get('description', ''),
            'input_schema': tool_def.get('input_schema', {'type': 'object', 'properties': {}}),
        }

    def _parse_response(self, response) -> LLMResponse:
        text_parts = []
        tool_calls = []

        for block in response.content:
            if block.type == 'text':
                text_parts.append(block.text)
            elif block.type == 'tool_use':
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    input=block.input,
                ))

        return LLMResponse(
            content='\n'.join(text_parts) if text_parts else None,
            tool_calls=tuple(tool_calls),
            stop_reason='tool_use' if tool_calls else 'end_turn',
            usage=Usage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            ),
            model=response.model,
        )
