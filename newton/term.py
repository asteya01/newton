"""Terminal primitives shared by plan mode, chat, fix and commit: keys, spinner, line editing, streaming Markdown."""
from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
from typing import List, Optional, Tuple

from newton import ui


def width(maxw: int = 100) -> int:
    return max(40, min(shutil.get_terminal_size((100, 24)).columns, maxw))


def interactive() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def set_title(text: str) -> None:
    """Puts progress in the terminal tab title (e.g. '◆ Python project · 2/5'). No-op when not a terminal."""
    if sys.stdout.isatty() and os.environ.get("TERM", "") not in ("", "dumb"):
        sys.stdout.write(f"\033]0;{text.replace(chr(27), '').replace(chr(7), '')}\007")
        sys.stdout.flush()


def bell() -> None:
    if sys.stdout.isatty():
        sys.stdout.write("\a")
        sys.stdout.flush()


def trunc(s: str, n: int) -> str:
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[: max(1, n - 1)] + "…"


def wrap(text: str, indent: str = "  ", w: Optional[int] = None) -> str:
    w = w or width()
    return "\n".join(
        textwrap.fill(p, w, initial_indent=indent, subsequent_indent=indent) if p.strip() else ""
        for p in text.splitlines())


def rl(s: str) -> str:
    """Hide ANSI colour codes from readline's cursor maths (only matters when prompting at a keyboard)."""
    return re.sub(r"(\x1b\[[0-9;]*m)", "\001\\1\002", s) if sys.stdin.isatty() else s


def menu(*items: Tuple[str, str]) -> str:
    return "  " + "   ".join(f"{ui.lime(k)} {ui.grey(v)}" for k, v in items) + "  "


# ----------------------------------------------------------------------------- spinner

class Spinner:
    FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def __init__(self, label: str):
        self.label = label
        self._stop = threading.Event()
        self._th: Optional[threading.Thread] = None
        self._t0 = 0.0
        self._live = False

    def start(self) -> "Spinner":
        self._t0 = time.time()
        if sys.stderr.isatty():
            self._live = True
            self._th = threading.Thread(target=self._spin, daemon=True)
            self._th.start()
        else:
            print(f"  … {self.label}", file=sys.stderr)
        return self

    def _spin(self) -> None:
        i = 0
        while not self._stop.wait(0.09):
            el = int(time.time() - self._t0)
            sys.stderr.write(f"\r  {ui.green(self.FRAMES[i % len(self.FRAMES)])} {self.label} {ui.grey(str(el) + 's')}\033[K")
            sys.stderr.flush()
            i += 1

    def stop(self) -> None:
        if self._live:
            self._stop.set()
            if self._th:
                self._th.join(timeout=1)
            sys.stderr.write("\r\033[2K")
            sys.stderr.flush()
            self._live = False

    def __enter__(self) -> "Spinner":
        return self.start()

    def __exit__(self, *exc) -> None:
        self.stop()


# ----------------------------------------------------------------------------- keys & lines

def _getch() -> str:
    import termios
    import tty
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        ch = os.read(fd, 1)
        if ch == b"\x1b":
            import select
            while select.select([fd], [], [], 0.02)[0]:
                os.read(fd, 1)
            return "esc"
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    if ch in (b"\r", b"\n"):
        return "enter"
    if ch == b"\x04":
        return "q"
    return ch.decode("utf-8", "ignore").lower() or "?"


def ask_key(prompt: str) -> str:
    """One keypress (no Enter needed at a keyboard). Returns 'enter', 'esc', or a lowercase character.
    When stdin is piped, reads a line instead and uses its first character — handy for scripting and tests."""
    sys.stdout.write(prompt)
    sys.stdout.flush()
    if sys.stdin.isatty():
        key = _getch()
    else:
        line = sys.stdin.readline()
        if line == "":
            sys.stdout.write("\n")
            return "q"
        line = line.strip()
        key = "enter" if not line else line[0].lower()
    sys.stdout.write(ui.grey("⏎" if key == "enter" else key) + "\n")
    sys.stdout.flush()
    return key


