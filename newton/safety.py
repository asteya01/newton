"""Local safety net. Runs on every suggestion and plan step, independent of the AI."""
from __future__ import annotations

import re
from typing import List, Optional

# (severity, pattern, warning).  2 = destructive / irreversible, 1 = needs a second look.
RULES = [
    (2, r"\brm\s+(-[a-zA-Z]*[rR][a-zA-Z]*\s+)*-[a-zA-Z]*[fF]?[a-zA-Z]*\s+(/|~|\$HOME|\*|/\*)(\s|$)", "Deletes everything under a root, home or wildcard path"),
    (1, r"\brm\s+-[a-zA-Z]*[rR]", "Recursively deletes files — there is no undo"),
    (1, r"\bsudo\b", "Runs with administrator privileges"),
    (2, r"\bdd\s+.*\bof=/dev/", "Writes raw data directly to a disk device"),
    (2, r"\bmkfs(\.\w+)?\b", "Formats a filesystem — erases the target device"),
    (2, r"(curl|wget)\b[^|]*\|\s*(sudo\s+)?(ba|z|fi)?sh\b", "Downloads a script and executes it immediately"),
    (1, r"\bchmod\s+(-R\s+)?0?777\b", "Makes files writable by every user"),
    (1, r"\bchown\s+-R\b", "Recursively changes file ownership"),
    (2, r":\(\)\s*\{\s*:\|:&\s*\};:", "Fork bomb — will freeze the machine"),
    (2, r"\bgit\s+push\b.*(--force\b|-f\b)", "Force-push rewrites remote history"),
    (2, r"\bgit\s+reset\s+--hard\b", "Discards all uncommitted changes"),
    (2, r"\bgit\s+clean\s+-[a-zA-Z]*f", "Permanently deletes untracked files"),
    (2, r"\bdocker\s+(system|volume|image)\s+prune\b", "Permanently removes Docker data"),
    (2, r"\bkubectl\s+delete\b", "Deletes Kubernetes resources"),
    (2, r">\s*/dev/sd[a-z]", "Overwrites a disk device"),
    (2, r"\bshutdown\b|\breboot\b|\bhalt\b", "Shuts down or restarts the machine"),
    (1, r"\bkill(all)?\s+-9\b", "Force-kills processes without letting them clean up"),
    (2, r"\b(DROP|TRUNCATE)\s+(TABLE|DATABASE)\b", "Destroys database data"),
    (2, r"\bfind\b.*\s-delete\b", "Deletes every file the search matches"),
    (0, r"(^|[^>])>\s*~?/?[\w./-]+\s*$", "Overwrites the target file"),   # a note, not a risk: plans write files all the time
    (1, r"(^|[^>])>>?\s*(~|/etc/|/usr/|/var/|/opt/|\$HOME|/home/|/root/|/Library/)\S*", "Writes to a file outside the current folder"),
]
_COMPILED = [(sev, re.compile(p, re.IGNORECASE), msg) for sev, p, msg in RULES]


def check(command: str, notes: bool = True) -> List[str]:
    """Returns a de-duplicated list of warnings for a command (empty if it looks safe).
    `notes=False` leaves out severity-0 remarks (like 'overwrites the target file'), which are useful on a
    single suggested command but just noise in a plan where creating files is the whole point."""
    found: List[str] = []
    for sev, rx, msg in _COMPILED:
        if (sev > 0 or notes) and rx.search(command) and msg not in found:
            found.append(msg)
    # The broad "rm -r" rule is redundant when the root/home rule already fired.
    if found and found[0].startswith("Deletes everything") and "Recursively deletes files — there is no undo" in found:
        found.remove("Recursively deletes files — there is no undo")
    return found


def level(command: str) -> int:
    """0 = looks safe, 1 = caution, 2 = danger (the worst rule that matches)."""
    worst = 0
    for sev, rx, _ in _COMPILED:
        if rx.search(command):
            worst = max(worst, sev)
    return worst


def summarize(command: str, model_warning: Optional[str] = None) -> Optional[str]:
    warnings = check(command)
    # Local rules are authoritative; fall back to the AI's warning only when they found nothing.
    if not warnings and model_warning and model_warning.strip():
        warnings.append(model_warning.strip().rstrip("."))
    return "; ".join(warnings) if warnings else None


# ----------------------------------------------------------------------------- secrets

_SECRETS = [re.compile(p) for p in (
    r"sk-ant-[A-Za-z0-9_\-]{10,}", r"sk-[A-Za-z0-9]{20,}", r"gh[pousr]_[A-Za-z0-9]{20,}", r"github_pat_[A-Za-z0-9_]{20,}",
    r"AKIA[0-9A-Z]{16}", r"xox[baprs]-[A-Za-z0-9-]{10,}", r"AIza[0-9A-Za-z_\-]{30,}",
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----",
)]
_KV = re.compile(r"(?i)\b(password|passwd|secret|token|api[_-]?key|authorization)\b(\s*[=:]\s*)([^\s'\"]{4,})")


def redact(text: str) -> str:
    """Masks anything that looks like a credential before text is sent to an AI provider."""
    for rx in _SECRETS:
        text = rx.sub("***redacted***", text)
    return _KV.sub(lambda m: f"{m.group(1)}{m.group(2)}***redacted***", text)
