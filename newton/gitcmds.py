"""`newton commit` — a commit message that matches your repo's style, written from the staged diff."""
from __future__ import annotations

import subprocess
from typing import Any, Dict, List, Optional

from newton import brain, term, ui
from newton.llm import NewtonError

NOISE = [":(exclude)package-lock.json", ":(exclude)yarn.lock", ":(exclude)pnpm-lock.yaml", ":(exclude)*.lock",
         ":(exclude)*.min.js", ":(exclude)*.map"]
MAX_DIFF = 28_000


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], capture_output=True, text=True)


def commit(cfg: Dict[str, Any], stage_all: bool = False, yes: bool = False) -> int:
    if _git("rev-parse", "--is-inside-work-tree").returncode != 0:
        ui.err("This folder isn't inside a git repository.")
        return 1

    staged = _git("diff", "--cached", "--name-only").stdout.split()
    if not staged:
        dirty = _git("status", "--porcelain").stdout.strip()
        if not dirty:
            print(f"\n  {ui.CHECK} {ui.grey('Nothing to commit — working tree is clean.')}\n")
            return 0
        print(f"\n  {ui.grey('Nothing is staged yet. Changed files:')}")
        for ln in dirty.splitlines()[:12]:
            print(f"  {ui.grey(ln)}")
        if not (stage_all or yes):
            if term.ask_key(term.menu(("⏎", "stage everything (git add -A)"), ("n", "cancel"))) != "enter":
                return 0
        _git("add", "-A")

    stat = _git("diff", "--cached", "--stat").stdout.strip()
    diff = _git("diff", "--cached", "--no-color", "-U2", "--", ".", *NOISE).stdout
    if len(diff) > MAX_DIFF:
        diff = diff[:MAX_DIFF] + "\n… (diff truncated)"
    recent = _git("log", "-8", "--format=%s").stdout.strip().splitlines()

    msg: Optional[Dict[str, str]] = None
    while True:
        if msg is None:
            try:
                with term.Spinner("Newton is reading your diff"):
                    msg = brain.commit_message(stat, diff, recent, cfg)
            except NewtonError as e:
                ui.err(str(e))
                return 1
        print()
        print(f"  {ui.grey(stat.splitlines()[-1] if stat else '')}")
        print(f"\n  {ui.bold(msg['subject'])}")
        if msg["body"]:
            print(term.wrap(msg["body"], "  "))
        print()
        key = "enter" if yes else term.ask_key(term.menu(("⏎", "commit"), ("e", "edit subject"), ("r", "rewrite"), ("q", "cancel")))
        if key in ("q", "esc"):
            print(f"  {ui.grey('cancelled — your changes are still staged.')}\n")
            return 0
        if key == "r":
            msg = None
            continue
        if key == "e":
            new = term.ask_line(ui.green("  subject › "), prefill=msg["subject"])
            if new:
                msg["subject"] = new
            continue
        if key == "enter":
            args = ["commit", "-m", msg["subject"]] + (["-m", msg["body"]] if msg["body"] else [])
            res = _git(*args)
            if res.returncode != 0:
                ui.err((res.stderr or res.stdout).strip() or "git commit failed")
                return 1
            first = (res.stdout.strip().splitlines() or [""])[0]
            print(f"  {ui.CHECK} {ui.green('committed')} {ui.grey(first)}\n")
            return 0