def ask_line(prompt: str, default: str = "", prefill: str = "") -> str:
    try:
        import readline
    except ImportError:  # pragma: no cover
        readline = None  # type: ignore
    if prefill and readline and sys.stdin.isatty():
        readline.set_startup_hook(lambda: readline.insert_text(prefill))
    try:
        val = input(rl(prompt))
    except EOFError:
        print()
        return default
    finally:
        if prefill and readline:
            readline.set_startup_hook()
    val = val.strip()
    return val if val else default


def edit_command(cmd: str) -> Optional[str]:
    """Lets the user change a command. Multi-line commands open in $EDITOR; one-liners edit in place."""
    if "\n" in cmd and sys.stdin.isatty():
        editor = os.environ.get("VISUAL") or os.environ.get("EDITOR") or shutil.which("nano") or "vi"
        with tempfile.NamedTemporaryFile("w+", suffix=".sh", delete=False) as f:
            f.write(cmd)
            path = f.name
        try:
            subprocess.call(shlex.split(editor) + [path])
            with open(path) as f:
                out = f.read().strip()
        finally:
            os.unlink(path)
        return out or None
    val = ask_line(ui.green("  ❯ "), prefill=cmd)
    return val or None


# ----------------------------------------------------------------------------- streaming markdown

class MarkdownStream:
    """Renders a streamed Markdown answer line by line with terminal styling."""

    def __init__(self, indent: str = "  "):
        self.indent = indent
        self.buf = ""
        self.in_code = False
        self.lang = ""

    def feed(self, text: str) -> None:
        self.buf += text
        while "\n" in self.buf:
            line, self.buf = self.buf.split("\n", 1)
            self._line(line)

    def flush(self) -> None:
        if self.buf:
            self._line(self.buf)
            self.buf = ""
        sys.stdout.flush()

    @staticmethod
    def inline(s: str) -> str:
        s = re.sub(r"`([^`]+)`", lambda m: ui.cmd(m.group(1)), s)
        s = re.sub(r"\*\*([^*]+)\*\*", lambda m: ui.bold(m.group(1)), s)
        return s

    def _line(self, line: str) -> None:
        stripped = line.strip()
        if stripped.startswith("```"):
            if not self.in_code:
                self.in_code, self.lang = True, stripped[3:].strip()
                if self.lang:
                    sys.stdout.write(f"{self.indent}{ui.grey('╭ ' + self.lang)}\n")
            else:
                self.in_code = False
            return
        if self.in_code:
            sys.stdout.write(f"{self.indent}{ui.grey('│')} {ui.cmd(line)}\n")
            return
        m = re.match(r"^#{1,6}\s+(.*)$", line)
        if m:
            sys.stdout.write(f"{self.indent}{ui.bold(m.group(1))}\n")
        else:
            sys.stdout.write(f"{self.indent}{self.inline(line)}\n")
        sys.stdout.flush()


FENCE = re.compile(r"```([\w+-]*)\n(.*?)```", re.S)


def code_blocks(text: str) -> List[Tuple[str, str]]:
    return [(m.group(1).lower(), m.group(2).rstrip("\n")) for m in FENCE.finditer(text)]


SHELL_LANGS = {"", "bash", "sh", "shell", "zsh", "fish", "console", "terminal"}


def render_explain(command: str, data: dict) -> None:
    print()
    print(f"  {ui.green('❯')} {ui.bold(command)}")
    print(f"    {data.get('summary', '')}")
    print()
    parts = data.get("parts") or []
    w = min(28, max((len(str(p.get("part", ""))) for p in parts), default=0))
    for p in parts:
        print(f"  {ui.lime(str(p.get('part', '')).ljust(w))}  {ui.grey(str(p.get('meaning', '')))}")
    if data.get("danger"):
        print()
        print(f"  {ui.WARN} {ui.amber(data['danger'])}")
    print()
