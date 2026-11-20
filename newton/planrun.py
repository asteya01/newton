"""Plan mode — a checklist you work through one reviewed step at a time.

The goal and a live progress checklist are redrawn before every step so you always know where you
are. Each step is shown before it runs (run / edit / skip / explain / ask / revise / pause). When a
step fails, Newton reads the output, explains what went wrong and proposes a fix you can run.
"""
from __future__ import annotations

import os
import shlex
import shutil
import sys
import time
from typing import Any, Dict, List, Optional

from newton import __version__, brain, engine, planstore, safety, term, ui
from newton.llm import NewtonError
from newton.runner import RunResult, Session

BAR = 28
RISK_TAG = {"safe": "", "caution": ui.amber("▲ caution"), "danger": ui.red("▲ danger")}


# ----------------------------------------------------------------------------- drawing

def _icon(status: str, current: bool = False) -> str:
    if current:
        return ui.lime("▸")
    return {"done": ui.green("✓"), "skipped": ui.amber("↷"), "failed": ui.red("✗"), "undone": ui.grey("↶")}.get(status, ui.grey("○"))


def checklist(plan: Dict[str, Any], cur: Optional[int] = None, header: bool = True, times: bool = False) -> None:
    steps, w = plan["steps"], term.width()
    done, n = planstore.progress(plan)
    pct = int(100 * done / n) if n else 100
    if header:
        filled = round(BAR * done / n) if n else BAR
        where = f"step {min((cur if cur is not None else done) + 1, n)} of {n}" if cur is not None else f"{done} of {n} done"
        print(f"  {ui.lime('◆')} {ui.bold(term.trunc(plan['goal'], w - 36))}   {ui.grey(where + ' · ' + str(pct) + '%')}")
        print(f"  {ui.green('━' * filled)}{ui.grey('─' * (BAR - filled))}")
    for i, s in enumerate(steps):
        took = s.get("seconds", 0) if times and s["status"] == "done" else 0
        stamp = "  " + ui.grey(_fmt_time(took)) if took >= 1 else ""
        line = f"{i + 1:>2}  {term.trunc(s['title'], w - (22 if stamp else 14))}"
        if s["status"] in ("done", "skipped", "undone"):
            line = ui.grey(line)
        elif i == cur:
            line = ui.bold(line)
        tag = "  " + RISK_TAG[s["risk"]] if s["risk"] != "safe" and s["status"] == "pending" else ""
        print(f"  {_icon(s['status'], i == cur)} {line}{tag}{stamp}")


def render_header(plan: Dict[str, Any], cur: int) -> None:
    print()
    print(ui.grey("  " + "─" * (term.width() - 4)))
    checklist(plan, cur)


def show_command(command: str) -> None:
    for j, line in enumerate(command.splitlines() or [""]):
        print(f"  {ui.green('❯') if j == 0 else ' '} {ui.cmd(line)}")


def show_step(plan: Dict[str, Any], idx: int) -> None:
    s, n = plan["steps"][idx], len(plan["steps"])
    print()
    print(f"  {ui.bold('Step ' + str(idx + 1))} {ui.grey('of ' + str(n))}  {ui.bold(s['title'])}  {RISK_TAG[s['risk']]}")
    if s["why"]:
        print(f"  {ui.grey('why')}  {s['why']}")
    if s.get("manual") and not s.get("command"):
        print(f"  {ui.amber('you')}  {s['manual']}")
        return
    show_command(s["command"])
    warn = safety.check(s["command"], notes=False)
    if warn:
        print(f"  {ui.WARN} {ui.amber('; '.join(warn))}")


