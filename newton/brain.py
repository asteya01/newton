"""Everything Newton asks the AI beyond one-line suggestions: plans, revisions, diagnoses, answers, commit messages."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterator, List, Optional, Tuple

from newton.engine import fix_escapes
from newton import context as ctxmod
from newton import llm, safety, term
from newton.llm import NewtonError

PLAN_SYSTEM = """PLAN MODE. You are Newton, a senior engineer who lives in the user's terminal. The user states a goal; you produce a short, correct, step-by-step plan they will execute one reviewed step at a time, right in their terminal.

Reply with ONLY a JSON object (no prose, no code fences):
{
  "goal": "title of at most 7 words",
  "summary": "one sentence: what will be true when the plan is finished",
  "assumptions": ["short strings: things you assumed about their setup"],
  "requires": ["external programs the commands need that may not be installed, e.g. git, node, docker"],
  "inputs": [{"name": "UPPER_SNAKE", "prompt": "question for the user", "default": "sensible default"}],
  "steps": [
    {"title": "imperative, at most 8 words", "why": "at most 18 words", "command": "bash command(s)", "manual": "", "verify": "quick bash check that exits 0 when the step worked, or empty", "undo": "bash command that reverses this step, or empty if there is nothing to reverse", "risk": "safe|caution|danger"}
  ],
  "after": "optional one-line tip for when the plan finishes (a URL to open, a command to try)"
}

Rules:
- Every command runs in bash, not the user's interactive shell. The working directory and exported variables carry over from one step to the next, so a `cd` in one step affects the following ones.
- For anything the user must choose (names, ports, paths) declare an input and use "$NAME" in commands (quote it). Never invent values and never use <angle-bracket> placeholders.
- Make steps non-interactive: pass -y / --yes / --no-input style flags; never open editors or pagers.
- Prefer idempotent steps: `mkdir -p`, `command -v tool >/dev/null || install tool`.
- Use the user's OS, package manager and installed tools (see Environment). Don't reinstall what they already have.
- 3 to 12 steps. One logical action per step. No filler like "open a terminal".
- A step that cannot be a command (create an account, copy a key from a website) has "command": "" and the instruction in "manual".
- "risk": "danger" for anything that deletes data, overwrites files, force-pushes or runs downloaded scripts; "caution" for sudo, installs, opening network services or edits outside the working directory; otherwise "safe".
- "requires": only programs outside the basic OS toolset (not ls, cd, echo, mkdir, cat...). Empty list if none.
- "undo": give one whenever a step creates something (folders, files, packages, containers, git repos). Never write an undo that deletes anything the step didn't create. Empty for read-only steps.
- Never put secrets in commands.
- If the goal is unsafe or impossible, return {"goal": "", "summary": "<why>", "steps": []}."""

REVISE_SYSTEM = """REVISE MODE. You revise the REMAINING steps of a terminal plan according to the user's feedback.

Reply with ONLY a JSON object: {"steps": [ ...step objects... ], "inputs": [ ...optional new inputs... ]}.
Step objects use the same schema as the original plan: title, why, command, manual, verify, undo, risk.
- Replace ALL remaining steps. Do not repeat steps that are already done or skipped.
- Same rules as before: commands run in bash, state carries between steps, use "$NAME" inputs, stay non-interactive, mark risk honestly."""

DIAGNOSE_SYSTEM = """DIAGNOSE MODE. A command failed in the user's terminal. Work out why and give the smallest fix.

Reply with ONLY a JSON object:
{"diagnosis": "one or two plain sentences", "fix": {"title": "at most 8 words", "command": "bash command", "risk": "safe|caution|danger"}, "then": "retry|next", "confidence": "high|medium|low"}
- "fix" is null when you cannot tell or when only the user can resolve it; the diagnosis should then say exactly what to check.
- "then": "retry" means: run the fix, then run the original command again. "next" means the fix replaces the original command entirely.
- The fix must be specific to the evidence (exit code, output, environment). Don't suggest generic things like "reinstall".
- Commands run in bash. Prefer the smallest change; never delete user data to make an error go away."""

COMMIT_SYSTEM = """COMMIT MODE. Write a git commit message for the staged changes.

Reply with ONLY a JSON object: {"subject": "...", "body": "..."}
- subject: imperative mood, at most 70 characters, no trailing period. Follow the style of the recent commit subjects you are shown (for example Conventional Commits like "feat: ..." only if they use it).
- body: empty string for small changes; otherwise 1 to 4 short lines explaining WHY, not a file list.
- Describe what the diff actually does. Don't invent details."""

