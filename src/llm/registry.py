"""LLM client factory — builds the right client for a provider."""
from __future__ import annotations
import os
from functools import lru_cache
from .base import BaseLLMClient

# Default models per provider
DEFAULT_MODELS = {
    'anthropic': 'claude-sonnet-4-20250514',
    'openai': 'o3',
    'gemini': 'gemini-2.5-flash',
    'ollama': 'llama3.1',
    'lmstudio': 'local-model',
}

PROVIDERS = ('anthropic', 'openai', 'gemini', 'ollama', 'lmstudio')


def build_llm_client(
    provider: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
) -> BaseLLMClient:
    """Build an LLM client for the specified provider.

    Args:
        provider: One of 'anthropic', 'openai', 'gemini', 'ollama', 'lmstudio'.
                  Defaults to CLAW_PROVIDER env var, or 'anthropic'.
        model: Model name. Defaults to CLAW_MODEL env var, or provider default.
        base_url: Base URL override (useful for Ollama/LMStudio on non-default ports).

    Returns:
        Configured BaseLLMClient instance.

    Raises:
        ValueError: If provider is not recognized.
        ImportError: If required SDK is not installed (for anthropic/openai/gemini).
        ConnectionError: If local server is not reachable (for ollama/lmstudio).
    """
    provider = provider or os.environ.get('CLAW_PROVIDER', 'anthropic')
    model = model or os.environ.get('CLAW_MODEL') or DEFAULT_MODELS.get(provider, '')

    if provider == 'anthropic':
        from .anthropic_client import AnthropicClient
        return AnthropicClient(model=model)

    elif provider == 'openai':
        from .openai_client import OpenAIClient
        kwargs = {'model': model}
        if base_url:
            kwargs['base_url'] = base_url
        return OpenAIClient(**kwargs)

    elif provider == 'gemini':
        from .gemini_client import GeminiClient
        return GeminiClient(model=model)

    elif provider == 'ollama':
        from .ollama_client import OllamaClient
        url = base_url or os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')
        return OllamaClient(model=model, base_url=url)

    elif provider == 'lmstudio':
        from .lmstudio_client import LMStudioClient
        url = base_url or os.environ.get('LMSTUDIO_BASE_URL', 'http://localhost:1234')
        return LMStudioClient(model=model, base_url=url)

    else:
        raise ValueError(
            f'Unknown provider: {provider!r}. '
            f'Available: {", ".join(PROVIDERS)}'
        )
