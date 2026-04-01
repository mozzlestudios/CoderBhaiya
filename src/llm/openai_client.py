"""OpenAI (GPT-4, etc.) LLM adapter."""
from __future__ import annotations
import json
import os
from typing import Iterator
from .base import BaseLLMClient
from .types import LLMMessage, LLMResponse, ToolCall, Usage


class OpenAIClient(BaseLLMClient):
    provider = 'openai'

    def __init__(self, model: str = 'gpt-4o', api_key: str | None = None, base_url: str | None = None) -> None:
        self.model = model
        self._api_key = api_key or os.environ.get('OPENAI_API_KEY', '')

        try:
            import openai
            kwargs = {'api_key': self._api_key}
            if base_url:
                kwargs['base_url'] = base_url
            self._client = openai.OpenAI(**kwargs)
        except ImportError:
            raise ImportError('openai package required. Install with: pip install openai')

    def send(self, messages, system_prompt='', tool_definitions=(), max_tokens=4096) -> LLMResponse:
        oai_messages = self._format_messages(messages, system_prompt)

        kwargs = {
            'model': self.model,
            'messages': oai_messages,
            'max_tokens': max_tokens,
        }
        if tool_definitions:
            kwargs['tools'] = [self._format_tool(t) for t in tool_definitions]

        response = self._client.chat.completions.create(**kwargs)
        return self._parse_response(response)

    def stream(self, messages, system_prompt='', tool_definitions=(), max_tokens=4096) -> Iterator[dict]:
        oai_messages = self._format_messages(messages, system_prompt)
        kwargs = {
            'model': self.model,
            'messages': oai_messages,
            'max_tokens': max_tokens,
            'stream': True,
        }
        if tool_definitions:
            kwargs['tools'] = [self._format_tool(t) for t in tool_definitions]

        for chunk in self._client.chat.completions.create(**kwargs):
            if chunk.choices and chunk.choices[0].delta.content:
                yield {'type': 'text_delta', 'content': chunk.choices[0].delta.content}

    def _format_messages(self, messages: list[LLMMessage], system_prompt: str = '') -> list[dict]:
        result = []
        if system_prompt:
            result.append({'role': 'system', 'content': system_prompt})

        for msg in messages:
            if isinstance(msg.content, str):
                role = 'user' if msg.role == 'user' else 'assistant'
                result.append({'role': role, 'content': msg.content})
            else:
                for block in msg.content:
                    if block.type == 'tool_use' and block.tool_call:
                        result.append({
                            'role': 'assistant',
                            'content': None,
                            'tool_calls': [{
                                'id': block.tool_call.id,
                                'type': 'function',
                                'function': {
                                    'name': block.tool_call.name,
                                    'arguments': json.dumps(block.tool_call.input),
                                },
                            }],
                        })
                    elif block.type == 'tool_result' and block.tool_result:
                        result.append({
                            'role': 'tool',
                            'tool_call_id': block.tool_result.tool_use_id,
                            'content': block.tool_result.content,
                        })
        return result

    def _format_tool(self, tool_def: dict) -> dict:
        return {
            'type': 'function',
            'function': {
                'name': tool_def['name'],
                'description': tool_def.get('description', ''),
                'parameters': tool_def.get('input_schema', {'type': 'object', 'properties': {}}),
            },
        }

    def _parse_response(self, response) -> LLMResponse:
        choice = response.choices[0]
        text = choice.message.content
        tool_calls = []

        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    input=args,
                ))

        usage = Usage()
        if response.usage:
            usage = Usage(
                input_tokens=response.usage.prompt_tokens or 0,
                output_tokens=response.usage.completion_tokens or 0,
            )

        return LLMResponse(
            content=text,
            tool_calls=tuple(tool_calls),
            stop_reason='tool_use' if tool_calls else 'end_turn',
            usage=usage,
            model=response.model or self.model,
        )