ASK_SYSTEM = """ASK MODE. You are Newton, a pair-programmer that lives in the user's terminal. Answer for a terminal reader:
- Be direct and concise: lead with the answer, then only the detail that's needed.
- No markdown headings and no tables. Short paragraphs; "-" bullets are fine.
- Put every command or code snippet in a fenced block with a language tag (```bash, ```python ...).
- Commands must fit the user's OS and shell (see Environment).
- If you need to see a file or some output to be sure, say exactly which command to run to show it.
- If the user wants a multi-step task done, suggest `newton plan "<their goal>"` rather than writing a long answer.
- Never claim to have run anything."""

RISKS = ("safe", "caution", "danger")


def env_block(cfg: Dict[str, Any], shell: str = "bash") -> str:
    return ctxmod.describe(ctxmod.gather(shell, bool(cfg.get("share_file_names", True))))


def risk_for(model_risk: str, command: str) -> str:
    """The stricter of what the AI claims and what Newton's local rules say."""
    base = model_risk if model_risk in RISKS else "safe"
    local = RISKS[safety.level(command)] if command else "safe"
    return max(base, local, key=RISKS.index)


def _s(v: Any, n: int = 400) -> str:
    return str(v).strip()[:n] if v is not None else ""


def norm_steps(raw: Any, limit: int) -> List[Dict[str, Any]]:
    steps = []
    for item in (raw or [])[:limit]:
        if isinstance(item, str) and item.strip():          # small models sometimes return bare command strings
            item = {"command": item}
        if not isinstance(item, dict):
            continue
        command, manual = fix_escapes(_s(item.get("command"), 4000)), _s(item.get("manual"), 400)
        if not command and not manual:
            continue
        steps.append({
            "title": _s(item.get("title"), 80) or (command.splitlines()[0][:60] if command else "Manual step"),
            "why": _s(item.get("why"), 200),
            "command": command,
            "manual": manual,
            "verify": _s(item.get("verify"), 400),
            "undo": fix_escapes(_s(item.get("undo"), 2000)),
            "risk": risk_for(_s(item.get("risk")).lower(), command),
            "seconds": 0.0,
            "status": "pending",
            "attempts": 0,
        })
    return steps


def norm_requires(raw: Any) -> List[str]:
    out: List[str] = []
    for item in (raw or [])[:10] if isinstance(raw, list) else []:
        name = _s(item, 40)
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]*", name) and name not in out:
            out.append(name)
    return out


def norm_inputs(raw: Any) -> List[Dict[str, str]]:
    out = []
    for item in (raw or [])[:8]:
        if isinstance(item, dict) and re.fullmatch(r"[A-Z][A-Z0-9_]*", _s(item.get("name"))):
            out.append({"name": _s(item["name"]), "prompt": _s(item.get("prompt"), 120) or _s(item["name"]),
                        "default": _s(item.get("default"), 120)})
    return out


STRICT_RETRY = ("Your last reply could not be parsed. Reply again with ONLY one valid JSON object that follows the schema exactly: "
                "double-quoted keys and strings, no comments, no trailing commas, no text before or after it.")


def _plan_json(cfg: Dict[str, Any], system: str, user: str, max_tokens: int, timeout: float, need: str = "steps") -> Dict[str, Any]:
    """Asks for a JSON plan; if the reply is unparseable or empty, asks once more, strictly. Local models need this."""
    messages = [{"role": "user", "content": user}]
    last: Optional[NewtonError] = None
    for attempt in range(2):
        raw = llm.complete(cfg, system, messages, max_tokens=max_tokens, smart=True, json_mode=True, timeout=timeout)
        try:
            data = llm.parse_json(raw)
        except NewtonError as e:
            last = e
            data = None
        if data is not None and (data.get(need) or data.get("summary")):
            return data
        messages = messages + [{"role": "assistant", "content": raw or "(empty)"}, {"role": "user", "content": STRICT_RETRY}]
    raise last or NewtonError("The AI didn't return a usable plan. Try again, or rephrase the goal.")


