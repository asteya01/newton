"""Terminal styling helpers (respects NO_COLOR and non-TTY output)."""
from __future__ import annotations

import os
import sys

_ON = sys.stdout.isatty() and not os.environ.get("NO_COLOR") and os.environ.get("TERM") != "dumb"


def _c(code: str):
    return lambda s: f"\033[{code}m{s}\033[0m" if _ON else str(s)


bold = _c("1")
dim = _c("2")
italic = _c("3")
green = _c("38;5;121")      # Newton mint
lime = _c("38;5;156")
amber = _c("38;5;214")
red = _c("38;5;203")
blue = _c("38;5;111")
grey = _c("38;5;245")
cmd = _c("1;38;5;121")

CHECK = green("✓")
CROSS = red("✗")
WARN = amber("▲")
DOT = grey("•")


def banner() -> str:
    return "\n".join([
        "",
        f"   {lime('●')}",
        f"   {grey('┊')}     {bold('n e w t o n')}",
        f"   {grey('┊')}     {grey('Think it.')} {lime('Tab it.')} {grey('Done.')}",
        f"  {green('❯')} {lime('_')}",
        "",
    ])


def err(msg: str) -> None:
    print(f"{CROSS} {msg}", file=sys.stderr)