def overview(plan: Dict[str, Any]) -> None:
    print()
    print(f"  {ui.lime('◆')} {ui.bold(plan['goal'])}")
    if plan.get("summary"):
        print(term.wrap(plan["summary"], "    "))
    if plan.get("assumptions"):
        print()
        print(f"  {ui.grey('assuming')}")
        for a in plan["assumptions"]:
            print(f"  {ui.grey('·')} {ui.grey(a)}")
    print()
    checklist(plan, header=False)
    needs = plan.get("requires") or []
    if needs:
        marks = "   ".join((ui.green("✓") if shutil.which(n) else ui.amber("✗")) + " " + n for n in needs)
        print("\n  " + ui.grey("needs") + "  " + marks)
        if any(not shutil.which(n) for n in needs):
            print("  " + ui.grey("✗ = not found on this machine yet (fine if a step installs it)"))
    care, total = sum(1 for st in plan["steps"] if st["risk"] != "safe"), len(plan["steps"])
    if care:
        print("\n  " + ui.grey("%d of %d steps need care. You approve each one before it runs." % (care, total)))
    print()


# ----------------------------------------------------------------------------- helpers

def _mark(plan: Dict[str, Any], idx: int, status: str, **extra: Any) -> None:
    plan["steps"][idx].update(status=status, **extra)
    planstore.save(plan)


def _fmt_time(sec: float) -> str:
    sec = int(sec)
    return f"{sec // 60}m {sec % 60:02d}s" if sec >= 60 else f"{sec}s"


def _first_open(plan: Dict[str, Any]) -> Optional[int]:
    for i, s in enumerate(plan["steps"]):
        if s["status"] in ("pending", "failed"):
            return i
    return None


def collect_inputs(plan: Dict[str, Any], auto: bool) -> None:
    for inp in plan.get("inputs", []):
        name = inp["name"]
        if name in plan["vars"]:
            continue
        default = inp.get("default", "")
        if auto:
            val = default
            print(f"  {ui.lime(name)}  {ui.grey(inp['prompt'])} {ui.grey('→ ' + default)}")
        else:
            hint = ui.grey(f"[{default}] ") if default else ""
            val = term.ask_line(f"  {ui.lime(name)}  {inp['prompt']} {hint}", default=default)
        plan["vars"][name] = val


def execute(plan: Dict[str, Any], step: Dict[str, Any], sess: Session, command: Optional[str] = None) -> RunResult:
    cmd = command if command is not None else step["command"]
    rule = max(10, term.width() - 14)
    print(f"\n  {ui.grey('─ running ' + '─' * rule)}")
    if command is None:
        step["ran_in"] = sess.cwd                       # where this step started, so `plans undo` can run its undo there
    res = sess.run(cmd)
    print(f"  {ui.grey('─' * (rule + 9))}")
    plan["elapsed"] = plan.get("elapsed", 0) + res.seconds
    step["seconds"] = step.get("seconds", 0) + res.seconds
    if res.seconds >= 15:
        term.bell()                                     # long step finished: nudge the user back to this tab
    if res.ok and command is None and step.get("verify"):
        chk = sess.run(step["verify"], quiet=True, persist=False)
        if not chk.ok:
            print(f"  {ui.CROSS} the step ran, but its check failed: {ui.grey(step['verify'])}")
            res = RunResult(1, f"The command succeeded but this verification failed: {step['verify']}\n{chk.output}",
                            res.seconds, False, sess.cwd)
    return res


def ask_about(plan: Dict[str, Any], idx: int, cfg: Dict[str, Any], output: str = "") -> None:
    q = term.ask_line(f"  {ui.green('ask ›')} ")
    if not q:
        return
    step = plan["steps"][idx]
    steps = "; ".join(f"{i + 1}. {s['title']} [{s['status']}]" for i, s in enumerate(plan["steps"]))
    msg = (f"Environment:\n{brain.env_block(cfg)}\n\nI'm working through a terminal plan: {plan['goal']}.\nSteps: {steps}\n"
           f"Current step: {step['title']}\nCommand: {step.get('command') or step.get('manual')}\n"
           + (f"Last output:\n{safety.redact(output)}\n" if output else "") + f"\nQuestion: {q}")
    try:
        brain.answer(cfg, [{"role": "user", "content": msg}])
    except NewtonError as e:
        print(f"  {ui.CROSS} {e}")


def explain_step(step: Dict[str, Any], cfg: Dict[str, Any]) -> None:
    try:
        with term.Spinner("Newton is explaining"):
            data = engine.explain(step["command"], cfg)
        term.render_explain(step["command"], data)
    except NewtonError as e:
        print(f"  {ui.CROSS} {e}")


