"""`newton chat` — a conversation with Newton that knows your machine, without leaving the terminal."""
from __future__ import annotations

import os
import re
import sys
from typing import Any, Dict, List

from newton import brain, safety, term, ui
from newton.llm import NewtonError
from newton.runner import Session

SENSITIVE = re.compile(r"(^|/)(\.env(\..*)?|id_(rsa|dsa|ecdsa|ed25519)|.*\.(pem|key|p12|pfx)|credentials|\.netrc|\.npmrc|\.pypirc)$", re.I)
MAX_FILE = 24_000

HELP = [
    ("/plan <goal>", "turn a goal into a step-by-step plan and run it"),
    ("/run [n]", "run the last shell snippet Newton gave you (after you review it)"),
    ("/file <path>", "show Newton a file (secrets files are refused)"),
    ("!<command>", "run a command here; Newton sees what it printed"),
    ("/fix", "diagnose your last failed command"),
    ("/clear", "forget the conversation"),
    ("/exit", "leave (or press Ctrl+D)"),
]


def read_file_for_ai(path: str, force: bool = False) -> str:
    path = os.path.expanduser(path)
    if SENSITIVE.search(path) and not force:
        raise NewtonError(f"'{os.path.basename(path)}' looks like it holds secrets, so Newton won't send it.")
    try:
        with open(path, "r", errors="replace") as f:
            text = f.read(MAX_FILE + 1)
    except OSError as e:
        raise NewtonError(f"Can't read {path}: {e.strerror or e}") from None
    note = f"\n… (truncated at {MAX_FILE} characters)" if len(text) > MAX_FILE else ""
    return safety.redact(text[:MAX_FILE]) + note


def _trim(history: List[Dict[str, str]], keep: int = 16) -> List[Dict[str, str]]:
    h = history[-keep:]
    while h and h[0]["role"] != "user":
        h = h[1:]
    return h


def chat(cfg: Dict[str, Any]) -> int:
    sess = Session()
    history: List[Dict[str, str]] = []
    last_blocks: List[str] = []
    system = brain.ASK_SYSTEM + "\n\nEnvironment:\n" + brain.env_block(cfg, os.path.basename(os.environ.get("SHELL", "bash")))

    print(f"\n  {ui.lime('●')} {ui.bold('newton chat')}  {ui.grey('· ask anything · /help for commands · Ctrl+D to leave')}\n")
    while True:
        try:
            line = input(term.rl(f"{ui.green('❯')} ")).strip()
        except EOFError:
            print()
            return 0
        except KeyboardInterrupt:
            print()
            continue
        if not line:
            continue

        if line in ("/exit", "/quit", "exit", "quit"):
            return 0
        if line == "/help":
            print()
            for k, v in HELP:
                print(f"  {ui.lime(k.ljust(14))} {ui.grey(v)}")
            print()
            continue
        if line == "/clear":
            history, last_blocks = [], []
            print(f"  {ui.grey('conversation cleared')}\n")
            continue
        if line.startswith("/plan"):
            from newton import planrun
            goal = line[5:].strip() or term.ask_line("  goal › ")
            if goal:
                planrun.start(goal, cfg)
            continue
        if line == "/fix":
            from newton import fixcmd
            fixcmd.fix(cfg)
            continue
        if line.startswith("/file"):
            path = line[5:].strip()
            if not path:
                print(f"  {ui.grey('usage: /file <path>')}\n")
                continue
            try:
                text = read_file_for_ai(path)
            except NewtonError as e:
                print(f"  {ui.CROSS} {e}\n")
                continue
            history.append({"role": "user", "content": f"Here is the file {path}:\n```\n{text}\n```\n(No question yet — wait for me to ask.)"})
            history.append({"role": "assistant", "content": "Got it. What would you like to know about it?"})
            print(f"  {ui.CHECK} {ui.grey('attached ' + path + f' ({len(text)} chars)')}\n")
            continue
        if line.startswith("!"):
            cmd = line[1:].strip()
            if not cmd:
                continue
            res = sess.run(cmd)
            out = safety.redact(res.output)[-4000:]
            history.append({"role": "user", "content": f"I ran `{cmd}` (exit {res.code}) and it printed:\n```\n{out}\n```\n(No question yet — wait for me to ask.)"})
            history.append({"role": "assistant", "content": "Noted. What would you like to know?"})
            print(f"  {ui.grey('exit ' + str(res.code) + ' · Newton can see that output now')}\n")
            continue
        if line.startswith("/run"):
            runnable = last_blocks
            if not runnable:
                print(f"  {ui.grey('Nothing runnable yet — ask Newton for a command first.')}\n")
                continue
            pick = line[4:].strip()
            n = int(pick) - 1 if pick.isdigit() else len(runnable) - 1
            if not 0 <= n < len(runnable):
                print(f"  {ui.grey('There are ' + str(len(runnable)) + ' snippet(s) — try /run 1')}\n")
                continue
            cmd = runnable[n]
            print()
            for j, l in enumerate(cmd.splitlines()):
                print(f"  {ui.green('❯') if j == 0 else ' '} {ui.cmd(l)}")
            warn = safety.check(cmd)
            if warn:
                print(f"  {ui.WARN} {ui.amber('; '.join(warn))}")
            lvl = safety.level(cmd)
            key = term.ask_key(term.menu(("y" if lvl == 2 else "⏎", "run"), ("n", "don't")))
            if key == "y" or (key == "enter" and lvl < 2):
                res = sess.run(cmd)
                print(f"  {ui.grey('exit ' + str(res.code))}\n")
            continue

        history.append({"role": "user", "content": line})
        try:
            reply = brain.answer(cfg, _trim(history), system)
        except NewtonError as e:
            history.pop()
            print(f"  {ui.CROSS} {e}\n")
            continue
        except KeyboardInterrupt:
            history.pop()
            print()
            continue
        history.append({"role": "assistant", "content": reply})
        last_blocks = [code for lang, code in term.code_blocks(reply) if lang in term.SHELL_LANGS]
        if last_blocks:
            print(f"  {ui.grey('/run to execute the command above')}\n")
