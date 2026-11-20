"""Collects lightweight facts about the user's environment so suggestions fit their machine."""
from __future__ import annotations

import os
import platform
import shutil
from pathlib import Path
from typing import Dict, List, Optional

TOOLS = [
    "git", "gh", "docker", "kubectl", "brew", "apt", "dnf", "pacman", "npm", "pnpm", "yarn", "bun",
    "node", "python3", "pip", "uv", "cargo", "go", "rg", "fd", "jq", "fzf", "curl", "wget", "ffmpeg",
    "make", "terraform", "aws", "gcloud", "systemctl", "lsof", "tar", "zip",
]

PROJECT_MARKERS = {
    "package.json": "Node.js", "pyproject.toml": "Python", "requirements.txt": "Python",
    "Cargo.toml": "Rust", "go.mod": "Go", "Gemfile": "Ruby", "pom.xml": "Java (Maven)",
    "build.gradle": "Java (Gradle)", "Makefile": "Make", "docker-compose.yml": "Docker Compose",
    "compose.yaml": "Docker Compose", "Dockerfile": "Docker",
}


def os_name() -> str:
    system = platform.system()
    if system == "Darwin":
        ver = platform.mac_ver()[0]
        return f"macOS {ver}".strip()
    if system == "Linux":
        try:
            for line in Path("/etc/os-release").read_text().splitlines():
                if line.startswith("PRETTY_NAME="):
                    return line.split("=", 1)[1].strip().strip('"')
        except OSError:
            pass
        return "Linux"
    if system == "Windows":
        return f"Windows {platform.release()}"
    return system or "Unknown"


def _git_info(cwd: Path) -> Optional[str]:
    for d in [cwd, *cwd.parents]:
        head = d / ".git" / "HEAD"
        if head.exists():
            try:
                ref = head.read_text().strip()
                branch = ref.rsplit("/", 1)[-1] if ref.startswith("ref:") else ref[:8]
            except OSError:
                branch = "?"
            return f"git repo (branch: {branch})"
        if (d / ".git").is_file():
            return "git repo (worktree)"
    return None


def gather(shell: Optional[str] = None, share_file_names: bool = True) -> Dict[str, object]:
    cwd = Path.cwd()
    shell = shell or Path(os.environ.get("SHELL", "sh")).name
    entries: List[str] = []
    project: List[str] = []
    try:
        names = sorted(os.listdir(cwd))
        project = sorted({label for f, label in PROJECT_MARKERS.items() if f in names})
        if share_file_names:
            entries = [n + ("/" if (cwd / n).is_dir() else "") for n in names if not n.startswith(".")][:40]
    except OSError:
        pass
    return {
        "os": os_name(),
        "shell": shell,
        "cwd": str(cwd).replace(str(Path.home()), "~", 1),
        "git": _git_info(cwd),
        "project": project,
        "tools": [t for t in TOOLS if shutil.which(t)],
        "files": entries,
    }


def describe(ctx: Dict[str, object]) -> str:
    lines = [
        f"OS: {ctx['os']}",
        f"Shell: {ctx['shell']}",
        f"Working directory: {ctx['cwd']}",
    ]
    if ctx.get("git"):
        lines.append(f"Version control: {ctx['git']}")
    if ctx.get("project"):
        lines.append("Project type: " + ", ".join(ctx["project"]))  # type: ignore[arg-type]
    if ctx.get("tools"):
        lines.append("Installed tools: " + ", ".join(ctx["tools"]))  # type: ignore[arg-type]
    if ctx.get("files"):
        lines.append("Files here: " + ", ".join(ctx["files"]))  # type: ignore[arg-type]
    return "\n".join(lines)