def revise(plan: Dict[str, Any], cfg: Dict[str, Any]) -> bool:
    fb = term.ask_line(f"  {ui.green('what should change? ›')} ")
    if not fb:
        return False
    try:
        with term.Spinner("Newton is revising the plan"):
            steps, inputs = brain.revise_plan(plan, fb, cfg)
    except NewtonError as e:
        print(f"  {ui.CROSS} {e}")
        return False
    plan["steps"] = [s for s in plan["steps"] if s["status"] in ("done", "skipped")] + steps
    known = {i["name"] for i in plan.get("inputs", [])}
    plan.setdefault("inputs", []).extend(i for i in inputs if i["name"] not in known)
    collect_inputs(plan, auto=False)
    planstore.save(plan)
    print(f"  {ui.CHECK} plan updated")
    return True


# ----------------------------------------------------------------------------- failure handling

def heal(plan: Dict[str, Any], idx: int, sess: Session, cfg: Dict[str, Any], res: RunResult) -> str:
    """Runs after a step fails. Returns 'next' when the step is resolved, 'quit' to pause."""
    step = plan["steps"][idx]
    cur_cmd = step["command"]
    diagnoses = 0
    while True:
        if res.ok:
            _mark(plan, idx, "done")
            print(f"  {ui.CHECK} {ui.green('step fixed')}")
            return "next"

        if res.interrupted:
            print(f"\n  {ui.WARN} {ui.amber('Interrupted.')}")
            key = term.ask_key(term.menu(("r", "retry"), ("s", "skip"), ("d", "mark done"), ("q", "pause")))
            if key == "r":
                res = execute(plan, step, sess)
            elif key == "s":
                _mark(plan, idx, "skipped")
                return "next"
            elif key == "d":
                _mark(plan, idx, "done")
                return "next"
            else:
                return "quit"
            continue

        _mark(plan, idx, "failed", exit=res.code, tail=res.output[-1500:])
        print(f"\n  {ui.CROSS} {ui.red('Step failed')} {ui.grey('(exit ' + str(res.code) + ')')}")

        dx: Optional[Dict[str, Any]] = None
        if cfg.get("share_output", True) and diagnoses < 3:
            diagnoses += 1
            try:
                with term.Spinner("Newton is working out what went wrong"):
                    dx = brain.diagnose(cfg, cur_cmd, res.code, res.output, task=f"{plan['goal']} — {step['title']}")
            except NewtonError as e:
                print(f"  {ui.grey(str(e))}")
        fix = dx["fix"] if dx else None
        if dx:
            print()
            print(term.wrap(dx["diagnosis"], f"  {ui.red('┃')} "))
        if fix:
            print(f"\n  {ui.bold('Suggested fix')}  {ui.grey(fix['title'])}  {RISK_TAG[fix['risk']]}")
            show_command(fix["command"])

        # One menu per failure; actions that run something set `res` and drop back to the outer loop.
        while True:
            if fix:
                runkey = ("y", "run fix — danger") if fix["risk"] == "danger" else ("⏎", "run fix")
                key = term.ask_key(term.menu(runkey, ("e", "edit fix"), ("r", "retry as-is"), ("s", "skip step"), ("a", "ask"), ("q", "pause")))
            else:
                key = term.ask_key(term.menu(("r", "retry"), ("e", "edit command"), ("s", "skip step"), ("a", "ask"),
                                             ("d", "diagnose again"), ("q", "pause")))
            if key in ("q", "esc"):
                return "quit"
            if key == "s":
                _mark(plan, idx, "skipped")
                return "next"
            if key == "a":
                ask_about(plan, idx, cfg, res.output)
                continue
            if key == "d" and not fix:
                diagnoses = min(diagnoses, 2)
                break
            if key == "r":
                res, cur_cmd = execute(plan, step, sess), step["command"]
                break
            if key == "e":
                target = fix["command"] if fix else step["command"]
                new = term.edit_command(target)
                if not new:
                    continue
                if fix:
                    fix["command"], fix["risk"] = new, brain.risk_for(fix["risk"], new)
                    show_command(new)
                    continue
                step["command"] = new
                step["risk"] = brain.risk_for(step["risk"], new)
                res, cur_cmd = execute(plan, step, sess), new
                break
            if fix and (key == "y" or (key == "enter" and fix["risk"] != "danger")):
                fres = execute(plan, step, sess, command=fix["command"])
                if not fres.ok:
                    res, cur_cmd = fres, fix["command"]
                    break
                if dx and dx["then"] == "next":
                    _mark(plan, idx, "done")
                    print(f"  {ui.CHECK} {ui.green('fixed — moving on')}")
                    return "next"
                print(f"  {ui.grey('fix worked — retrying the original step…')}")
                res, cur_cmd = execute(plan, step, sess), step["command"]
                break
            if key == "enter" and fix:
                print(f"  {ui.grey('This fix is marked danger — press y to run it.')}")


