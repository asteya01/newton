"""`newton fix` — diagnose the command that just failed and offer to run the fix, all in the same tab."""
from __future__ import annotations

import os
from typing import Any, Dict, Optional, Tuple

from newton import brain, planrun, safety, term, ui
from newton.llm import NewtonError
from newton.runner import Session


def last_command() -> Tuple[str, Optional[int]]:
    """The last command you ran in this shell and its exit status (recorded by the shell integration)."""
    cmd = os.environ.get("NEWTON_LAST_CMD", "").strip()
    raw = os.environ.get("NEWTON_LAST_STATUS", "")
    if not cmd:
        path = os.environ.get("NEWTON_LAST_FILE", "")
        try:
            with open(path) as f:
                raw, _, rest = f.read().partition("\n")
            cmd = rest.strip()
        except OSError:
            return "", None
    return cmd, int(raw) if raw.strip().lstrip("-").isdigit() else None


def fix(cfg: Dict[str, Any], command: Optional[str] = None) -> int:
    status: Optional[int] = None
    if command:
        target = command
    else:
        target, status = last_command()
        if not target:
            ui.err("Newton doesn't know your last command in this window. Open a new terminal (so the shell hook loads), "
                   "or pass it: " + ui.bold("newton fix 'npm test'"))
            return 1
        if status == 0:
            print(f"\n  {ui.CHECK} Your last command succeeded (exit 0): {ui.grey(target)}")
            hint = 'newton fix "<command>"'
            print(f"  {ui.grey('To check something specific, pass it:')} {ui.lime(hint)}\n")
            return 0

    sess = Session()
    print()
    print(f"  {ui.grey('command')}  {ui.cmd(target)}" + (f"  {ui.grey('(exit ' + str(status) + ')')}" if status is not None else ""))
    lvl = safety.level(target)
    output, code = "", status if status is not None else 1

    if command or lvl < 2:
        rerun_key = ("y", "re-run it to capture the error") if lvl >= 1 else ("⏎", "re-run it to capture the error")
        print(f"  {ui.grey('Re-running shows Newton the real error. It will execute the command again.')}")
        if lvl:
            print(f"  {ui.WARN} {ui.amber('; '.join(safety.check(target)))}")
        key = term.ask_key(term.menu(rerun_key, ("n", "diagnose from the command alone"), ("q", "cancel")))
        if key in ("q", "esc"):
            return 0
        if key == "y" or (key == "enter" and lvl == 0):
            res = planrun_execute(sess, target)
            output, code = res.output, res.code
            if res.ok:
                print(f"\n  {ui.CHECK} {ui.green('It worked this time')} {ui.grey('(exit 0) — nothing to fix.')}\n")
                return 0
    else:
        note = "That command is destructive, so Newton won't re-run it. Diagnosing from the command alone."
        print(f"  {ui.WARN} {ui.amber(note)}")

    try:
        with term.Spinner("Newton is working out what went wrong"):
            dx = brain.diagnose(cfg, target, code, output, task="The user's last terminal command failed")
    except NewtonError as e:
        ui.err(str(e))
        return 1
    print()
    print(term.wrap(dx["diagnosis"], f"  {ui.red('┃')} "))
    f = dx["fix"]
    if not f:
        print()
        return 0
    print(f"\n  {ui.bold('Suggested fix')}  {ui.grey(f['title'])}  {planrun.RISK_TAG[f['risk']]}")
    planrun.show_command(f["command"])
    while True:
        runkey = ("y", "run fix — danger") if f["risk"] == "danger" else ("⏎", "run fix")
        key = term.ask_key(term.menu(runkey, ("e", "edit"), ("n", "no thanks")))
        if key in ("n", "q", "esc"):
            print()
            return 0
        if key == "e":
            new = term.edit_command(f["command"])
            if new:
                f["command"], f["risk"] = new, brain.risk_for(f["risk"], new)
                planrun.show_command(new)
            continue
        if key == "y" or (key == "enter" and f["risk"] != "danger"):
            break
    res = planrun_execute(sess, f["command"])
    if res.ok and dx["then"] == "retry":
        print(f"  {ui.grey('fix applied — re-running your original command…')}")
        res = planrun_execute(sess, target)
    if res.ok:
        verdict = f"{ui.CHECK} {ui.green('All good')}"
    else:
        verdict = f"{ui.CROSS} {ui.red('Still failing')} {ui.grey('(exit ' + str(res.code) + ') — run newton fix again for another look')}"
    print(f"\n  {verdict}\n")
    return 0 if res.ok else 1


def planrun_execute(sess: Session, command: str):
    rule = max(10, term.width() - 14)
    print(f"\n  {ui.grey('─ running ' + '─' * rule)}")
    res = sess.run(command)
    print(f"  {ui.grey('─' * (rule + 9))}")
    return res
