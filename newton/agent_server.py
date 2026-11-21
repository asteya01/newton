"""The local web app for the Newton agent. It only listens on your own computer, and only answers requests that
carry a secret token, so other websites and other people on your network can't talk to it."""
from __future__ import annotations

import html as htmllib
import json
import os
import re
import secrets
import threading
import time
import uuid
import webbrowser
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

from newton import agent as agentmod
from newton import config as cfgmod

WEB = Path(__file__).resolve().parent / "web"


def read_page() -> bytes:
    """The chat page's HTML. Newton installs as a single zipped file, so it is read through the import system
    (works both from a folder and from inside the zip) rather than as a plain file path."""
    try:
        from importlib import resources
        return resources.files("newton").joinpath("web").joinpath("iris.html").read_bytes()
    except Exception:
        return (WEB / "iris.html").read_bytes()
COOKIE = "newton_agent"


class Conversation:
    def __init__(self, cfg: Dict[str, Any], cwd: str, mode: str, name: str, cid: Optional[str] = None):
        self.id = cid or uuid.uuid4().hex[:12]
        self.title = "New chat"
        self.created = self.updated = time.time()
        self.events: List[Dict[str, Any]] = []
        self.cond = threading.Condition()
        self.busy = False
        self.agent = agentmod.Agent(cfg, cwd, mode, name)

    def emit(self, ev: Dict[str, Any]) -> None:
        ev = dict(ev, t=time.time())
        with self.cond:
            ev["i"] = len(self.events)
            self.events.append(ev)
            self.updated = ev["t"]
            self.cond.notify_all()

    def to_json(self) -> Dict[str, Any]:
        return {"id": self.id, "title": self.title, "created": self.created, "updated": self.updated,
                "events": [e for e in self.events if e["type"] != "thinking"], "messages": self.agent.messages, "cwd": self.agent.shell.cwd}

    def save(self, folder: Path) -> None:
        try:
            folder.mkdir(parents=True, exist_ok=True)
            p = folder / f"{self.id}.json"
            p.write_text(json.dumps(self.to_json()))
            os.chmod(p, 0o600)
        except OSError:
            pass


class Hub:
    def __init__(self, cfg: Dict[str, Any], cwd: str, mode: str = "smart", name: str = agentmod.NAME, persist: bool = True):
        self.cfg, self.cwd, self.mode, self.name = cfg, cwd, mode if mode in agentmod.MODES else "smart", name
        self.token = secrets.token_urlsafe(24)
        self.folder = (cfgmod.data_dir() / "agent") if persist else None
        self.convs: Dict[str, Conversation] = {}
        self.lock = threading.Lock()
        if self.folder:
            self._load()

    def _load(self) -> None:
        try:
            files = sorted(self.folder.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:40]
        except OSError:
            return
        for p in files:
            try:
                d = json.loads(p.read_text())
                c = Conversation(self.cfg, d.get("cwd") or self.cwd, self.mode, self.name, d["id"])
                c.title, c.created, c.updated = d.get("title", "Chat"), d.get("created", 0), d.get("updated", 0)
                c.events = d.get("events", [])
                for i, e in enumerate(c.events):
                    e["i"] = i
                c.agent.messages = d.get("messages", [])
                self.convs[c.id] = c
            except (OSError, ValueError, KeyError):
                continue

    def new(self) -> Conversation:
        c = Conversation(self.cfg, self.cwd, self.mode, self.name)
        with self.lock:
            self.convs[c.id] = c
        return c

    def listing(self) -> List[Dict[str, Any]]:
        with self.lock:
            items = sorted(self.convs.values(), key=lambda c: c.updated, reverse=True)
        return [{"id": c.id, "title": c.title, "updated": c.updated, "busy": c.busy} for c in items if c.events or c.busy]

    def send(self, c: Conversation, text: str) -> bool:
        with c.cond:
            if c.busy:
                return False
            c.busy = True
        if c.title == "New chat":
            c.title = (re.sub(r"\s+", " ", text).strip()[:48] or "New chat")
        c.emit({"type": "user", "text": text})

        def work() -> None:
            try:
                c.agent.turn(text, c.emit)
            finally:
                c.busy = False
                c.emit({"type": "done"})
                if self.folder:
                    c.save(self.folder)
        threading.Thread(target=work, daemon=True).start()
        return True

    def delete(self, cid: str) -> None:
        with self.lock:
            c = self.convs.pop(cid, None)
        if c:
            c.agent.stop.set()
            if self.folder:
                try:
                    (self.folder / f"{c.id}.json").unlink()
                except OSError:
                    pass