# ----------------------------------------------------------------------------- one step

def do_step(plan: Dict[str, Any], idx: int, sess: Session, cfg: Dict[str, Any], auto: bool) -> str:
    step = plan["steps"][idx]
    show_step(plan, idx)
    manual = bool(step.get("manual")) and not step.get("command")
    while True:
        risk = step["risk"]
        if manual:
            key = term.ask_key(term.menu(("⏎", "done"), ("s", "skip"), ("a", "ask"), ("r", "revise"), ("q", "pause")))
        elif auto and risk == "safe":
            print(f"  {ui.grey('auto-running (safe step)')}")
            key = "enter"
        else:
            runkey = ("y", "run — danger") if risk == "danger" else ("⏎", "run")
            key = term.ask_key(term.menu(runkey, ("e", "edit"), ("s", "skip"), ("?", "explain"), ("a", "ask"), ("r", "revise"), ("q", "pause")))

        if key in ("q", "esc"):
            return "quit"
        if key == "s":
            _mark(plan, idx, "skipped")
            print(f"  {ui.amber('↷')} {ui.grey('skipped')}")
            return "next"
        if key == "a":
            ask_about(plan, idx, cfg)
            continue
        if key == "r":
            if revise(plan, cfg):
                return "revised"
            continue
        if manual:
            if key in ("enter", "d", "y"):
                _mark(plan, idx, "done")
                print(f"  {ui.CHECK} {ui.grey('marked done')}")
                return "next"
            continue
        if key == "?":
            explain_step(step, cfg)
            continue
        if key == "e":
            new = term.edit_command(step["command"])
            if new:
                step["command"] = new
                step["risk"] = brain.risk_for(step["risk"], new)
                show_step(plan, idx)
            continue
        if key == "enter" and risk == "danger":
            print(f"  {ui.grey('This step is marked danger — press y to run it, or s to skip.')}")
            continue
        if key in ("enter", "y"):
            res = execute(plan, step, sess)
            if res.ok:
                _mark(plan, idx, "done", exit=0)
                print(f"  {ui.CHECK} {ui.green('done')} {ui.grey('in ' + _fmt_time(res.seconds))}")
                return "next"
            return heal(plan, idx, sess, cfg, res)


# ----------------------------------------------------------------------------- the loop

def _title(plan: Dict[str, Any], state: str = "") -> None:
    done, n = planstore.progress(plan)
    term.set_title("◆ %s · %s" % (term.trunc(plan["goal"], 40), state or "%d/%d" % (done, n)))


def _check_cwd(plan: Dict[str, Any]) -> bool:
    """A resumed plan whose folder was moved or deleted must never silently run somewhere else."""
    cwd = plan.get("cwd") or ""
    if cwd and os.path.isdir(cwd):
        return True
    here = os.getcwd()
    print(f"\n  {ui.WARN} {ui.amber('This plan was working in a folder that no longer exists:')}")
    print(f"    {ui.grey(cwd or '(unknown)')}")
    key = term.ask_key(term.menu(("h", "continue here: " + term.trunc(here, 40)), ("q", "pause")))
    if key != "h":
        return False
    plan["cwd"] = here
    planstore.save(plan)
    return True


