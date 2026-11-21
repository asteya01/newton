"""Configuration: ~/.config/newton/config.json, overridable with environment variables."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

PROVIDERS = {
    "anthropic": {"label": "Claude (Anthropic API)", "model": "claude-haiku-5-5", "base_url": "https://api.anthropic.com", "key_env": "ANTHROPIC_API_KEY"},
    "openai": {"label": "OpenAI-compatible API", "model": "gpt-4o-mini", "base_url": "https://api.openai.com/v1", "key_env": "OPENAI_API_KEY"},
    "ollama": {"label": "Ollama (local, offline)", "model": "llama3.1", "base_url": "http://localhost:11434", "key_env": ""},
}

DEFAULTS: Dict[str, Any] = {
    "provider": "anthropic",
    "model": "",              # empty = provider default
    "api_key": "",            # empty = read from the provider's env var
    "base_url": "",           # empty = provider default
    "alternatives": 2,        # extra suggestions you can cycle with Tab
    "share_file_names": True, # send top-level file names in cwd for better suggestions
    "cache": True,
    "timeout": 20,
    "trigger": "smart",       # smart | prefix   (prefix = only lines starting with '#')
    "smart_model": "",        # stronger model for plan / ask / fix / commit (empty = same as `model`)
    "share_output": True,     # on a failed step, send the last lines of its output to the AI for diagnosis
    "plan_timeout": 90,       # seconds to wait while the AI drafts a plan
    "plan_max_steps": 15,
    "agent_name": "",         # what the `newton agent` app calls itself (empty = Iris)
}


def config_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "newton"


def cache_dir() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "newton"


def data_dir() -> Path:
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "newton"


def ensure_private(path: Path) -> Path:
    """Creates the directory (and its parents) and makes the newton folder itself owner-only."""
    path.mkdir(parents=True, exist_ok=True)
    for d in (path, *path.parents):
        if d.name == "newton":
            try:
                os.chmod(d, 0o700)
            except OSError:
                pass
            break
    return path


def config_path() -> Path:
    return Path(os.environ.get("NEWTON_CONFIG") or config_dir() / "config.json")


def load() -> Dict[str, Any]:
    cfg = dict(DEFAULTS)
    p = config_path()
    if p.exists():
        try:
            cfg.update(json.loads(p.read_text()))
        except (OSError, ValueError):
            pass
    # Environment overrides (handy for CI, testing and one-off runs)
    for key in ("provider", "model", "smart_model", "api_key", "base_url"):
        env = os.environ.get("NEWTON_" + key.upper())
        if env:
            cfg[key] = env
    if cfg["provider"] not in PROVIDERS:
        cfg["provider"] = "anthropic"
    prov = PROVIDERS[cfg["provider"]]
    cfg["model"] = cfg["model"] or prov["model"]
    cfg["smart_model"] = cfg.get("smart_model") or cfg["model"]
    cfg["base_url"] = (cfg["base_url"] or prov["base_url"]).rstrip("/")
    if not cfg["api_key"] and prov["key_env"]:
        cfg["api_key"] = os.environ.get(prov["key_env"], "")
    return cfg


def save(patch: Dict[str, Any]) -> Path:
    p = config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    current: Dict[str, Any] = {}
    if p.exists():
        try:
            current = json.loads(p.read_text())
        except (OSError, ValueError):
            current = {}
    current.update(patch)
    p.write_text(json.dumps(current, indent=2) + "\n")
    try:
        os.chmod(p, 0o600)  # the file may hold an API key
    except OSError:
        pass
    return p