def make_handler(hub: Hub, port_box: List[int]):
    class H(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        server_version = "Newton"

        def log_message(self, *a) -> None:      # keep the terminal quiet
            pass

        # -- helpers
        def _host_ok(self) -> bool:
            host = (self.headers.get("Host") or "").lower()
            return host in (f"127.0.0.1:{port_box[0]}", f"localhost:{port_box[0]}")

        def _authed(self) -> bool:
            raw = self.headers.get("Cookie") or ""
            try:
                c = SimpleCookie(raw)
            except Exception:
                return False
            return COOKIE in c and secrets.compare_digest(c[COOKIE].value, hub.token)

        def _send(self, code: int, body: bytes, ctype: str = "application/json", extra: Optional[Dict[str, str]] = None) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def _json(self, obj: Any, code: int = 200) -> None:
            self._send(code, json.dumps(obj).encode())

        def _gate(self, write: bool = False) -> bool:
            if not self._host_ok():
                self._send(403, b'{"error":"bad host"}')
                return False
            if not self._authed():
                self._send(401, b'{"error":"open Newton through the link printed in your terminal"}')
                return False
            if write:
                origin = self.headers.get("Origin")
                if origin and origin not in (f"http://127.0.0.1:{port_box[0]}", f"http://localhost:{port_box[0]}"):
                    self._send(403, b'{"error":"bad origin"}')
                    return False
                if "application/json" not in (self.headers.get("Content-Type") or ""):
                    self._send(415, b'{"error":"json only"}')
                    return False
            return True

        def _body(self) -> Dict[str, Any]:
            n = int(self.headers.get("Content-Length") or 0)
            if n > 200_000:
                return {}
            try:
                d = json.loads(self.rfile.read(n) or b"{}")
                return d if isinstance(d, dict) else {}
            except ValueError:
                return {}

        def _conv(self, cid: str) -> Optional[Conversation]:
            with hub.lock:
                return hub.convs.get(cid)

        # -- routes
        def do_GET(self) -> None:
            u = urlparse(self.path)
            if not self._host_ok():
                return self._send(403, b"bad host", "text/plain")
            if u.path == "/":
                q = parse_qs(u.query)
                tok = (q.get("t") or [""])[0]
                if tok and secrets.compare_digest(tok, hub.token):         # first visit: trade the link token for a cookie
                    return self._send(302, b"", "text/plain", {"Location": "/", "Set-Cookie": f"{COOKIE}={hub.token}; Path=/; HttpOnly; SameSite=Strict"})
                if not self._authed():
                    return self._send(401, b"Open Newton through the link printed in your terminal.", "text/plain")
                html = read_page().replace(b"__NAME__", htmllib.escape(hub.name[:30]).encode())
                return self._send(200, html, "text/html; charset=utf-8")
            if not self._gate():
                return
            if u.path == "/api/state":
                return self._json({"name": hub.name, "model": hub.cfg["model"], "provider": hub.cfg["provider"], "cwd": hub.cwd,
                                   "mode": hub.mode, "conversations": hub.listing(), "home": str(Path.home())})
            m = re.fullmatch(r"/api/conv/([a-f0-9]+)", u.path)
            if m:
                c = self._conv(m.group(1))
                return self._json({"id": c.id, "title": c.title, "busy": c.busy, "mode": c.agent.mode, "cwd": c.agent.shell.cwd,
                                   "events": [e for e in c.events if e["type"] != "thinking"]}) if c else self._json({"error": "not found"}, 404)
            m = re.fullmatch(r"/api/stream/([a-f0-9]+)", u.path)
            if m:
                c = self._conv(m.group(1))
                if not c:
                    return self._json({"error": "not found"}, 404)
                return self._stream(c, int((parse_qs(u.query).get("from") or ["0"])[0] or 0))
            self._send(404, b"not found", "text/plain")

        def _stream(self, c: Conversation, start: int) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "close")
            self.end_headers()
            i = start
            try:
                while True:
                    with c.cond:
                        while i >= len(c.events):
                            if not c.cond.wait(timeout=15):
                                break
                        batch = c.events[i:]
                    if not batch:
                        self.wfile.write(b": keepalive\n\n")
                        self.wfile.flush()
                        continue
                    for ev in batch:
                        self.wfile.write(b"data: " + json.dumps(ev).encode() + b"\n\n")
                    self.wfile.flush()
                    i += len(batch)
            except (BrokenPipeError, ConnectionResetError, OSError):
                return

        def do_POST(self) -> None:
            if not self._gate(write=True):
                return
            u, d = urlparse(self.path).path, self._body()
            if u == "/api/conv":
                c = hub.new()
                return self._json({"id": c.id})
            if u == "/api/mode":
                mode = d.get("mode")
                if mode in agentmod.MODES:
                    hub.mode = mode
                    with hub.lock:
                        for c in hub.convs.values():
                            c.agent.mode = mode
                return self._json({"mode": hub.mode})
            c = self._conv(str(d.get("conv", "")))
            if not c:
                return self._json({"error": "not found"}, 404)
            if u == "/api/send":
                text = str(d.get("text", "")).strip()[:8000]
                if not text:
                    return self._json({"error": "empty"}, 400)
                return self._json({"ok": hub.send(c, text)}) if not c.busy else self._json({"ok": False, "error": "busy"}, 409)
            if u == "/api/approve":
                return self._json({"ok": c.agent.decide(str(d.get("id", "")), bool(d.get("allow")))})
            if u == "/api/stop":
                c.agent.stop.set()
                return self._json({"ok": True})
            self._send(404, b"not found", "text/plain")

        def do_DELETE(self) -> None:
            if not self._gate(write=False):
                return
            m = re.fullmatch(r"/api/conv/([a-f0-9]+)", urlparse(self.path).path)
            if not m:
                return self._send(404, b"not found", "text/plain")
            hub.delete(m.group(1))
            self._json({"ok": True})

    return H


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def start(cfg: Dict[str, Any], cwd: str, port: int = 0, mode: str = "smart", name: str = agentmod.NAME, persist: bool = True):
    hub = Hub(cfg, cwd, mode, name, persist)
    box = [0]
    srv = Server(("127.0.0.1", port), make_handler(hub, box))
    box[0] = srv.server_address[1]
    return srv, hub


def serve(cfg: Dict[str, Any], cwd: str, port: int = 0, open_browser: bool = True, mode: str = "smart") -> int:
    from newton import ui
    name = cfg.get("agent_name") or agentmod.NAME
    try:
        srv, hub = start(cfg, cwd, port, mode, name)
    except OSError as e:
        ui.err(f"Couldn't start on port {port}: {e.strerror or e}. Try `newton agent --port 0`.")
        return 1
    url = f"http://127.0.0.1:{srv.server_address[1]}/?t={hub.token}"
    print(f"\n  {ui.lime('●')} {ui.bold(name)} {ui.grey('is running on your computer. Press Ctrl+C to stop.')}\n")
    print(f"  {ui.bold(url)}\n")
    print(ui.grey(f"  Using {cfg['provider']} · {cfg['model']}  ·  working in {cwd}\n"))
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        srv.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        print()
    finally:
        srv.server_close()
    return 0
