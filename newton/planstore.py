"""Saved plans: ~/.local/share/newton/plans/<id>.json, plus a pointer to the one you're working on."""
from __future__ import annotations

import json
import os
import secrets
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from newton import config as cfgmod

Plan = Dict[str, Any]


def plans_dir() -> Path:
    return cfgmod.data_dir() / "plans"


def new_id() -> str:
    return time.strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(2)


def save(plan: Plan) -> None:
    plan["updated"] = time.time()
    d = cfgmod.ensure_private(plans_dir())
    path = d / f"{plan['id']}.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(plan, indent=2))
    os.replace(tmp, path)
    cur = d / "current"
    if plan.get("status") == "active":
        cur.write_text(plan["id"])
    elif cur.exists() and cur.read_text().strip() == plan["id"]:
        cur.unlink()


def list_plans() -> List[Plan]:
    out: List[Plan] = []
    d = plans_dir()
    if d.exists():
        for p in d.glob("*.json"):
            try:
                out.append(json.loads(p.read_text()))
            except (OSError, ValueError):
                continue
    return sorted(out, key=lambda x: x.get("created", 0), reverse=True)


def load(plan_id: str) -> Optional[Plan]:
    """Accepts a full id or any unique prefix."""
    matches = [p for p in list_plans() if p["id"] == plan_id or p["id"].startswith(plan_id)]
    return matches[0] if len(matches) == 1 else None


def current() -> Optional[Plan]:
    d = plans_dir()
    cur = d / "current"
    if cur.exists():
        p = load(cur.read_text().strip())
        if p and p.get("status") == "active":
            return p
    active = [p for p in list_plans() if p.get("status") == "active"]
    return active[0] if active else None


def delete(plan_id: str) -> bool:
    p = load(plan_id)
    if not p:
        return False
    f = plans_dir() / f"{p['id']}.json"
    f.unlink(missing_ok=True)
    cur = plans_dir() / "current"
    if cur.exists() and cur.read_text().strip() == p["id"]:
        cur.unlink()
    return True


def progress(plan: Plan) -> Tuple[int, int]:
    steps = plan.get("steps", [])
    return sum(1 for s in steps if s["status"] in ("done", "skipped")), len(steps)


def fresh(goal_request: str, data: Dict[str, Any], cwd: str) -> Plan:
    return {
        "id": new_id(), "request": goal_request, "created": time.time(), "updated": time.time(),
        "status": "active", "cwd": cwd, "vars": {}, "elapsed": 0.0, **data,
    }
