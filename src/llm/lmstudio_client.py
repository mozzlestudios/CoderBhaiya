"""LMStudio LLM adapter — uses OpenAI-compatible API, pure stdlib.

Connects to LMStudio's local server at localhost:1234.
"""
from __future__ import annotations
import json
import urllib.request
import urllib.error
from typing import Iterator
from .base import BaseLLMClient
from .types import LLMMessage, LLMResponse, ToolCall, Usage


class LMStudioClient(BaseLLMClient):
    """LMStudio adapter using OpenAI-compatible REST API (no SDK required)."""
    provider = 'lmstudio'

    def __init__(self, model: str = 'local-model', base_url: str = 'http://localhost:1234') -> None:
        self.model = model
        self.base_url = base_url.rstrip('/')

    def send(self, messages, system_prompt='', tool_definitions=(), max_tokens=4096) -> LLMResponse:
        payload = {
            'model': self.model,
            'messages': self._format_messages(messages, system_prompt),
            'max_tokens': max_tokens,
            'stream': False,
        }
        if tool_definitions:
            payload['tools'] = [self._format_tool(t) for t in tool_definitions]

        data = self._post('/v1/chat/completions', payload)
        return self._parse_response(data)

    def stream(self, messages, system_prompt='', tool_definitions=(), max_tokens=4096) -> Iterator[dict]:
        payload = {
            'model': self.model,
            'messages': self._format_messages(messages, system_prompt),
            'max_tokens': max_tokens,
            'stream': True,
        }
        if tool_definitions:
            payload['tools'] = [self._format_tool(t) for t in tool_definitions]

        req = urllib.request.Request(
            f'{self.base_url}/v1/chat/completions',
            data=json.dumps(payload).encode(),
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            for line in resp:
                line = line.decode().strip()
                if line.startswith('data: ') and line != 'data: [DONE]':
                    chunk = json.loads(line[6:])
                    delta = chunk.get('choices', [{}])[0].get('delta', {})
                    if delta.get('content'):
                        yield {'type': 'text_delta', 'content': delta['content']}

    def _post(self, path: str, payload: dict) -> dict:
        req = urllib.request.Request(
            f'{self.base_url}{path}',
            data=json.dumps(payload).encode(),
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                return json.loads(resp.read())
        except urllib.error.URLError as e:
            raise ConnectionError(
                f'Cannot connect to LMStudio at {self.base_url}. '
                f'Is LMStudio running with API server enabled? Error: {e}'
            )

    def _format_messages(self, messages: list[LLMMessage], system_prompt: str = '') -> list[dict]:
        result = []
        if system_prompt:
            result.append({'role': 'system', 'content': system_prompt})
        for msg in messages:
            if isinstance(msg.content, str):
                result.append({'role': msg.role if msg.role != 'tool' else 'user', 'content': msg.content})
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

    def _parse_response(self, data: dict) -> LLMResponse:
        choice = data.get('choices', [{}])[0]
        msg = choice.get('message', {})
        text = msg.get('content')
        tool_calls = []

        for tc in msg.get('tool_calls', []):
            fn = tc.get('function', {})
            args = fn.get('arguments', '{}')
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            tool_calls.append(ToolCall(
                id=tc.get('id', f'call_{fn.get("name", "unknown")}'),
                name=fn.get('name', ''),
                input=args,
            ))

        usage_data = data.get('usage', {})
        usage = Usage(
            input_tokens=usage_data.get('prompt_tokens', 0),
            output_tokens=usage_data.get('completion_tokens', 0),
        )

        return LLMResponse(
            content=text,
            tool_calls=tuple(tool_calls),
            stop_reason='tool_use' if tool_calls else 'end_turn',
            usage=usage,
            model=data.get('model', self.model),
        )