def run(plan: Dict[str, Any], cfg: Dict[str, Any], auto: bool = False) -> int:
    if not _check_cwd(plan):
        return pause(plan)
    sess = Session(cwd=plan.get("cwd"), env={**os.environ, **plan.get("vars", {})})
    shell_cwd = os.getcwd()
    plan["status"] = "active"
    planstore.save(plan)
    try:
        while True:
            idx = _first_open(plan)
            if idx is None:
                break
            render_header(plan, idx)
            _title(plan)
            outcome = do_step(plan, idx, sess, cfg, auto)
            plan["cwd"] = sess.cwd
            planstore.save(plan)
            if outcome == "quit":
                return pause(plan)
    except KeyboardInterrupt:
        print()
        return pause(plan)

    plan["status"] = "done"
    plan["finished"] = time.time()
    _title(plan, "done ✓")
    plan["cwd"] = sess.cwd
    planstore.save(plan)
    finish(plan, sess.cwd, shell_cwd)
    return 0


def pause(plan: Dict[str, Any]) -> int:
    planstore.save(plan)
    done, n = planstore.progress(plan)
    where = f"at {done} of {n} — {plan['goal']}"
    _title(plan, "paused")
    print(f"\n  {ui.amber('⏸')} {ui.bold('Paused')} {ui.grey(where)}")
    print(f"  {ui.grey('pick it back up any time with:')} {ui.lime('newton resume')}\n")
    return 0


def finish(plan: Dict[str, Any], end_cwd: str, shell_cwd: str) -> None:
    steps = plan["steps"]
    done = sum(1 for s in steps if s["status"] == "done")
    skipped = sum(1 for s in steps if s["status"] == "skipped")
    print()
    print(ui.grey("  " + "─" * (term.width() - 4)))
    checklist(plan, header=False, times=True)
    print()
    print(f"  {ui.CHECK} {ui.green(ui.bold('Plan complete'))}  {ui.grey('— ' + plan['goal'])}")
    detail = f"{len(steps)} steps · {done} done" + (f" · {skipped} skipped" if skipped else "") + f" · {_fmt_time(plan.get('elapsed', 0))}"
    print(f"    {ui.grey(detail)}")
    if plan.get("after"):
        print(f"\n  {ui.lime('next')}  {plan['after']}")
    if any(st.get("undo") and st["status"] == "done" for st in steps):
        print(f"\n  {ui.grey('changed your mind? roll it back with')} {ui.lime('newton plans undo')}")
    if os.path.realpath(end_cwd) != os.path.realpath(shell_cwd):
        print(f"\n  {ui.grey('the plan ended in a different folder — to follow it:')} {ui.lime('cd ' + end_cwd)}")
    print()


# ----------------------------------------------------------------------------- entry points

def start(goal: str, cfg: Dict[str, Any], auto: bool = False, dry: bool = False, as_json: bool = False) -> int:
    try:
        with term.Spinner("Newton is drafting a plan"):
            data = brain.make_plan(goal, cfg)
    except NewtonError as e:
        ui.err(str(e))
        return 1
    if as_json:
        import json
        print(json.dumps(data, indent=2))
        return 0
    plan = planstore.fresh(goal, data, os.getcwd())
    overview(plan)
    if dry:
        print(f"  {ui.grey('dry run — nothing was saved or executed.')}\n")
        return 0
    try:
        while True:
            key = term.ask_key(term.menu(("⏎", "start"), ("r", "revise first"), ("q", "cancel")))
            if key in ("q", "esc"):
                print(f"  {ui.grey('cancelled — nothing was run.')}\n")
                return 0
            if key == "r":
                if revise(plan, cfg):
                    overview(plan)
                continue
            if key == "enter":
                break
        collect_inputs(plan, auto)
    except KeyboardInterrupt:
        print()
        return 0
    return run(plan, cfg, auto)


