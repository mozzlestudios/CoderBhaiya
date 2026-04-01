"""Configuration management for CoderBhaiya CLI.

Stores settings in ~/.coderbhaiya/config.yaml (or CODERBHAIYA_CONFIG_DIR).
"""
from __future__ import annotations

import os
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


def _config_dir() -> Path:
    """Return the config directory, creating it if needed."""
    env = os.environ.get('CODERBHAIYA_CONFIG_DIR')
    if env:
        d = Path(env)
    else:
        d = Path.home() / '.coderbhaiya'
    d.mkdir(parents=True, exist_ok=True)
    return d


def _config_path() -> Path:
    return _config_dir() / 'config.json'


def _history_path() -> Path:
    return _config_dir() / 'history'


@dataclass
class Config:
    """User-facing configuration."""
    provider: str = 'anthropic'
    model: str = ''
    api_key: str = ''
    max_turns: int = 15
    max_budget: int = 100_000
    ollama_url: str = 'http://localhost:11434'
    lmstudio_url: str = 'http://localhost:1234'
    default_skill: str = ''
    theme: str = 'default'

    def effective_model(self) -> str:
        """Return model name, falling back to provider default."""
        if self.model:
            return self.model
        from ..llm.registry import DEFAULT_MODELS
        return DEFAULT_MODELS.get(self.provider, '')

    def to_env(self) -> dict[str, str]:
        """Export config values as environment variable overrides."""
        env: dict[str, str] = {}
        if self.api_key:
            key_map = {
                'anthropic': 'ANTHROPIC_API_KEY',
                'openai': 'OPENAI_API_KEY',
                'gemini': 'GOOGLE_API_KEY',
            }
            env_var = key_map.get(self.provider)
            if env_var:
                env[env_var] = self.api_key
        if self.ollama_url != 'http://localhost:11434':
            env['OLLAMA_BASE_URL'] = self.ollama_url
        if self.lmstudio_url != 'http://localhost:1234':
            env['LMSTUDIO_BASE_URL'] = self.lmstudio_url
        return env


def load_config() -> Config:
    """Load config from disk. Returns defaults if no config file exists."""
    path = _config_path()
    if not path.exists():
        return Config()
    try:
        data = json.loads(path.read_text())
        known_fields = {f.name for f in Config.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return Config(**filtered)
    except (json.JSONDecodeError, TypeError):
        return Config()


def save_config(config: Config) -> Path:
    """Save config to disk. Returns the path written."""
    path = _config_path()
    data = asdict(config)
    # Don't persist empty strings for optional fields
    path.write_text(json.dumps(data, indent=2) + '\n')
    return path


def get_config_value(key: str) -> str:
    """Get a single config value by key name."""
    config = load_config()
    if not hasattr(config, key):
        raise KeyError(f'Unknown config key: {key!r}. Valid keys: {", ".join(asdict(config).keys())}')
    val = getattr(config, key)
    return str(val)


def set_config_value(key: str, value: str) -> Path:
    """Set a single config value by key name."""
    config = load_config()
    if not hasattr(config, key):
        raise KeyError(f'Unknown config key: {key!r}. Valid keys: {", ".join(asdict(config).keys())}')

    # Type coerce to match field type
    current = getattr(config, key)
    if isinstance(current, int):
        value = int(value)
    elif isinstance(current, bool):
        value = value.lower() in ('true', '1', 'yes')

    object.__setattr__(config, key, value)
    return save_config(config)


def history_path() -> Path:
    """Return the readline history file path."""
    return _history_path()
