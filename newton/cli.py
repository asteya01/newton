"""Command-line interface.

  newton <description>          print a command for the description (never runs it)
  newton plan <goal>            turn a goal into a checklist and work through it, step by step
  newton resume | status        continue / see the plan you're working on
  newton ask <question>         ask anything (pipe in errors, attach files with -f)
  newton chat                   a conversation that knows your machine
  newton fix                    diagnose the command that just failed, and offer the fix
  newton commit                 write a commit message from your staged changes
  newton explain <command>      break a command down, flag by flag
  newton setup | doctor | init | history | config
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from newton import __version__
from newton import config as cfgmod
from newton import engine, ui
from newton.engine import NewtonError

SHELLS = ("zsh", "bash", "fish")
SUBCOMMANDS = {"suggest", "explain", "setup", "init", "doctor", "history", "config", "help",
               "plan", "resume", "plans", "status", "prompt", "ask", "chat", "fix", "commit", "agent", "update", "uninstall"}
# Real English words people may start a request with ("update all my brew packages"). They only act as commands
# when used on their own, with a flag, or with a single path/URL argument.
AMBIGUOUS = {"update", "uninstall"}


# ----------------------------------------------------------------------------- helpers

def _shell_script(shell: str) -> str:
    import pkgutil                      # works inside the single-file install too (a zip has no real folders)
    data = pkgutil.get_data("newton", f"shells/newton.{shell}")
    if data is None:
        raise FileNotFoundError(f"shell integration for {shell} is missing from this install")
    return data.decode("utf-8")


def _rc_file(shell: str) -> Path:
    from newton import installer
    return installer.rc_path(shell)


def _init_line(shell: str) -> str:
    return "newton init fish | source" if shell == "fish" else f'eval "$(newton init {shell})"'


def _detect_shell() -> str:
    name = Path(os.environ.get("SHELL", "")).name
    return name if name in SHELLS else "bash"


def _copy(text: str) -> bool:
    for tool in (["pbcopy"], ["wl-copy"], ["xclip", "-selection", "clipboard"], ["xsel", "-b"], ["clip.exe"]):
        if shutil.which(tool[0]):
            try:
                subprocess.run(tool, input=text.encode(), check=True)
                return True
            except (OSError, subprocess.CalledProcessError):
                continue
    return False


# ----------------------------------------------------------------------------- commands

def cmd_suggest(args: argparse.Namespace) -> int:
    desc = " ".join(args.words).strip()
    if not desc and not sys.stdin.isatty():
        desc = sys.stdin.read().strip()
    if not desc:
        ui.err("Describe what you want, e.g. " + ui.bold('newton "kill whatever is using port 3000"'))
        return 2

    if args.porcelain:  # machine-readable output consumed by the shell widgets
        try:
            s = engine.suggest(desc, shell=args.shell, use_cache=not args.no_cache)
        except NewtonError as e:
            print(f"err\t{e}")
            return 1
        except Exception as e:  # never break the user's prompt with a traceback
            print(f"err\tUnexpected error: {e}")
            return 1
        print(f"cmd\t{s.command}")
        for a in s.alternatives:
            print(f"alt\t{a}")
        if s.explanation:
            print(f"note\t{s.explanation}")
        if s.danger:
            print(f"warn\t{s.danger}")
        return 0

    try:
        s = engine.suggest(desc, shell=args.shell, use_cache=not args.no_cache)
    except NewtonError as e:
        ui.err(str(e))
        return 1

    if args.json:
        print(json.dumps(s.to_dict(), indent=2))
        return 0

    print()
    print(f"  {ui.green('❯')} {ui.cmd(s.command)}")
    if s.explanation:
        print(f"    {ui.grey(s.explanation)}")
    if s.danger:
        print(f"    {ui.WARN} {ui.amber(s.danger)}")
    if s.alternatives:
        print()
        print(f"  {ui.grey('alternatives')}")
        for a in s.alternatives:
            print(f"  {ui.DOT} {a}")
    meta = "cached" if s.cached else f"{s.elapsed_ms} ms"
    print()
    if args.copy:
        print(f"  {ui.CHECK} {ui.grey('copied to clipboard')}" if _copy(s.command) else f"  {ui.CROSS} {ui.grey('no clipboard tool found')}")
    else:
        print(f"  {ui.grey('tip: type it in your prompt and press Tab to drop the command right in · ' + meta)}")
    print()
    return 0


def cmd_explain(args: argparse.Namespace) -> int:
    command = " ".join(args.words).strip()
    if not command:
        ui.err("Give me a command to explain, e.g. " + ui.bold("newton explain 'tar -xzvf a.tgz'"))
        return 2
    try:
        data = engine.explain(command)
    except NewtonError as e:
        ui.err(str(e))
        return 1
    print()
    print(f"  {ui.green('❯')} {ui.bold(command)}")
    print(f"    {data.get('summary', '')}")
    print()
    parts = data.get("parts") or []
    width = min(28, max((len(str(p.get('part', ''))) for p in parts), default=0))
    for p in parts:
        part = str(p.get("part", ""))
        print(f"  {ui.lime(part.ljust(width))}  {ui.grey(str(p.get('meaning', '')))}")
    if data.get("danger"):
        print()
        print(f"  {ui.WARN} {ui.amber(data['danger'])}")
    print()
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    shell = args.shell or _detect_shell()
    if shell not in SHELLS:
        ui.err(f"Unsupported shell '{shell}'. Newton supports: {', '.join(SHELLS)}")
        return 2
    sys.stdout.write(_shell_script(shell))
    return 0


def _ask(prompt: str, default: str = "") -> str:
    suffix = f" {ui.grey('[' + default + ']')}" if default else ""
    try:
        val = input(f"  {prompt}{suffix} ").strip()
    except EOFError:
        val = ""
    return val or default


def cmd_setup(args: argparse.Namespace) -> int:
    print(ui.banner())
    print(f"  {ui.bold('Step 1 · Pick your AI')}")
    keys = list(cfgmod.PROVIDERS)
    for i, k in enumerate(keys, 1):
        print(f"   {ui.lime(str(i))}  {cfgmod.PROVIDERS[k]['label']}")
    choice = _ask("Choice", "1")
    provider = keys[int(choice) - 1] if choice.isdigit() and 1 <= int(choice) <= len(keys) else "anthropic"
    prov = cfgmod.PROVIDERS[provider]
    patch = {"provider": provider}

    print()
    if prov["key_env"]:
        print(f"  {ui.bold('Step 2 · API key')}")
        existing = os.environ.get(prov["key_env"], "")
        if existing:
            print(f"  {ui.CHECK} Found {prov['key_env']} in your environment — Newton will use it.")
        else:
            hint = "console.anthropic.com" if provider == "anthropic" else "your provider's dashboard"
            print(f"  {ui.grey('Get one at ' + hint + '. It is stored locally in ' + str(cfgmod.config_path()) + ' (chmod 600).')}")
            try:
                key = getpass.getpass("  Paste key (hidden): ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return 1
            if key:
                patch["api_key"] = key
        if provider == "openai":
            base = _ask("Base URL", prov["base_url"])
            patch["base_url"] = base
    else:
        print(f"  {ui.bold('Step 2 · Local model')}")
        patch["model"] = _ask("Ollama model", prov["model"])

    path = cfgmod.save(patch)
    print(f"  {ui.CHECK} Saved {ui.grey(str(path))}")

    print()
    print(f"  {ui.bold('Step 3 · Test connection')}")
    try:
        ms = engine.ping()
        print(f"  {ui.CHECK} Connected · {ms} ms round trip")
    except NewtonError as e:
        print(f"  {ui.CROSS} {e}")
        print(f"  {ui.grey('You can fix this later and run `newton doctor`.')}")

    print()
    print(f"  {ui.bold('Step 4 · Shell integration')}")
    shell = _ask(f"Your shell ({'/'.join(SHELLS)})", _detect_shell())
    if shell not in SHELLS:
        shell = _detect_shell()
    from newton import installer
    rc = _rc_file(shell)
    line = _init_line(shell)
    exe = installer.current_executable()
    bin_dir = exe.parent if exe else installer.default_bin_dir()
    if installer.init_enabled(shell):
        print(f"  {ui.CHECK} Already enabled in {rc}")
    elif _ask(f"Add Newton to {rc}? (y/n)", "y").lower().startswith("y"):
        try:
            installer.ensure_block(shell, bin_dir, init=True)
            print(f"  {ui.CHECK} Added to {rc}  {ui.grey('(remove any time with: newton uninstall)')}")
        except OSError as e:
            print(f"  {ui.CROSS} Couldn't edit {rc}: {e}\n  Add this line yourself:\n    {ui.lime(line)}")
    else:
        print(f"  Add this line to {rc} yourself:\n    {ui.lime(line)}")

    print()
    print(f"  {ui.green('You are all set.')} Open a new terminal, then try:")
    print(f"    {ui.grey('$')} find every file over 100MB in my home folder{ui.lime('⇥')}")
    print()
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    cfg = cfgmod.load()
    ok = True
    print()
    from newton import installer
    print(f"  {ui.bold('Newton')} {ui.grey('v' + __version__)}   {ui.grey(sys.executable)}")
    print()
    exe = installer.current_executable()
    print(f"  {ui.CHECK} Install     {ui.grey('single file · ' + str(exe))}" if exe
          else f"  {ui.CHECK} Install     {ui.grey('python package (pip/dev)')}")
    on_path = shutil.which("newton")
    if not on_path:
        print(f"  {ui.WARN} PATH        `newton` isn't on your PATH here. Open a new terminal, or add {ui.lime('~/.local/bin')} to it.")
    elif exe and Path(on_path).resolve() != exe.resolve():
        print(f"  {ui.WARN} PATH        running {exe}, but your shell finds {on_path} first")
    if sys.version_info < (3, 9):
        ok = False
        print(f"  {ui.CROSS} Python      {sys.version_info[0]}.{sys.version_info[1]} is too old (needs 3.9+)")
    print(f"  {ui.CHECK} Config      {ui.grey(str(cfgmod.config_path()))}" if cfgmod.config_path().exists()
          else f"  {ui.WARN} Config      {ui.grey('none yet — using defaults (run `newton setup`)')}")
    print(f"  {ui.CHECK} Provider    {cfgmod.PROVIDERS[cfg['provider']]['label']} · {cfg['model']}")
    needs_key = bool(cfgmod.PROVIDERS[cfg["provider"]]["key_env"])
    if needs_key:
        if cfg["api_key"]:
            masked = cfg["api_key"][:7] + "…" + cfg["api_key"][-4:] if len(cfg["api_key"]) > 12 else "set"
            print(f"  {ui.CHECK} API key     {ui.grey(masked)}")
        else:
            ok = False
            print(f"  {ui.CROSS} API key     missing — run `newton setup`")
    try:
        ms = engine.ping(cfg)
        print(f"  {ui.CHECK} Connection  {ms} ms")
    except NewtonError as e:
        ok = False
        print(f"  {ui.CROSS} Connection  {e}")
    for sh in SHELLS:
        rc = _rc_file(sh)
        if rc.exists() and "newton init" in rc.read_text(errors="ignore"):
            print(f"  {ui.CHECK} {sh.ljust(11)} enabled in {ui.grey(str(rc))}")
    active = os.environ.get("NEWTON_SHELL_INTEGRATION")
    print(f"  {ui.CHECK} This shell  Tab integration active ({active})" if active
          else f"  {ui.WARN} This shell  integration not loaded here — open a new terminal or run: {ui.lime(_init_line(_detect_shell()))}")
    print()
    return 0 if ok else 1


def cmd_update(args: argparse.Namespace) -> int:
    from newton import installer
    return installer.update(args.source, force=args.force, yes=args.yes)


def cmd_uninstall(args: argparse.Namespace) -> int:
    from newton import installer
    return installer.uninstall(purge=args.purge, yes=args.yes)


def cmd_history(args: argparse.Namespace) -> int:
    rows = engine.read_history(args.limit)
    if not rows:
        print(ui.grey("  No history yet."))
        return 0
    print()
    for r in rows:
        print(f"  {ui.grey(r.get('q', ''))}")
        print(f"  {ui.green('❯')} {r.get('cmd', '')}")
        print()
    return 0


def cmd_config(args: argparse.Namespace) -> int:
    if not args.key:
        cfg = cfgmod.load()
        if cfg.get("api_key"):
            cfg["api_key"] = cfg["api_key"][:7] + "…"
        print(json.dumps(cfg, indent=2))
        return 0
    if args.value is None:
        print(cfgmod.load().get(args.key, ""))
        return 0
    if args.key not in cfgmod.DEFAULTS:
        ui.err(f"Unknown setting '{args.key}'. Known: {', '.join(cfgmod.DEFAULTS)}")
        return 2
    val: object = args.value
    default = cfgmod.DEFAULTS[args.key]
    if isinstance(default, bool):
        val = args.value.lower() in ("1", "true", "yes", "on")
    elif isinstance(default, int):
        val = int(args.value)
    cfgmod.save({args.key: val})
    print(f"{ui.CHECK} {args.key} = {val}")
    return 0


# ----------------------------------------------------------------------------- v2 commands

def cmd_plan(args: argparse.Namespace) -> int:
    from newton import planrun
    goal = " ".join(args.words).strip()
    if not goal:
        if sys.stdin.isatty() and sys.stdout.isatty():
            return planrun.interactive_entry(cfgmod.load(), auto=args.yes)
        ui.err("Describe your goal, e.g. " + ui.bold("newton plan set up a python project with tests and a linter"))
        return 2
    return planrun.start(goal, cfgmod.load(), auto=args.yes, dry=args.dry_run, as_json=args.json)


def cmd_resume(args: argparse.Namespace) -> int:
    from newton import planrun
    return planrun.resume(args.id, cfgmod.load(), auto=args.yes)


def cmd_status(args: argparse.Namespace) -> int:
    from newton import planrun
    return planrun.show_status(args.id, markdown=args.md)


def cmd_plans(args: argparse.Namespace) -> int:
    from newton import planrun, planstore
    if args.action in (None, "list"):
        return planrun.list_all()
    if args.action == "undo":
        return planrun.undo(args.id, cfgmod.load())
    if args.action == "export":
        return planrun.export(args.id, "md" if args.md else "sh", args.output)
    if not args.id:
        ui.err(f"Which plan? e.g. newton plans {args.action} <id>")
        return 2
    if args.action == "show":
        return planrun.show_status(args.id)
    if planstore.delete(args.id):
        print(f"{ui.CHECK} deleted")
        return 0
    ui.err(f"No plan matches '{args.id}'.")
    return 1


def cmd_prompt(args: argparse.Namespace) -> int:
    from newton import planrun
    text = planrun.badge()
    if text:
        print(text)
    return 0


def cmd_ask(args: argparse.Namespace) -> int:
    from newton import brain, chat, safety
    cfg = cfgmod.load()
    question = " ".join(args.words).strip()
    piped = "" if sys.stdin.isatty() else sys.stdin.read()
    if not question and not piped.strip() and not args.file:
        ui.err("Ask something, e.g. " + ui.bold('newton ask "why does my docker build keep failing?"')
               + "  (you can also pipe text in:  npm test 2>&1 | newton ask what broke)")
        return 2
    parts = ["Environment:\n" + brain.env_block(cfg, os.path.basename(os.environ.get("SHELL", "bash")))]
    for path in args.file or []:
        try:
            parts.append(f"File {path}:\n```\n{chat.read_file_for_ai(path, args.force)}\n```")
        except NewtonError as e:
            ui.err(str(e))
            return 1
    if piped.strip():
        parts.append("Piped input:\n```\n" + safety.redact(piped[-20000:]) + "\n```")
    parts.append("Question: " + (question or "Explain this and point out any problems."))
    try:
        brain.answer(cfg, [{"role": "user", "content": "\n\n".join(parts)}])
    except NewtonError as e:
        ui.err(str(e))
        return 1
    return 0


def cmd_chat(args: argparse.Namespace) -> int:
    from newton import chat
    return chat.chat(cfgmod.load())


def cmd_agent(args: argparse.Namespace) -> int:
    from newton import agent_server
    cfg = cfgmod.load()
    cwd = os.path.abspath(os.path.expanduser(args.dir or os.getcwd()))
    if not os.path.isdir(cwd):
        ui.err(f"That folder doesn't exist: {cwd}")
        return 1
    return agent_server.serve(cfg, cwd, port=args.port, open_browser=not args.no_open, mode="ask" if args.ask else "smart")


def cmd_fix(args: argparse.Namespace) -> int:
    from newton import fixcmd
    return fixcmd.fix(cfgmod.load(), " ".join(args.words).strip() or None)


def cmd_commit(args: argparse.Namespace) -> int:
    from newton import gitcmds
    return gitcmds.commit(cfgmod.load(), stage_all=args.all, yes=args.yes)


# ----------------------------------------------------------------------------- entry point

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="newton", description="Think it. Tab it. Done.", formatter_class=argparse.RawDescriptionHelpFormatter,
                                epilog="examples:\n  newton find files bigger than 100mb\n  newton plan set up a python project with tests\n  npm test 2>&1 | newton ask what broke\n  newton fix\n  newton commit")
    p.add_argument("--version", action="version", version=f"newton {__version__}")
    sub = p.add_subparsers(dest="command")

    s = sub.add_parser("suggest", help="turn a description into a command (default)")
    s.add_argument("words", nargs="*")
    s.add_argument("--shell", choices=SHELLS)
    s.add_argument("--porcelain", action="store_true", help=argparse.SUPPRESS)
    s.add_argument("--json", action="store_true", help="print the full suggestion as JSON")
    s.add_argument("-c", "--copy", action="store_true", help="copy the command to the clipboard")
    s.add_argument("--no-cache", action="store_true", help="ignore cached answers")
    s.set_defaults(func=cmd_suggest)

    e = sub.add_parser("explain", help="explain what a command does")
    e.add_argument("words", nargs="*")
    e.set_defaults(func=cmd_explain)

    i = sub.add_parser("init", help="print shell integration")
    i.add_argument("shell", nargs="?", choices=SHELLS)
    i.set_defaults(func=cmd_init)

    sub.add_parser("setup", help="guided setup").set_defaults(func=cmd_setup)
    sub.add_parser("doctor", help="check your installation").set_defaults(func=cmd_doctor)

    h = sub.add_parser("history", help="recent translations")
    h.add_argument("-n", "--limit", type=int, default=15)
    h.set_defaults(func=cmd_history)

    c = sub.add_parser("config", help="view or change settings")
    c.add_argument("key", nargs="?")
    c.add_argument("value", nargs="?")
    c.set_defaults(func=cmd_config)

    pl = sub.add_parser("plan", help="turn a goal into a checklist and work through it, step by step")
    pl.add_argument("words", nargs="*")
    pl.add_argument("-y", "--yes", action="store_true", help="auto-run safe steps (risky steps still ask)")
    pl.add_argument("--dry-run", action="store_true", help="show the plan without saving or running it")
    pl.add_argument("--json", action="store_true", help="print the plan as JSON")
    pl.set_defaults(func=cmd_plan)

    rs = sub.add_parser("resume", help="continue the plan you were working on")
    rs.add_argument("id", nargs="?")
    rs.add_argument("-y", "--yes", action="store_true")
    rs.set_defaults(func=cmd_resume)

    st = sub.add_parser("status", help="show your current plan's checklist")
    st.add_argument("id", nargs="?")
    st.add_argument("--md", action="store_true", help="print as a Markdown checklist")
    st.set_defaults(func=cmd_status)

    ps = sub.add_parser("plans", help="list, show or delete saved plans")
    ps.add_argument("action", nargs="?", choices=["list", "show", "rm", "undo", "export"])
    ps.add_argument("id", nargs="?")
    ps.add_argument("--md", action="store_true", help="export: markdown checklist instead of a shell script")
    ps.add_argument("-o", "--output", help="export: write to this file instead of printing")
    ps.set_defaults(func=cmd_plans)

    sub.add_parser("prompt", help="one-line plan badge for your shell prompt").set_defaults(func=cmd_prompt)

    up = sub.add_parser("update", help="update Newton from a downloaded zip, a folder or an https address")
    up.add_argument("source", nargs="?", help="newton.zip, a folder, or https://… (default: the newest newton*.zip in ~/Downloads)")
    up.add_argument("--force", action="store_true", help="reinstall even if the version isn't newer")
    up.add_argument("-y", "--yes", action="store_true", help="don't ask for confirmation")
    up.set_defaults(func=cmd_update)

    un = sub.add_parser("uninstall", help="remove Newton and its shell config lines")
    un.add_argument("--purge", action="store_true", help="also delete settings, API key, history and saved plans")
    un.add_argument("-y", "--yes", action="store_true", help="don't ask for confirmation")
    un.set_defaults(func=cmd_uninstall)

    ak = sub.add_parser("ask", help="ask a question (pipe text in, attach files with -f)")
    ak.add_argument("words", nargs="*")
    ak.add_argument("-f", "--file", action="append", help="attach a file (repeatable)")
    ak.add_argument("--force", action="store_true", help="allow attaching files that look like secrets")
    ak.set_defaults(func=cmd_ask)

    sub.add_parser("chat", help="a conversation that knows your machine").set_defaults(func=cmd_chat)

    ag = sub.add_parser("agent", help="open the agent app: give it a goal and it works through it, asking before it changes anything")
    ag.add_argument("--dir", help="folder to work in (default: here)")
    ag.add_argument("--port", type=int, default=0, help="port to listen on (default: any free port)")
    ag.add_argument("--no-open", action="store_true", help="print the link but don't open a browser")
    ag.add_argument("--ask", action="store_true", help="ask before every command, even read-only ones")
    ag.set_defaults(func=cmd_agent)

    fx = sub.add_parser("fix", help="diagnose the command that just failed")
    fx.add_argument("words", nargs="*", help="a command to run and fix (default: your last command)")
    fx.set_defaults(func=cmd_fix)

    cm = sub.add_parser("commit", help="write a commit message from your staged changes")
    cm.add_argument("-a", "--all", action="store_true", help="stage everything first")
    cm.add_argument("-y", "--yes", action="store_true", help="commit without asking")
    cm.set_defaults(func=cmd_commit)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "help":
        argv = ["--help"]
    # `newton find big files` is shorthand for `newton suggest find big files`
    if argv and argv[0] in AMBIGUOUS:
        positional = [a for a in argv[1:] if not a.startswith("-")]
        is_command = not positional or (len(positional) == 1 and (
            "/" in positional[0] or positional[0].startswith("~") or positional[0].lower().endswith((".zip", ".pyz"))))
        if not is_command:
            argv = ["suggest", *argv]
    elif argv and argv[0] not in SUBCOMMANDS and argv[0] not in ("-h", "--help", "--version"):
        argv = ["suggest", *argv]
    if not argv:
        build_parser().print_help()
        return 0
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print()
        return 130