def resume(plan_id: Optional[str], cfg: Dict[str, Any], auto: bool = False) -> int:
    plan = planstore.load(plan_id) if plan_id else planstore.current()
    if not plan:
        ui.err("No unfinished plan to resume." if not plan_id else f"No plan matches '{plan_id}'.")
        return 1
    if plan.get("status") == "done":
        print(f"  {ui.CHECK} That plan is already complete.")
        return 0
    if plan.get("status") == "undone":
        print(f"  {ui.grey('That plan was rolled back. Start it again with:')} {ui.lime('newton plan ' + plan.get('request', plan['goal']))}")
        return 0
    done, n = planstore.progress(plan)
    print(f"\n  {ui.lime('◆')} Resuming {ui.bold(plan['goal'])} {ui.grey(f'({done} of {n} done)')}")
    return run(plan, cfg, auto)


def show_status(plan_id: Optional[str] = None, markdown: bool = False) -> int:
    plan = planstore.load(plan_id) if plan_id else planstore.current()
    if not plan:
        print(f"  {ui.grey('No active plan. Start one with:')} {ui.lime('newton plan <goal>')}")
        return 0
    if markdown:
        box = {"done": "x", "skipped": "x", "pending": " ", "failed": " "}
        print(f"# {plan['goal']}\n\n{plan.get('summary', '')}\n")
        for s in plan["steps"]:
            print(f"- [{box.get(s['status'], ' ')}] {s['title']}" + (f" _(skipped)_" if s["status"] == "skipped" else ""))
            if s.get("command"):
                print(f"  ```sh\n  {s['command']}\n  ```")
        return 0
    print()
    checklist(plan, cur=_first_open(plan), times=True)
    print(f"\n  {ui.grey('id ' + plan['id'] + ' · ' + plan['status'] + ' · ' + plan['cwd'])}")
    if plan["status"] == "active":
        print(f"  {ui.grey('continue with')} {ui.lime('newton resume')}")
    print()
    return 0


def list_all() -> int:
    plans = planstore.list_plans()
    if not plans:
        print(f"  {ui.grey('No plans yet. Try:')} {ui.lime('newton plan set up a python project with tests')}")
        return 0
    print()
    for p in plans[:20]:
        done, n = planstore.progress(p)
        age = engine_age(p.get("updated", p["created"]))
        mark = {"done": ui.green("✓"), "active": ui.lime("▸"), "undone": ui.grey("↶"), "abandoned": ui.grey("·")}.get(p.get("status"), ui.grey("·"))
        print(f"  {mark} {ui.bold(term.trunc(p['goal'], 42).ljust(42))} {ui.grey(f'{done}/{n}'.rjust(6))}  {ui.grey(age.ljust(12))} {ui.grey(p['id'])}")
    print()
    return 0


def engine_age(ts: float) -> str:
    s = int(time.time() - ts)
    if s < 90:
        return "just now"
    if s < 3600:
        return f"{s // 60} min ago"
    if s < 86400:
        return f"{s // 3600} hr ago"
    return f"{s // 86400} days ago"


# ----------------------------------------------------------------------------- undo

def _find_for_undo(plan_id: Optional[str]) -> Optional[Dict[str, Any]]:
    if plan_id:
        return planstore.load(plan_id)
    for p in planstore.list_plans():
        if any(st["status"] == "done" and st.get("undo") for st in p["steps"]):
            return p
    return None


