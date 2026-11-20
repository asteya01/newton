"""Turns a plain-English description into a shell command using the configured AI provider."""
from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from newton import config as cfgmod
from newton import llm
from newton.llm import NewtonError
from newton import context as ctxmod
from newton import safety

SYSTEM_PROMPT = """You are Newton, an expert at the command line. You turn a plain-English request into the exact shell command that does it.

Reply with ONLY a JSON object, no prose and no code fences:
{"command": "...", "alternatives": ["..."], "explanation": "...", "danger": null}

Rules:
- "command": ONE line, ready to paste and run in the user's shell on the user's OS. Chain steps with && or pipes; never use line breaks.
- Match the platform: BSD flags on macOS (e.g. sed -i ''), GNU flags on Linux; the user's package manager; tools they actually have installed.
- Use the files and project context you are given (e.g. reference real file names, use npm vs pnpm correctly).
- If a value is genuinely unknown, use a short ALL-CAPS placeholder such as FILE or PORT. Never invent paths.
- For find, prefer `-exec CMD {} +` over `-exec CMD {} \\;`, and never double a backslash: the command must be exactly what is typed in the terminal.
- Prefer the simplest, most common, safest correct command. Quote paths that may contain spaces.
- "alternatives": up to {n} meaningfully different commands that also work (empty list if none are worth it).
- "explanation": what the command does, max 18 words, plain English.
- "danger": a short warning if the command deletes data, is irreversible, needs sudo, or executes downloaded code; otherwise null.
- If the input is already a shell command, return it fixed/improved.
- If the request cannot be done in a shell, set "command" to "" and say why in "explanation"."""

EXPLAIN_PROMPT = """You explain shell commands to developers. Reply with ONLY a JSON object:
{"summary": "one sentence", "parts": [{"part": "token or flag", "meaning": "what it does"}], "danger": null}
Keep each meaning under 14 words. "danger" is a short warning if the command is destructive or risky, else null."""


@dataclass
class Suggestion:
    command: str
    alternatives: List[str] = field(default_factory=list)
    explanation: str = ""
    danger: Optional[str] = None
    cached: bool = False
    elapsed_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ----------------------------------------------------------------------------- provider calls

def _complete(cfg: Dict[str, Any], system: str, user: str, max_tokens: int = 500) -> str:
    return llm.complete(cfg, system, [{"role": "user", "content": user}], max_tokens, json_mode=True)


_parse_json = llm.parse_json


_DOUBLE_ESCAPE = re.compile(r"(?<!\\)\\\\(?=[;()])")


def fix_escapes(cmd: str) -> str:
    """Small models often double-escape backslashes inside JSON, turning `find -exec ... \\;` into `\\\\;`.
    In every shell that breaks the command, so collapse a doubled backslash before ; ( )."""
    return _DOUBLE_ESCAPE.sub(lambda m: "\\", cmd)


def _one_line(cmd: str) -> str:
    cmd = fix_escapes((cmd or "").strip())
    if cmd.startswith("$ "):
        cmd = cmd[2:]
    lines = [l.strip() for l in cmd.splitlines() if l.strip()]
    return " && ".join(lines) if len(lines) > 1 else (lines[0] if lines else "")


# ----------------------------------------------------------------------------- cache & history

def _cache_file():
    return cfgmod.cache_dir() / "cache.json"


def _cache_key(desc: str, ctx: Dict[str, Any], cfg: Dict[str, Any]) -> str:
    raw = "|".join([desc.strip().lower(), str(ctx["os"]), str(ctx["shell"]), cfg["provider"], cfg["model"]])
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def _cache_get(key: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(_cache_file().read_text()).get(key)
    except (OSError, ValueError):
        return None


def _cache_put(key: str, value: Dict[str, Any]) -> None:
    path = _cache_file()
    try:
        data = json.loads(path.read_text()) if path.exists() else {}
    except (OSError, ValueError):
        data = {}
    data[key] = value
    if len(data) > 500:  # keep the newest 500
        data = dict(list(data.items())[-500:])
    cfgmod.ensure_private(path.parent)
    path.write_text(json.dumps(data))


def record_history(desc: str, s: Suggestion) -> None:
    path = cfgmod.cache_dir() / "history.jsonl"
    try:
        cfgmod.ensure_private(path.parent)
        with path.open("a") as f:
            f.write(json.dumps({"t": int(time.time()), "q": desc, "cmd": s.command}) + "\n")
    except OSError:
        pass


def read_history(limit: int = 20) -> List[Dict[str, Any]]:
    path = cfgmod.cache_dir() / "history.jsonl"
    try:
        lines = path.read_text().splitlines()[-limit:]
    except OSError:
        return []
    out = []
    for l in lines:
        try:
            out.append(json.loads(l))
        except ValueError:
            pass
    return out


# ----------------------------------------------------------------------------- public API

def suggest(description: str, shell: Optional[str] = None, cfg: Optional[Dict[str, Any]] = None, use_cache: bool = True) -> Suggestion:
    description = description.strip().lstrip("#").strip()
    if not description:
        raise NewtonError("Describe what you want to do, e.g. `find files bigger than 100MB`.")
    cfg = cfg or cfgmod.load()
    ctx = ctxmod.gather(shell, bool(cfg.get("share_file_names", True)))
    key = _cache_key(description, ctx, cfg)
    t0 = time.monotonic()

    if use_cache and cfg.get("cache", True):
        hit = _cache_get(key)
        if hit:
            s = Suggestion(**{**hit, "cached": True, "elapsed_ms": 0})
            s.command = fix_escapes(s.command)
            s.alternatives = [fix_escapes(a) for a in s.alternatives]
            return s

    n = max(0, min(5, int(cfg.get("alternatives", 2))))
    user = f"Environment:\n{ctxmod.describe(ctx)}\n\nRequest: {description}"
    data = _parse_json(_complete(cfg, SYSTEM_PROMPT.replace("{n}", str(n)), user))

    command = _one_line(str(data.get("command") or ""))
    alts = []
    for a in data.get("alternatives") or []:
        a = _one_line(str(a))
        if a and a != command and a not in alts:
            alts.append(a)
    s = Suggestion(
        command=command,
        alternatives=alts[:n],
        explanation=str(data.get("explanation") or "").strip(),
        danger=safety.summarize(command, data.get("danger") if isinstance(data.get("danger"), str) else None) if command else None,
        elapsed_ms=int((time.monotonic() - t0) * 1000),
    )
    if not s.command:
        raise NewtonError(s.explanation or "Newton couldn't turn that into a command. Try rephrasing.")
    if cfg.get("cache", True):
        _cache_put(key, {k: v for k, v in s.to_dict().items() if k not in ("cached", "elapsed_ms")})
    record_history(description, s)
    return s


def explain(command: str, cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cfg = cfg or cfgmod.load()
    ctx = ctxmod.gather(None, False)
    data = _parse_json(_complete(cfg, EXPLAIN_PROMPT, f"OS: {ctx['os']}\nShell: {ctx['shell']}\nCommand: {command}", 700))
    data["danger"] = safety.summarize(command, data.get("danger") if isinstance(data.get("danger"), str) else None)
    return data


def ping(cfg: Optional[Dict[str, Any]] = None) -> int:
    """Round-trip latency to the provider in ms (raises NewtonError on failure)."""
    cfg = cfg or cfgmod.load()
    t0 = time.monotonic()
    _complete(cfg, "Reply with the single word: ok", "ping", 5)
    return int((time.monotonic() - t0) * 1000)