def make_plan(goal: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    user = f"Environment:\n{env_block(cfg)}\n\nGoal: {goal}"
    timeout = max(float(cfg["timeout"]), float(cfg.get("plan_timeout", 90)))
    data = _plan_json(cfg, PLAN_SYSTEM, user, 3500, timeout)
    steps = norm_steps(data.get("steps"), int(cfg.get("plan_max_steps", 15)))
    if not steps:
        raise NewtonError(_s(data.get("summary"), 300) or "Newton couldn't turn that into a plan. Try describing the goal differently.")
    return {
        "goal": _s(data.get("goal"), 80) or " ".join(goal.split()[:7]),
        "summary": _s(data.get("summary"), 300),
        "assumptions": [_s(a, 160) for a in (data.get("assumptions") or [])[:6] if a],
        "requires": norm_requires(data.get("requires")),
        "inputs": norm_inputs(data.get("inputs")),
        "steps": steps,
        "after": _s(data.get("after"), 300),
    }


def revise_plan(plan: Dict[str, Any], feedback: str, cfg: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    done = [f"- {s['title']} ({s['status']})" for s in plan["steps"] if s["status"] in ("done", "skipped")]
    remaining = [{k: s.get(k, "") for k in ("title", "why", "command", "manual", "verify", "undo", "risk")}
                 for s in plan["steps"] if s["status"] not in ("done", "skipped")]
    user = (f"Environment:\n{env_block(cfg)}\n\nGoal: {plan['goal']}\nVariables set: {json.dumps(plan.get('vars', {}))}\n"
            f"Already finished:\n{chr(10).join(done) or '(nothing yet)'}\n\n"
            f"Remaining steps (JSON): {json.dumps(remaining)}\n\nUser feedback: {feedback}")
    data = _plan_json(cfg, REVISE_SYSTEM, user, 3000, max(float(cfg["timeout"]), float(cfg.get("plan_timeout", 90))))
    steps = norm_steps(data.get("steps"), int(cfg.get("plan_max_steps", 15)))
    if not steps:
        raise NewtonError("Newton couldn't revise the plan from that. Try rephrasing the change.")
    return steps, norm_inputs(data.get("inputs"))


def diagnose(cfg: Dict[str, Any], command: str, code: int, output: str, task: str = "") -> Dict[str, Any]:
    user = (f"Environment:\n{env_block(cfg)}\n\n" + (f"Task: {task}\n" if task else "") +
            f"Command:\n{command}\nExit code: {code}\nOutput (last lines):\n{safety.redact(output) or '(no output)'}")
    data = llm.parse_json(llm.complete(cfg, DIAGNOSE_SYSTEM, [{"role": "user", "content": user}], max_tokens=800,
                                       smart=True, json_mode=True, timeout=max(float(cfg["timeout"]), 40.0)))
    fix = data.get("fix")
    if isinstance(fix, dict) and _s(fix.get("command")):
        cmd = _s(fix["command"], 4000)
        fix = {"title": _s(fix.get("title"), 80) or "Apply fix", "command": cmd, "risk": risk_for(_s(fix.get("risk")).lower(), cmd)}
    else:
        fix = None
    return {"diagnosis": _s(data.get("diagnosis"), 600) or "Newton couldn't pin down the cause.",
            "fix": fix, "then": "next" if data.get("then") == "next" else "retry",
            "confidence": _s(data.get("confidence"), 10)}


def commit_message(stat: str, diff: str, recent: List[str], cfg: Dict[str, Any]) -> Dict[str, str]:
    user = (f"Recent commit subjects (match this style):\n" + "\n".join(f"- {r}" for r in recent) +
            f"\n\nChanged files:\n{stat}\n\nDiff:\n{safety.redact(diff)}")
    data = llm.parse_json(llm.complete(cfg, COMMIT_SYSTEM, [{"role": "user", "content": user}], max_tokens=500,
                                       smart=True, json_mode=True, timeout=max(float(cfg["timeout"]), 40.0)))
    subject = _s(data.get("subject"), 100).rstrip(".")
    if not subject:
        raise NewtonError("Newton couldn't write a commit message for that diff.")
    return {"subject": subject, "body": _s(data.get("body"), 1200)}


def answer(cfg: Dict[str, Any], messages: List[Dict[str, str]], system: Optional[str] = None, indent: str = "  ") -> str:
    """Streams a reply to the terminal with light Markdown styling; returns the full text."""
    md = term.MarkdownStream(indent)
    spin = term.Spinner("Newton is thinking").start()
    full: List[str] = []
    first = True
    try:
        for chunk in llm.stream(cfg, system or ASK_SYSTEM, messages, smart=True):
            if first:
                spin.stop()
                print()
                first = False
            full.append(chunk)
            md.feed(chunk)
    finally:
        spin.stop()
    md.flush()
    print()
    return "".join(full)