def undo(plan_id: Optional[str], cfg: Dict[str, Any]) -> int:
    """Rolls back finished steps, newest first, each one reviewed like a normal step."""
    plan = _find_for_undo(plan_id)
    if not plan:
        ui.err(f"No plan matches '{plan_id}'." if plan_id else "Nothing to undo: no finished plan has reversible steps.")
        return 1
    todo = [i for i in range(len(plan["steps"]) - 1, -1, -1) if plan["steps"][i]["status"] == "done" and plan["steps"][i].get("undo")]
    manual = [st for st in plan["steps"] if st["status"] == "done" and not st.get("undo")]
    if not todo:
        print(f"  {ui.grey('This plan has no steps that can be undone automatically.')}")
        return 0
    print(f"\n  {ui.lime('↶')} {ui.bold('Undoing')} {ui.bold(plan['goal'])} {ui.grey('— newest step first, each one reviewed')}\n")
    sess = Session(cwd=plan.get("cwd"), env={**os.environ, **plan.get("vars", {})})
    undone = 0
    try:
        for n, i in enumerate(todo, 1):
            st = plan["steps"][i]
            cmd = st["undo"]
            risk = brain.risk_for("safe", cmd)
            print(f"  {ui.bold('Undo ' + str(n))} {ui.grey('of ' + str(len(todo)))}  {ui.bold(st['title'])}  {RISK_TAG[risk]}")
            show_command(cmd)
            warn = safety.check(cmd, notes=False)
            if warn:
                print(f"  {ui.WARN} {ui.amber('; '.join(warn))}")
            while True:
                runkey = ("y", "undo — danger") if risk == "danger" else ("⏎", "undo")
                key = term.ask_key(term.menu(runkey, ("e", "edit"), ("s", "skip"), ("q", "stop")))
                if key in ("q", "esc"):
                    raise KeyboardInterrupt
                if key == "s":
                    print(f"  {ui.amber('↷')} {ui.grey('left as it is')}\n")
                    break
                if key == "e":
                    new = term.edit_command(cmd)
                    if new:
                        cmd, risk = new, brain.risk_for("safe", new)
                        show_command(cmd)
                    continue
                if key == "enter" and risk == "danger":
                    print(f"  {ui.grey('This undo is marked danger — press y to run it, or s to skip.')}")
                    continue
                if key in ("enter", "y"):
                    target = st.get("ran_in") or plan.get("cwd") or sess.cwd
                    if not os.path.isdir(target):                      # never run an undo somewhere else
                        st["status"] = "undone"
                        planstore.save(plan)
                        undone += 1
                        print(f"  {ui.grey('that folder no longer exists, so there is nothing left to undo there')}\n")
                        break
                    sess.cwd = target
                    res = sess.run(cmd, persist=False)
                    if res.ok:
                        st["status"] = "undone"
                        planstore.save(plan)
                        undone += 1
                        print(f"  {ui.CHECK} {ui.green('undone')}\n")
                        break
                    print(f"  {ui.CROSS} {ui.red('undo failed')} {ui.grey('(exit ' + str(res.code) + ')')}")
    except KeyboardInterrupt:
        print()
    if undone:
        plan["status"] = "undone"                     # a partly rolled-back plan must not be resumed by accident
        planstore.save(plan)
    print(f"  {ui.grey(f'{undone} of {len(todo)} steps undone.')}")
    if manual:
        print(f"  {ui.grey('No automatic undo for:')} {ui.grey(', '.join(m['title'] for m in manual))}")
    print()
    return 0


# ----------------------------------------------------------------------------- export

def export(plan_id: Optional[str], fmt: str = "sh", out: Optional[str] = None) -> int:
    """Turns a plan into a script you can keep, share or run later (`sh`) or a readable checklist (`md`)."""
    plan = planstore.load(plan_id) if plan_id else (planstore.list_plans() or [None])[0]
    if not plan:
        ui.err("No plan to export." if not plan_id else f"No plan matches '{plan_id}'.")
        return 1
    text = _export_md(plan) if fmt == "md" else _export_sh(plan)
    if out:
        with open(out, "w") as f:
            f.write(text)
        if fmt == "sh":
            os.chmod(out, 0o755)
        print(f"{ui.CHECK} wrote {ui.bold(out)}", file=sys.stderr)
    else:
        sys.stdout.write(text)
    return 0


def _dq(val: str) -> str:
    """Escapes a value for use inside double quotes in bash."""
    for ch in ("\\", '"', "$", "`"):
        val = val.replace(ch, "\\" + ch)
    return val


