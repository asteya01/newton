"""Provider layer — the one place that knows how to talk to Claude, OpenAI-compatible APIs and Ollama."""
from __future__ import annotations

import json
import re
import socket
import urllib.error
import urllib.request
from typing import Any, Dict, Iterator, List, Optional, Tuple

from newton import __version__


class NewtonError(Exception):
    """A user-facing error with a helpful message."""


Message = Dict[str, str]


# ----------------------------------------------------------------------------- HTTP

def _http_error(e: urllib.error.HTTPError) -> NewtonError:
    body = e.read().decode(errors="replace")
    try:
        msg = json.loads(body).get("error", {})
        msg = msg.get("message", body) if isinstance(msg, dict) else str(msg)
    except ValueError:
        msg = body[:200]
    if e.code in (401, 403):
        return NewtonError(f"API key was rejected ({e.code}). Run `newton setup` to update it.")
    if e.code == 429:
        return NewtonError("Rate limited by the API — wait a moment and try again.")
    if e.code == 400 and "credit" in str(msg).lower():
        return NewtonError("Your API account is out of credit. Add funds at console.anthropic.com.")
    return NewtonError(f"API error {e.code}: {msg}")


def _request(url: str, payload: Dict[str, Any], headers: Dict[str, str], timeout: float):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST", headers={
        "content-type": "application/json", "user-agent": f"newton-cli/{__version__}", **headers})
    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        raise _http_error(e) from None
    except urllib.error.URLError as e:
        raise NewtonError(f"Can't reach {url.split('/')[2]} ({e.reason}). Check your connection or `newton doctor`.") from None
    except (TimeoutError, socket.timeout):
        raise NewtonError("The AI took too long to answer. Try again, or raise `timeout` in your config.") from None


def _build(cfg: Dict[str, Any], system: str, messages: List[Message], max_tokens: int,
           stream: bool, smart: bool, json_mode: bool) -> Tuple[str, Dict[str, Any], Dict[str, str]]:
    provider, base, key = cfg["provider"], cfg["base_url"], cfg["api_key"]
    model = (cfg.get("smart_model") if smart else "") or cfg["model"]
    if provider in ("anthropic", "openai") and not key:
        from newton import config as cfgmod
        raise NewtonError(f"No API key configured. Run `newton setup` or export {cfgmod.PROVIDERS[provider]['key_env']}.")

    if provider == "anthropic":
        payload: Dict[str, Any] = {"model": model, "max_tokens": max_tokens, "system": system, "messages": messages}
        if stream:
            payload["stream"] = True
        return f"{base}/v1/messages", payload, {"x-api-key": key, "anthropic-version": "2023-06-01"}

    full = [{"role": "system", "content": system}] + messages
    if provider == "openai":
        payload = {"model": model, "max_tokens": max_tokens, "temperature": 0, "messages": full}
        if stream:
            payload["stream"] = True
        return f"{base}/chat/completions", payload, {"authorization": f"Bearer {key}"}

    if provider == "ollama":
        payload = {"model": model, "stream": bool(stream), "options": {"temperature": 0}, "messages": full}
        if json_mode and not stream:
            payload["format"] = "json"
        return f"{base}/api/chat", payload, {}

    raise NewtonError(f"Unknown provider: {provider}")


# ----------------------------------------------------------------------------- public API

def complete(cfg: Dict[str, Any], system: str, messages: List[Message], max_tokens: int = 500, *,
             smart: bool = False, json_mode: bool = False, timeout: Optional[float] = None) -> str:
    url, payload, headers = _build(cfg, system, messages, max_tokens, False, smart, json_mode)
    try:
        with _request(url, payload, headers, timeout or float(cfg["timeout"])) as r:
            res = json.loads(r.read().decode())
    except (TimeoutError, socket.timeout):
        raise NewtonError("The AI took too long to answer. Try again, or raise `timeout` in your config.") from None
    except ValueError:
        raise NewtonError("The AI returned an unreadable response. Try again.") from None

    provider = cfg["provider"]
    if provider == "anthropic":
        return "".join(b.get("text", "") for b in res.get("content", []) if b.get("type") == "text")
    if provider == "openai":
        return res["choices"][0]["message"]["content"]
    return res.get("message", {}).get("content", "")


def stream(cfg: Dict[str, Any], system: str, messages: List[Message], max_tokens: int = 1800, *,
           smart: bool = True, timeout: Optional[float] = None) -> Iterator[str]:
    """Yields text as it is generated."""
    url, payload, headers = _build(cfg, system, messages, max_tokens, True, smart, False)
    provider = cfg["provider"]
    r = _request(url, payload, headers, timeout or max(float(cfg["timeout"]), 45.0))
    try:
        for raw in r:
            line = raw.decode("utf-8", "replace").strip()
            if not line:
                continue
            if provider == "ollama":
                obj = json.loads(line)
                piece = obj.get("message", {}).get("content", "")
                if piece:
                    yield piece
                if obj.get("done"):
                    break
                continue
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                obj = json.loads(data)
            except ValueError:
                continue
            if provider == "anthropic":
                kind = obj.get("type")
                if kind == "content_block_delta" and obj.get("delta", {}).get("type") == "text_delta":
                    yield obj["delta"].get("text", "")
                elif kind == "error":
                    raise NewtonError(obj.get("error", {}).get("message", "The AI stopped mid-answer."))
                elif kind == "message_stop":
                    break
            else:
                choices = obj.get("choices") or [{}]
                piece = (choices[0].get("delta") or {}).get("content")
                if piece:
                    yield piece
    except (TimeoutError, socket.timeout, ConnectionError):
        raise NewtonError("The connection dropped mid-answer. Try again.") from None
    finally:
        r.close()


_BAD_ESCAPE = re.compile(r'\\(?!["\\/bfnrtu])')
_TRAILING_COMMA = re.compile(r",\s*([}\]])")


def parse_json(text: str) -> Dict[str, Any]:
    """Parses a JSON object out of a model reply, repairing the slips small models make:
    code fences, prose around the object, trailing commas, and invalid escapes such as `\\;` in `find -exec`."""
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise NewtonError("The AI returned an unexpected answer. Try rephrasing.")
    body = text[start:end + 1]
    for attempt in (body, _TRAILING_COMMA.sub(r"\1", _BAD_ESCAPE.sub(r"\\\\", body))):
        try:
            data = json.loads(attempt)
        except ValueError:
            continue
        if isinstance(data, dict):
            return data
    raise NewtonError("The AI returned malformed JSON. Try again.")