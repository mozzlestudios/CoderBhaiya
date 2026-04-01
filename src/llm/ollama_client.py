"""Ollama LLM adapter — pure stdlib, no external deps.

Connects to Ollama's REST API at localhost:11434.
"""
from __future__ import annotations
import json
import urllib.request
import urllib.error
from typing import Iterator
from .base import BaseLLMClient
from .types import LLMMessage, LLMResponse, ToolCall, Usage


class OllamaClient(BaseLLMClient):
    provider = 'ollama'

    def __init__(self, model: str = 'llama3.1', base_url: str = 'http://localhost:11434') -> None:
        self.model = model
        self.base_url = base_url.rstrip('/')

    def send(self, messages, system_prompt='', tool_definitions=(), max_tokens=4096) -> LLMResponse:
        payload = {
            'model': self.model,
            'messages': self._format_messages(messages, system_prompt),
            'stream': False,
            'options': {'num_predict': max_tokens},
        }
        if tool_definitions:
            payload['tools'] = [self._format_tool(t) for t in tool_definitions]

        data = self._post('/api/chat', payload)

        return self._parse_response(data)

    def stream(self, messages, system_prompt='', tool_definitions=(), max_tokens=4096) -> Iterator[dict]:
        payload = {
            'model': self.model,
            'messages': self._format_messages(messages, system_prompt),
            'stream': True,
            'options': {'num_predict': max_tokens},
        }
        if tool_definitions:
            payload['tools'] = [self._format_tool(t) for t in tool_definitions]

        req = urllib.request.Request(
            f'{self.base_url}/api/chat',
            data=json.dumps(payload).encode(),
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            for line in resp:
                if line.strip():
                    chunk = json.loads(line)
                    if chunk.get('message', {}).get('content'):
                        yield {'type': 'text_delta', 'content': chunk['message']['content']}

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
                f'Cannot connect to Ollama at {self.base_url}. '
                f'Is Ollama running? Error: {e}'
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
                            'content': '',
                            'tool_calls': [{
                                'function': {
                                    'name': block.tool_call.name,
                                    'arguments': block.tool_call.input,
                                },
                            }],
                        })
                    elif block.type == 'tool_result' and block.tool_result:
                        result.append({
                            'role': 'tool',
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
        msg = data.get('message', {})
        text = msg.get('content', '')
        tool_calls = []

        for tc in msg.get('tool_calls', []):
            fn = tc.get('function', {})
            tool_calls.append(ToolCall(
                id=f'call_{fn.get("name", "unknown")}',
                name=fn.get('name', ''),
                input=fn.get('arguments', {}),
            ))

        # Ollama provides eval_count and prompt_eval_count
        usage = Usage(
            input_tokens=data.get('prompt_eval_count', 0),
            output_tokens=data.get('eval_count', 0),
        )

        return LLMResponse(
            content=text if text else None,
            tool_calls=tuple(tool_calls),
            stop_reason='tool_use' if tool_calls else 'end_turn',
            usage=usage,
            model=data.get('model', self.model),
        )
