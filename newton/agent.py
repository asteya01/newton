"""The Newton agent: give it a goal and it works through it step by step, using your own AI.

It runs a loop: think, take one action (run a command, read a file, list a folder, write a file), look at the
result, decide the next action, and stop with a plain-language answer. Looking around (read-only commands, reading
files) happens on its own; anything that could change something waits for your approval. Dangerous commands always
ask, and secrets are redacted before anything is sent to the AI.
"""
from __future__ import annotations

import os
import re
import shlex
import signal
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from newton import brain, chat, llm, safety
from newton.llm import NewtonError
from newton.runner import PRELUDE, _ANSI

NAME = "Iris"
MAX_STEPS = 16
CMD_TIMEOUT = 90
OUT_LIMIT = 6000
MODES = ("smart", "ask")          # smart = read-only runs by itself, the rest asks.   ask = every action asks.

SYSTEM = """You are {name}, the agent inside Newton. You work on the user's computer through tools, one step at a time, to finish the task they give you.

Reply with exactly ONE JSON object and nothing else. The actions are:
{{"action":"run","command":"<one shell command or a short && pipeline>","why":"<one short sentence>"}}
{{"action":"read","path":"<file>"}}
{{"action":"list","path":"<folder>"}}
{{"action":"write","path":"<file>","content":"<the complete new content of the file>","why":"<one short sentence>"}}
{{"action":"say","message":"<your answer or a question for the user>"}}

Rules:
- Take ONE action per reply. You will be shown the result, then you choose the next action.
- Look before you change anything: inspect with read-only commands first, then act.
- Commands must be non-interactive: no editors, no prompts, use -y style flags. Each command should finish quickly.
- Never invent output. If you need information, run something to get it.
- Use "say" when you are finished, or when you must ask the user something. Keep it short, plain and friendly. Light markdown is fine (short paragraphs, `code`, fenced blocks, - bullets).
- If the user denies an action, do not try the same thing again. Offer another way or ask what they prefer.
- Stay inside what the user asked. Do not delete things, install things or change settings they didn't ask for.
- Match the user's OS and shell (see Environment). The working directory carries over between commands.

Environment:
{env}"""

# ----------------------------------------------------------------------------- what runs without asking

READ_ONLY = {
    "ls", "pwd", "cat", "head", "tail", "wc", "grep", "egrep", "fgrep", "rg", "find", "tree", "stat", "file", "which",
    "whereis", "type", "echo", "printf", "date", "uname", "whoami", "hostname", "uptime", "df", "du", "free", "ps",
    "pgrep", "id", "lsof", "sort", "uniq", "cut", "tr", "basename", "dirname", "realpath", "readlink", "sw_vers",
    "nproc", "lscpu", "cd", "true", "test", "[", "diff", "cmp", "md5sum", "shasum", "sha256sum", "column", "nl",
}
GIT_READ = {"status", "log", "diff", "show", "rev-parse", "ls-files", "blame", "describe", "shortlog", "remote",
            "branch", "tag", "config", "ls-remote", "grep", "reflog", "stash"}
_BAD_FIND = {"-exec", "-execdir", "-ok", "-okdir", "-delete", "-fprint", "-fprintf", "-fls"}
_SPLIT = re.compile(r"\|\||&&|\||;|\n")


def _segment_ok(seg: str) -> bool:
    try:
        words = shlex.split(seg, comments=False)
    except ValueError:
        return False
    while words and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", words[0]):     # leading VAR=value
        words = words[1:]
    if not words:
        return True
    prog, rest = os.path.basename(words[0]), words[1:]
    if prog == "git":
        args = [w for w in rest if not w.startswith("-")]
        if not args or args[0] not in GIT_READ:
            return False
        sub = args[0]
        if sub == "branch":
            return all(w in ("-a", "-v", "-vv", "-r", "--list", "--show-current", "--all") for w in rest[rest.index("branch") + 1:])
        if sub == "tag":
            return all(w in ("-l", "--list", "-n") for w in rest[rest.index("tag") + 1:])
        if sub == "remote":
            tail = rest[rest.index("remote") + 1:]
            return not tail or tail[0] in ("-v", "show", "get-url")
        if sub == "config":
            return "--get" in rest or "--list" in rest or "-l" in rest
        if sub == "stash":
            return "list" in rest or "show" in rest
        return True
    if prog not in READ_ONLY:
        return False
    if prog == "find" and any(w in _BAD_FIND for w in words):
        return False
    if prog == "sort" and any(w.startswith("-o") for w in rest):
        return False
    if prog == "date" and any(w.startswith("-s") or w == "--set" for w in rest):
        return False
    if prog == "tree" and "-o" in rest:
        return False
    return True