def _export_sh(plan: Dict[str, Any]) -> str:
    L: List[str] = ["#!/usr/bin/env bash", f"# {plan['goal']}"]
    if plan.get("summary"):
        L.append("# " + plan["summary"])
    L += [f"# Generated by Newton {__version__}. Read it before you run it.", "set -euo pipefail", ""]
    for inp in plan.get("inputs", []):
        val = plan.get("vars", {}).get(inp["name"], inp.get("default", ""))
        L.append("# " + inp["prompt"])
        L.append(': "${%s:=%s}"' % (inp["name"], _dq(val)))
        L.append("export " + inp["name"])
    if plan.get("inputs"):
        L.append("")
    for tool in plan.get("requires", []):
        L.append(f"command -v {shlex.quote(tool)} >/dev/null 2>&1 || echo {shlex.quote('note: ' + tool + ' was not found on this machine')} >&2")
    if plan.get("requires"):
        L.append("")
    for i, st in enumerate(plan["steps"], 1):
        L.append(f"# {i}. {st['title']}" + (f" ({st['risk']})" if st["risk"] != "safe" else ""))
        if st.get("why"):
            L.append(f"#    {st['why']}")
        if st["status"] == "skipped":
            L.append("# (skipped when this plan was run)")
            L += ["# " + ln for ln in st.get("command", "").splitlines()] + [""]
            continue
        if st.get("manual") and not st.get("command"):
            L.append(f"echo {shlex.quote('MANUAL STEP: ' + st['manual'])}")
            L.append('read -r -p "Press Enter when that is done... " _')
        else:
            if st["risk"] == "danger":
                ask = "Step %d (%s) is marked danger. Continue? [y/N] " % (i, st["title"])
                L.append("read -r -p %s _ok; [ \"${_ok:-n}\" = y ] || exit 1" % shlex.quote(ask))
            L.append(st["command"])
            if st.get("verify"):
                L.append(f"{st['verify']} || {{ echo {shlex.quote('check failed after step ' + str(i))} >&2; exit 1; }}")
        L.append("")
    if plan.get("after"):
        L.append(f"echo {shlex.quote('Done. ' + plan['after'])}")
    return "\n".join(L) + "\n"


def _export_md(plan: Dict[str, Any]) -> str:
    L = [f"# {plan['goal']}", ""]
    if plan.get("summary"):
        L += [plan["summary"], ""]
    if plan.get("requires"):
        L += ["**Needs:** " + ", ".join(f"`{r}`" for r in plan["requires"]), ""]
    for i, st in enumerate(plan["steps"], 1):
        box = "x" if st["status"] in ("done", "skipped") else " "
        L.append(f"{i}. [{box}] **{st['title']}**" + (f" — {st['why']}" if st.get("why") else ""))
        if st.get("manual") and not st.get("command"):
            L.append(f"   - Do this yourself: {st['manual']}")
        elif st.get("command"):
            L += ["", "   ```sh"] + ["   " + ln for ln in st["command"].splitlines()] + ["   ```"]
        L.append("")
    if plan.get("after"):
        L.append(f"**Next:** {plan['after']}")
    return "\n".join(L).rstrip() + "\n"


# ----------------------------------------------------------------------------- `newton plan` with no goal

def interactive_entry(cfg: Dict[str, Any], auto: bool = False) -> int:
    cur = planstore.current()
    if cur:
        done, n = planstore.progress(cur)
        print(f"\n  {ui.lime('◆')} Unfinished plan: {ui.bold(cur['goal'])} {ui.grey(f'({done} of {n} done)')}")
        key = term.ask_key(term.menu(("⏎", "resume it"), ("n", "start a new plan"), ("q", "cancel")))
        if key == "enter":
            return resume(None, cfg, auto)
        if key != "n":
            return 0
    try:
        goal = term.ask_line(f"\n  {ui.lime('◆')} {ui.bold('What do you want to get done?')}\n  {ui.green('›')} ")
    except KeyboardInterrupt:
        print()
        return 0
    if not goal:
        return 0
    return start(goal, cfg, auto=auto)


def badge() -> str:
    """Compact one-line label for shell prompts: '◆ goal · 3/7'. Empty when nothing is active. No network."""
    plan = planstore.current()
    if not plan:
        return ""
    done, n = planstore.progress(plan)
    return f"◆ {term.trunc(plan['goal'], 28)} · {done}/{n}"
