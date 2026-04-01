"""Google Gemini LLM adapter."""
from __future__ import annotations
import os
from typing import Iterator
from .base import BaseLLMClient
from .types import LLMMessage, LLMResponse, ToolCall, Usage


class GeminiClient(BaseLLMClient):
    provider = 'gemini'

    def __init__(self, model: str = 'gemini-2.5-flash', api_key: str | None = None) -> None:
        self.model = model
        self._api_key = api_key or os.environ.get('GOOGLE_API_KEY', '') or os.environ.get('GEMINI_API_KEY', '')

        try:
            import google.generativeai as genai
            genai.configure(api_key=self._api_key)
            self._genai = genai
            self._model_instance = genai.GenerativeModel(self.model)
        except ImportError:
            raise ImportError(
                'google-generativeai package required. Install with: pip install google-generativeai'
            )

    def send(self, messages, system_prompt='', tool_definitions=(), max_tokens=4096) -> LLMResponse:
        tools = [self._format_tool(t) for t in tool_definitions] if tool_definitions else None

        # Build config
        config = {'max_output_tokens': max_tokens}
        if system_prompt:
            config['system_instruction'] = system_prompt

        model = self._genai.GenerativeModel(
            self.model,
            tools=tools,
            system_instruction=system_prompt if system_prompt else None,
        )

        contents = self._format_messages(messages)
        response = model.generate_content(
            contents,
            generation_config={'max_output_tokens': max_tokens},
        )

        return self._parse_response(response)

    def stream(self, messages, system_prompt='', tool_definitions=(), max_tokens=4096) -> Iterator[dict]:
        tools = [self._format_tool(t) for t in tool_definitions] if tool_definitions else None
        model = self._genai.GenerativeModel(
            self.model,
            tools=tools,
            system_instruction=system_prompt if system_prompt else None,
        )
        contents = self._format_messages(messages)
        response = model.generate_content(contents, stream=True)
        for chunk in response:
            if chunk.text:
                yield {'type': 'text_delta', 'content': chunk.text}

    def _format_messages(self, messages: list[LLMMessage]) -> list[dict]:
        contents = []
        for msg in messages:
            if isinstance(msg.content, str):
                role = 'user' if msg.role in ('user', 'tool') else 'model'
                contents.append({'role': role, 'parts': [{'text': msg.content}]})
            else:
                parts = []
                role = 'model'
                for block in msg.content:
                    if block.type == 'tool_use' and block.tool_call:
                        role = 'model'
                        parts.append({
                            'function_call': {
                                'name': block.tool_call.name,
                                'args': block.tool_call.input,
                            }
                        })
                    elif block.type == 'tool_result' and block.tool_result:
                        role = 'user'
                        parts.append({
                            'function_response': {
                                'name': 'tool',
                                'response': {'result': block.tool_result.content},
                            }
                        })
                if parts:
                    contents.append({'role': role, 'parts': parts})
        return contents

    def _format_tool(self, tool_def: dict) -> dict:
        """Convert to Gemini function declaration format."""
        schema = tool_def.get('input_schema', {})
        # Gemini uses a slightly different schema format
        properties = schema.get('properties', {})
        required = schema.get('required', [])

        return {
            'function_declarations': [{
                'name': tool_def['name'],
                'description': tool_def.get('description', ''),
                'parameters': {
                    'type': 'OBJECT',
                    'properties': {
                        k: {'type': v.get('type', 'STRING').upper(), 'description': v.get('description', '')}
                        for k, v in properties.items()
                    },
                    'required': required,
                },
            }],
        }

    def _parse_response(self, response) -> LLMResponse:
        text_parts = []
        tool_calls = []

        for candidate in response.candidates:
            for part in candidate.content.parts:
                if hasattr(part, 'text') and part.text:
                    text_parts.append(part.text)
                if hasattr(part, 'function_call') and part.function_call:
                    fc = part.function_call
                    tool_calls.append(ToolCall(
                        id=f'call_{fc.name}',
                        name=fc.name,
                        input=dict(fc.args) if fc.args else {},
                    ))

        # Gemini doesn't always provide token counts directly
        usage = Usage(
            input_tokens=getattr(response, 'usage_metadata', None) and response.usage_metadata.prompt_token_count or 0,
            output_tokens=getattr(response, 'usage_metadata', None) and response.usage_metadata.candidates_token_count or 0,
        )

        return LLMResponse(
            content='\n'.join(text_parts) if text_parts else None,
            tool_calls=tuple(tool_calls),
            stop_reason='tool_use' if tool_calls else 'end_turn',
            usage=usage,
            model=self.model,
        )