def is_read_only(command: str) -> bool:
    """True only for plain inspection: no redirects, no substitutions, nothing that edits, deletes or installs."""
    c = command.strip()
    if not c or len(c) > 600:
        return False
    if re.search(r"[<>`]|\$\(|\$\{|<\(|(?<!&)&(?!&)", c):
        return False
    if re.search(r"\.env\b|id_rsa|id_ed25519|\.pem\b|credentials|\.netrc", c):
        return False
    return all(_segment_ok(s) for s in _SPLIT.split(c))


# ----------------------------------------------------------------------------- running commands

def _clip(text: str, limit: int = OUT_LIMIT) -> str:
    text = safety.redact(_ANSI.sub("", text or "")).replace("\r", "")
    if len(text) <= limit:
        return text
    head = text[: limit // 3]
    tail = text[-(limit - len(head)):]
    return f"{head}\n… ({len(text) - limit} characters left out) …\n{tail}"


class Shell:
    """A persistent working directory and environment, like the plan runner, with a timeout and a stop switch."""

    def __init__(self, cwd: Optional[str] = None):
        self.cwd = os.path.abspath(os.path.expanduser(cwd or os.getcwd()))
        self.env = dict(os.environ)
        self.env.setdefault("TERM", "dumb")
        self.env["NO_COLOR"] = "1"
        self.env["PAGER"] = "cat"
        self.env["GIT_PAGER"] = "cat"

    def run(self, command: str, stop: Optional[threading.Event] = None, timeout: Optional[int] = None) -> Dict[str, Any]:
        import json
        import shutil
        timeout = timeout or CMD_TIMEOUT
        tmp = tempfile.mkdtemp(prefix="newton-agent-")
        t0 = time.time()
        try:
            state, script = os.path.join(tmp, "state.json"), os.path.join(tmp, "step.sh")
            with open(script, "w") as f:
                f.write(PRELUDE + command.rstrip("\n") + "\n")
            env = dict(self.env, NEWTON_STATE=state, NEWTON_PY=sys.executable)
            out_path = os.path.join(tmp, "out.txt")
            with open(out_path, "wb") as out:
                p = subprocess.Popen([shutil.which("bash") or "/bin/sh", script], cwd=self.cwd, env=env, stdin=subprocess.DEVNULL,
                                     stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
                status = "ok"
                while p.poll() is None:
                    if stop is not None and stop.is_set():
                        status = "stopped"
                    elif time.time() - t0 > timeout:
                        status = "timeout"
                    if status != "ok":
                        try:
                            os.killpg(p.pid, signal.SIGTERM)
                            time.sleep(0.4)
                            if p.poll() is None:
                                os.killpg(p.pid, signal.SIGKILL)
                        except (ProcessLookupError, PermissionError):
                            pass
                        break
                    time.sleep(0.05)
                p.wait()
            if os.path.exists(state):
                try:
                    snap = json.load(open(state))
                    if os.path.isdir(snap.get("cwd", "")):
                        self.cwd = snap["cwd"]
                    self.env = {k: v for k, v in snap.get("env", {}).items() if k not in ("NEWTON_STATE", "NEWTON_PY", "_", "SHLVL")}
                except (OSError, ValueError):
                    pass
            raw = open(out_path, "rb").read(400_000).decode("utf-8", "replace")
            return {"code": p.returncode if status == "ok" else -1, "status": status, "output": _clip(raw),
                    "seconds": round(time.time() - t0, 1), "cwd": self.cwd}
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ----------------------------------------------------------------------------- the agent

Emit = Callable[[Dict[str, Any]], None]


def _extract(text: str) -> Dict[str, Any]:
    try:
        data = llm.parse_json(text)
    except NewtonError:
        return {"action": "say", "message": text.strip()} if text.strip() else {}
    if isinstance(data, dict) and "action" not in data:
        for k in ("say", "run", "read", "list", "write"):           # tolerate {"run": "ls"} style slips
            if k in data:
                v = data[k]
                if k == "say":
                    return {"action": "say", "message": str(v)}
                if k == "run":
                    return {"action": "run", "command": str(v), "why": str(data.get("why", ""))}
                return {"action": k, "path": str(v), "content": str(data.get("content", "")), "why": str(data.get("why", ""))}
        if "message" in data:
            return {"action": "say", "message": str(data["message"])}
    return data if isinstance(data, dict) else {}


class Agent:
    def __init__(self, cfg: Dict[str, Any], cwd: Optional[str] = None, mode: str = "smart", name: str = NAME):
        self.cfg = cfg
        self.name = name
        self.mode = mode if mode in MODES else "smart"
        self.shell = Shell(cwd)
        self.messages: List[Dict[str, str]] = []
        self.stop = threading.Event()
        self._approvals: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    # -- approvals
    def decide(self, call_id: str, allow: bool) -> bool:
        with self._lock:
            slot = self._approvals.get(call_id)
        if not slot:
            return False
        slot["allow"] = bool(allow)
        slot["event"].set()
        return True

    def _ask(self, emit: Emit, call_id: str, why_ask: str) -> bool:
        slot = {"event": threading.Event(), "allow": False}
        with self._lock:
            self._approvals[call_id] = slot
        emit({"type": "approval", "id": call_id, "reason": why_ask})
        deadline = time.time() + 900
        while not slot["event"].wait(0.25):
            if self.stop.is_set() or time.time() > deadline:
                break
        with self._lock:
            self._approvals.pop(call_id, None)
        allowed = slot["allow"] and not self.stop.is_set()
        emit({"type": "decision", "id": call_id, "allow": allowed})
        return allowed

    # -- the loop
    def _system(self) -> str:
        env = brain.env_block(self.cfg, os.path.basename(os.environ.get("SHELL", "bash")))
        return SYSTEM.format(name=self.name, env=env + f"\nWorking directory: {self.shell.cwd}")

    def _trim(self) -> List[Dict[str, str]]:
        m = self.messages[-40:]
        while m and m[0]["role"] != "user":
            m = m[1:]
        return m

    def _next(self) -> Dict[str, Any]:
        last_err = ""
        for _ in range(3):
            raw = llm.complete(self.cfg, self._system(), self._trim(), 1800, smart=True, json_mode=True,
                               timeout=max(float(self.cfg.get("timeout", 20)), 120.0))
            act = _extract(raw)
            if act.get("action") in ("run", "read", "list", "write", "say"):
                self.messages.append({"role": "assistant", "content": raw})
                return act
            last_err = raw
            self.messages.append({"role": "assistant", "content": raw or "(empty)"})
            self.messages.append({"role": "user", "content": 'Reply with exactly one JSON object using one of the listed actions, for example {"action":"say","message":"..."}.'})
        raise NewtonError("The AI didn't answer in a form I could follow. Try again, or pick a stronger model in `newton setup`.")

    def _observe(self, text: str) -> None:
        self.messages.append({"role": "user", "content": text})

    def turn(self, text: str, emit: Emit) -> None:
        """Runs one user request to completion, emitting UI events as it goes."""
        self.stop.clear()
        self.messages.append({"role": "user", "content": text})
        try:
            for step in range(MAX_STEPS):
                if self.stop.is_set():
                    emit({"type": "say", "text": "Stopped."})
                    return
                emit({"type": "thinking"})
                act = self._next()
                kind = act["action"]
                if kind == "say":
                    emit({"type": "say", "text": str(act.get("message", "")).strip() or "Done."})
                    return
                call_id = uuid.uuid4().hex[:10]
                if kind == "run":
                    result = self._do_run(call_id, act, emit)
                elif kind == "read":
                    result = self._do_read(call_id, act, emit)
                elif kind == "list":
                    result = self._do_list(call_id, act, emit)
                else:
                    result = self._do_write(call_id, act, emit)
                self._observe(result)
            emit({"type": "say", "text": f"I've taken {MAX_STEPS} steps without finishing, so I'm pausing here. Tell me to keep going or change direction."})
        except NewtonError as e:
            emit({"type": "error", "text": str(e)})
        except Exception as e:                                    # never let the worker die silently
            emit({"type": "error", "text": f"Something went wrong: {e}"})

    # -- actions
    def _resolve(self, path: str) -> str:
        p = os.path.expanduser(str(path or ""))
        return os.path.abspath(p if os.path.isabs(p) else os.path.join(self.shell.cwd, p))

    def _do_run(self, call_id: str, act: Dict[str, Any], emit: Emit) -> str:
        cmd = str(act.get("command", "")).strip()
        why = str(act.get("why", ""))[:200]
        if not cmd:
            return "Error: empty command."
        warnings = safety.check(cmd, notes=False)
        level = safety.level(cmd)
        auto = self.mode == "smart" and level == 0 and is_read_only(cmd)
        emit({"type": "tool", "id": call_id, "kind": "run", "command": cmd, "why": why, "cwd": self.shell.cwd,
              "auto": auto, "level": level, "warnings": warnings})
        if not auto:
            reason = "This could change something." if level == 0 else ("; ".join(warnings) or "This is risky.")
            if self.mode == "ask":
                reason = "You asked me to check every command first." if level == 0 else reason
            if not self._ask(emit, call_id, reason):
                emit({"type": "result", "id": call_id, "denied": True, "output": "", "code": None})
                return f"The user denied this command ({cmd}). Do not run it. Offer another approach or ask what they prefer."
        res = self.shell.run(cmd, self.stop)
        emit({"type": "result", "id": call_id, "code": res["code"], "status": res["status"], "output": res["output"],
              "seconds": res["seconds"], "cwd": res["cwd"]})
        note = {"timeout": f" The command was stopped after {CMD_TIMEOUT} seconds.", "stopped": " The user stopped it."}.get(res["status"], "")
        return f"Command finished with exit code {res['code']}.{note}\nWorking directory is now {res['cwd']}\nOutput:\n{res['output'] or '(no output)'}"

    def _do_read(self, call_id: str, act: Dict[str, Any], emit: Emit) -> str:
        path = self._resolve(act.get("path", ""))
        emit({"type": "tool", "id": call_id, "kind": "read", "command": path, "why": "", "cwd": self.shell.cwd, "auto": True, "level": 0, "warnings": []})
        try:
            body = chat.read_file_for_ai(path)
            if os.path.isdir(path):
                raise NewtonError(f"{path} is a folder. Use list instead.")
        except NewtonError as e:
            emit({"type": "result", "id": call_id, "code": 1, "status": "ok", "output": str(e), "seconds": 0})
            return f"Error: {e}"
        emit({"type": "result", "id": call_id, "code": 0, "status": "ok", "output": _clip(body, 3000), "seconds": 0})
        return f"Contents of {path}:\n{body}"

    def _do_list(self, call_id: str, act: Dict[str, Any], emit: Emit) -> str:
        path = self._resolve(act.get("path") or ".")
        emit({"type": "tool", "id": call_id, "kind": "list", "command": path, "why": "", "cwd": self.shell.cwd, "auto": True, "level": 0, "warnings": []})
        try:
            names = sorted(os.listdir(path), key=str.lower)
            lines = [n + ("/" if os.path.isdir(os.path.join(path, n)) else "") for n in names[:300]]
            out = "\n".join(lines) + (f"\n… and {len(names) - 300} more" if len(names) > 300 else "")
            code = 0
        except OSError as e:
            out, code = f"Can't list {path}: {e.strerror or e}", 1
        emit({"type": "result", "id": call_id, "code": code, "status": "ok", "output": out or "(empty folder)", "seconds": 0})
        return f"Listing of {path}:\n{out or '(empty folder)'}"

    def _do_write(self, call_id: str, act: Dict[str, Any], emit: Emit) -> str:
        path = self._resolve(act.get("path", ""))
        content = str(act.get("content", ""))
        exists = os.path.exists(path)
        emit({"type": "tool", "id": call_id, "kind": "write", "command": path, "why": str(act.get("why", ""))[:200], "cwd": self.shell.cwd,
              "auto": False, "level": 1 if exists else 0, "warnings": ["Replaces the existing file."] if exists else [], "preview": _clip(content, 2500)})
        if chat.SENSITIVE.search(path):
            emit({"type": "result", "id": call_id, "code": 1, "status": "ok", "output": "Newton won't write to files that hold secrets.", "seconds": 0})
            return "Error: refused, that file holds secrets."
        if not os.path.isdir(os.path.dirname(path)):
            emit({"type": "result", "id": call_id, "code": 1, "status": "ok", "output": "The folder doesn't exist.", "seconds": 0})
            return f"Error: the folder {os.path.dirname(path)} doesn't exist. Create it with a command first."
        if not self._ask(emit, call_id, "Replaces an existing file." if exists else "Creates a new file."):
            emit({"type": "result", "id": call_id, "denied": True, "output": "", "code": None})
            return f"The user denied writing {path}. Do not write it. Offer another approach or ask."
        try:
            Path(path).write_text(content)
            msg = f"Wrote {len(content)} characters to {path}."
            code = 0
        except OSError as e:
            msg, code = f"Couldn't write {path}: {e.strerror or e}", 1
        emit({"type": "result", "id": call_id, "code": code, "status": "ok", "output": msg, "seconds": 0})
        return msg
