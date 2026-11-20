"""Runs commands the way a person would in a terminal — and remembers where they ended up.

A Session keeps the working directory and exported variables between commands, so a plan can
`cd project` in step 2 and run `npm test` in step 3. Output streams live to the screen (through a
real pseudo-terminal when you're at a keyboard, so sudo, installers and progress bars all behave)
while the last lines are captured so Newton can diagnose a failure.
"""
from __future__ import annotations

import json
import os
import re
import select
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from typing import Dict, Optional

# Prepended to every command: report the final cwd + environment back to us, however the script exits.
PRELUDE = r'''set -o pipefail
__newton_exit() {
  __newton_rc=$?
  trap - EXIT
  "$NEWTON_PY" -I -c 'import os, json, sys; json.dump({"cwd": os.getcwd(), "env": dict(os.environ)}, open(sys.argv[1], "w"))' "$NEWTON_STATE" 2>/dev/null
  exit $__newton_rc
}
trap __newton_exit EXIT
'''

_DROP_ENV = {"NEWTON_STATE", "NEWTON_PY", "_", "SHLVL"}
_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[()][A-Z0-9]|\x1b[=>]")


@dataclass
class RunResult:
    code: int
    output: str
    seconds: float
    interrupted: bool
    cwd: str

    @property
    def ok(self) -> bool:
        return self.code == 0


def nearest_existing(path: str) -> str:
    """The closest parent folder that still exists. A step that deleted its own folder must not push the
    next step into the home directory."""
    path = os.path.abspath(path or ".")
    while path and not os.path.isdir(path):
        parent = os.path.dirname(path)
        if parent == path:
            break
        path = parent
    return path if os.path.isdir(path) else os.path.expanduser("~")


def clean_tail(raw: bytes, max_lines: int = 60, max_chars: int = 6000) -> str:
    text = _ANSI.sub("", raw.decode("utf-8", "replace")).replace("\r\n", "\n")
    lines = [ln.split("\r")[-1].rstrip() for ln in text.split("\n")]   # collapse progress-bar redraws
    return "\n".join(lines[-max_lines:])[-max_chars:].strip()


def _exit_code(status: int) -> int:
    code = os.waitstatus_to_exitcode(status)
    return 128 - code if code < 0 else code


def _write_out(data: bytes) -> None:
    try:
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()
    except AttributeError:  # stdout replaced by a text stream (unit tests)
        sys.stdout.write(data.decode("utf-8", "replace"))
        sys.stdout.flush()


def _spawn_pipe(argv, cwd: str, env: Dict[str, str], buf: bytearray, echo: bool) -> int:
    p = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    fd = p.stdout.fileno()  # type: ignore[union-attr]
    while True:
        ready, _, _ = select.select([fd], [], [], 0.1)
        if ready:
            data = os.read(fd, 65536)
            if not data:
                break
            buf.extend(data)
            if echo:
                _write_out(data)
        elif p.poll() is not None:
            # Exited: drain what's left, but don't hang if a background process keeps the pipe open.
            while select.select([fd], [], [], 0.05)[0]:
                data = os.read(fd, 65536)
                if not data:
                    break
                buf.extend(data)
                if echo:
                    _write_out(data)
            break
    code = p.wait()
    p.stdout.close()  # type: ignore[union-attr]
    return 128 - code if code < 0 else code


def _spawn_pty(argv, cwd: str, env: Dict[str, str], buf: bytearray) -> int:
    import fcntl
    import pty
    import signal
    import termios
    import tty

    stdin_fd, out_fd = sys.stdin.fileno(), sys.stdout.fileno()
    pid, fd = pty.fork()
    if pid == 0:  # child
        try:
            os.chdir(cwd)
        except OSError:
            pass
        os.execvpe(argv[0], argv, env)

    def sync_size(*_):
        try:
            size = fcntl.ioctl(stdin_fd, termios.TIOCGWINSZ, b"\0" * 8)
            fcntl.ioctl(fd, termios.TIOCSWINSZ, size)
        except OSError:
            pass

    sync_size()
    old_handler = signal.signal(signal.SIGWINCH, sync_size)
    old_tty = termios.tcgetattr(stdin_fd)
    status: Optional[int] = None
    stdin_open = True
    try:
        tty.setraw(stdin_fd)
        while True:
            watch = [fd] + ([stdin_fd] if stdin_open else [])
            try:
                ready, _, _ = select.select(watch, [], [], 0.1)
            except InterruptedError:
                continue
            if fd in ready:
                try:
                    data = os.read(fd, 65536)
                except OSError:
                    data = b""
                if not data:
                    break
                os.write(out_fd, data)
                buf.extend(data)
            if stdin_open and stdin_fd in ready:
                data = os.read(stdin_fd, 4096)
                if data:
                    os.write(fd, data)
                else:
                    stdin_open = False
            if status is None:
                wp, st = os.waitpid(pid, os.WNOHANG)
                if wp:
                    status = st
            if status is not None:
                # Child is gone: flush remaining output, don't wait on background processes holding the tty.
                while select.select([fd], [], [], 0.05)[0]:
                    try:
                        data = os.read(fd, 65536)
                    except OSError:
                        break
                    if not data:
                        break
                    os.write(out_fd, data)
                    buf.extend(data)
                break
    finally:
        termios.tcsetattr(stdin_fd, termios.TCSAFLUSH, old_tty)
        signal.signal(signal.SIGWINCH, old_handler)
        try:
            os.close(fd)
        except OSError:
            pass
    if status is None:
        _, status = os.waitpid(pid, 0)
    return _exit_code(status)


class Session:
    """A persistent 'virtual shell': each command runs in bash, but cwd and exported variables carry over."""

    def __init__(self, cwd: Optional[str] = None, env: Optional[Dict[str, str]] = None):
        self.cwd = cwd or os.getcwd()
        self.env: Dict[str, str] = dict(env if env is not None else os.environ)

    def run(self, command: str, *, quiet: bool = False, persist: bool = True) -> RunResult:
        if not os.path.isdir(self.cwd):
            self.cwd = nearest_existing(self.cwd)
        tmp = tempfile.mkdtemp(prefix="newton-run-")
        try:
            state = os.path.join(tmp, "state.json")
            script = os.path.join(tmp, "step.sh")
            with open(script, "w") as f:
                f.write(PRELUDE + command.rstrip("\n") + "\n")
            env = dict(self.env)
            env["NEWTON_STATE"] = state
            env["NEWTON_PY"] = sys.executable
            argv = [shutil.which("bash") or "/bin/sh", script]
            buf = bytearray()
            t0 = time.time()
            if not quiet and sys.stdin.isatty() and sys.stdout.isatty():
                code = _spawn_pty(argv, self.cwd, env, buf)
            else:
                code = _spawn_pipe(argv, self.cwd, env, buf, echo=not quiet)
            dt = time.time() - t0
            if persist and os.path.exists(state):
                try:
                    with open(state) as f:
                        snap = json.load(f)
                    if os.path.isdir(snap.get("cwd", "")):
                        self.cwd = snap["cwd"]
                    self.env = {k: v for k, v in snap.get("env", {}).items() if k not in _DROP_ENV}
                except (OSError, ValueError):
                    pass
            return RunResult(code, clean_tail(bytes(buf)), dt, code == 130, self.cwd)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
