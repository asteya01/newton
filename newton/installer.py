"""Install, update and uninstall Newton. Standard library only.

Newton ships as ONE executable file (a Python zipapp) that needs nothing but `python3` 3.9+: no pip,
no venv, no admin rights, and no "externally managed environment" errors. It lives in ~/.local/bin/newton.

This module is run two ways:
  python3 newton/installer.py install      (from the unzipped folder, via install.sh)
  newton update | newton uninstall         (from the installed copy)
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import List, Optional, Tuple

BEGIN = "# >>> newton >>>"
END = "# <<< newton <<<"
SHELLS = ("zsh", "bash", "fish")
MIN_PY = (3, 9)
MAX_DOWNLOAD = 40 * 1024 * 1024

MAIN_PY = '''import sys
if sys.version_info < (3, 9):
    sys.stderr.write("newton needs Python 3.9 or newer (this is %d.%d).\\n" % sys.version_info[:2])
    sys.exit(1)
from newton.cli import main
sys.exit(main())
'''

LEGACY_COMMENT = re.compile(r"^# Newton [—-] Think it\. Tab it\. Done\.\s*$")
LEGACY_INIT = re.compile(r'^(eval "\$\(newton init (zsh|bash)\)"|newton init fish \| source)\s*$')


# ----------------------------------------------------------------------------- small helpers

def _color() -> bool:
    return sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _color() else text


def ok(msg: str) -> None:
    print(f"  {_c('38;5;121', '✓')} {msg}")


def note(msg: str) -> None:
    print(f"  {_c('38;5;245', msg)}")


def warn(msg: str) -> None:
    print(f"  {_c('38;5;215', '!')} {msg}")


def fail(msg: str) -> None:
    print(f"  {_c('38;5;203', '✗')} {msg}", file=sys.stderr)


def home() -> Path:
    return Path(os.environ.get("HOME") or Path.home())


def default_bin_dir() -> Path:
    return Path(os.environ.get("NEWTON_BIN_DIR") or home() / ".local" / "bin")


def parse_version(text: str) -> Tuple[int, ...]:
    return tuple(int(n) for n in re.findall(r"\d+", text)[:3])


def package_version(pkg_dir: Path) -> str:
    m = re.search(r'__version__\s*=\s*"([^"]+)"', (pkg_dir / "__init__.py").read_text())
    return m.group(1) if m else "0"


def is_pyz_install() -> bool:
    """True when this code is running from the single-file install (the package 'directory' is a file)."""
    return os.path.isfile(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def current_executable() -> Optional[Path]:
    return Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) if is_pyz_install() else None


def current_version() -> str:
    try:
        from newton import __version__
        return __version__
    except Exception:
        return package_version(Path(__file__).resolve().parent)


# ----------------------------------------------------------------------------- building the single file

def build_pyz(pkg_dir: Path, out: Path) -> None:
    """Packs the newton package into one executable file. Bytecode is shipped inside it (a zip can't cache
    .pyc files itself), so every Tab press starts fast instead of recompiling Python source."""
    import py_compile
    import zipapp
    stage = Path(tempfile.mkdtemp(prefix="newton-build-"))
    try:
        dest = stage / "newton"
        shutil.copytree(pkg_dir, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))
        for src in list(dest.rglob("*.py")):
            try:
                py_compile.compile(str(src), cfile=str(src.with_suffix(".pyc")), dfile=str(src.relative_to(stage)),
                                   doraise=True, invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH)
            except py_compile.PyCompileError:
                pass                                    # the .py is still in the file; Python will compile it on demand
        (stage / "__main__.py").write_text(MAIN_PY)
        out.parent.mkdir(parents=True, exist_ok=True)
        zipapp.create_archive(stage, out, interpreter="/usr/bin/env python3", compressed=True)
        os.chmod(out, 0o755)
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def smoke_test(pyz: Path, expect_version: str) -> None:
    r = subprocess.run([sys.executable, str(pyz), "--version"], capture_output=True, text=True, timeout=60)
    if r.returncode != 0 or expect_version not in r.stdout:
        raise RuntimeError("the freshly built file did not start: " + (r.stderr.strip() or r.stdout.strip() or "no output"))


# ----------------------------------------------------------------------------- shell config

def detected_shell() -> str:
    name = Path(os.environ.get("SHELL", "")).name
    return name if name in SHELLS else "bash"


def rc_path(shell: str) -> Path:
    h = home()
    if shell == "zsh":
        return Path(os.environ.get("ZDOTDIR") or h) / ".zshrc"
    if shell == "fish":
        return Path(os.environ.get("XDG_CONFIG_HOME") or h / ".config") / "fish" / "config.fish"
    if sys.platform == "darwin" and not (h / ".bashrc").exists():
        return h / ".bash_profile"
    return h / ".bashrc"


def target_shells() -> List[str]:
    """Your login shell, plus any other supported shell you already have a config file for."""
    first = detected_shell()
    return [first] + [s for s in SHELLS if s != first and rc_path(s).exists()]


def _dir_expr(bin_dir: Path) -> str:
    try:
        return "$HOME/" + bin_dir.relative_to(home()).as_posix()
    except ValueError:
        return str(bin_dir)


def block_for(shell: str, bin_dir: Path, init: bool) -> str:
    d = _dir_expr(bin_dir)
    if shell == "fish":
        body = [f"contains -- {d} $PATH; or set -gx PATH {d} $PATH"]
        if init:
            body.append("type -q newton; and newton init fish | source")
    else:
        body = [f'case ":$PATH:" in *":{d}:"*) ;; *) export PATH="{d}:$PATH" ;; esac']
        if init:
            body.append(f'command -v newton >/dev/null 2>&1 && eval "$(newton init {shell})"')
    return "\n".join([BEGIN, "# Added by the Newton installer. Remove it all with: newton uninstall", *body, END]) + "\n"


def _strip(text: str) -> Tuple[str, bool]:
    """Removes Newton's block and any lines older versions appended outside a block. Returns (text, had_init)."""
    had_init = False
    out: List[str] = []
    inside = False
    for line in text.splitlines():
        if line.strip() == BEGIN:
            inside = True
            continue
        if inside:
            had_init = had_init or "newton init" in line
            if line.strip() == END:
                inside = False
            continue
        if LEGACY_COMMENT.match(line):
            continue
        if LEGACY_INIT.match(line):
            had_init = True
            continue
        out.append(line)
    while out and not out[-1].strip():
        out.pop()
    return ("\n".join(out) + "\n") if out else "", had_init


def _write_keep_mode(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o644
    tmp = path.with_name(path.name + ".newton-tmp")
    tmp.write_text(text)
    os.chmod(tmp, mode)
    os.replace(tmp, path)


def ensure_block(shell: str, bin_dir: Path, init: Optional[bool] = None) -> Tuple[Path, bool]:
    """Idempotently writes Newton's block into the shell's config file.
    init=None keeps whatever is already enabled; True/False sets it. Returns (file, changed)."""
    path = rc_path(shell)
    old = path.read_text(errors="replace") if path.exists() else ""
    rest, had_init = _strip(old)
    new = (rest + "\n" if rest else "") + block_for(shell, bin_dir, had_init if init is None else init)
    if new == old:
        return path, False
    _write_keep_mode(path, new)
    return path, True


def init_enabled(shell: str) -> bool:
    p = rc_path(shell)
    return p.exists() and "newton init" in p.read_text(errors="replace")


def remove_blocks() -> List[Path]:
    changed: List[Path] = []
    for shell in SHELLS:
        p = rc_path(shell)
        if not p.exists():
            continue
        old = p.read_text(errors="replace")
        new, _ = _strip(old)
        if new != old:
            _write_keep_mode(p, new)
            changed.append(p)
    return changed


# ----------------------------------------------------------------------------- install

def _remove_pip_install() -> bool:
    """An older `pip install` leaves a second copy that can shadow this one. Remove it if it's there."""
    if os.environ.get("NEWTON_NO_PIP_CLEANUP"):
        return False
    try:
        from importlib import metadata
        metadata.distribution("newton-cli")
    except Exception:
        return False
    for flags in ([], ["--break-system-packages"]):
        try:
            r = subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "newton-cli", *flags],
                               capture_output=True, timeout=90)
        except (OSError, subprocess.SubprocessError):
            return False
        if r.returncode == 0:
            return True
    return False


def other_copies(target: Path) -> List[Path]:
    found: List[Path] = []
    for d in os.environ.get("PATH", "").split(os.pathsep):
        if not d:
            continue
        p = Path(d) / "newton"
        try:
            if p.exists() and p.resolve() != target.resolve() and p not in found:
                found.append(p)
        except OSError:
            continue
    return found


def install(pkg_dir: Path, bin_dir: Path, *, path_setup: bool = True, quiet: bool = False) -> Path:
    version = package_version(pkg_dir)
    target = bin_dir / "newton"
    bin_dir.mkdir(parents=True, exist_ok=True)
    fresh = bin_dir / ".newton.new"
    try:
        build_pyz(pkg_dir, fresh)
        smoke_test(fresh, version)
        if _remove_pip_install() and not quiet:
            note("removed an older pip-installed copy")
        os.replace(fresh, target)
    finally:
        if fresh.exists():
            fresh.unlink()
    if not quiet:
        ok(f"installed newton {version} → {target}")
    if path_setup:
        for shell in target_shells():
            try:
                path, changed = ensure_block(shell, bin_dir)
            except OSError as e:
                warn(f"could not edit the {shell} config: {e}")
                continue
            if changed and not quiet:
                ok(f"{shell}: made sure {_dir_expr(bin_dir)} is on your PATH  {_c('38;5;245', '(' + str(path) + ')')}")
    if not quiet:
        extras = other_copies(target)
        for p in extras:
            warn(f"another copy exists at {p}. New terminals use the one in {bin_dir}; delete the other to avoid confusion.")
    return target


def cmd_install(args: argparse.Namespace) -> int:
    if sys.version_info < MIN_PY:
        fail("Newton needs Python %d.%d or newer (this is %d.%d)." % (MIN_PY + sys.version_info[:2]))
        return 1
    pkg_dir = Path(__file__).resolve().parent
    if is_pyz_install():
        fail("run this from the unzipped Newton folder, not from the installed copy (use `newton update`).")
        return 1
    bin_dir = Path(args.bin_dir) if args.bin_dir else default_bin_dir()
    if not args.quiet:
        print()
        print(f"  {_c('38;5;121', '●')}  Installing {_c('38;5;121', 'newton')} {package_version(pkg_dir)}\n")
    try:
        target = install(pkg_dir, bin_dir, path_setup=not args.no_path, quiet=args.quiet)
    except (OSError, RuntimeError, subprocess.SubprocessError) as e:
        fail(str(e))
        return 1
    if args.no_setup or args.quiet:
        return 0
    print()
    tty = None
    if not sys.stdin.isatty():
        try:
            tty = open("/dev/tty")                      # curl ... | sh: stdin is the script, so talk to the real terminal
        except OSError:
            note("Run `newton setup` to choose your AI and turn on Tab.")
            return 0
    env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"}
    rc = subprocess.call([str(target), "setup"], stdin=tty or None, env=env)
    if tty:
        tty.close()
    if rc == 0:
        shell = detected_shell()
        print(f"  {_c('38;5;245', 'Open a new terminal window to start using it (or run: exec ' + shell + ').')}\n")
    return rc


# ----------------------------------------------------------------------------- update

def downloads_dirs() -> List[Path]:
    """Where a freshly downloaded newton.zip is likely to be. On a Chromebook, files downloaded in Chrome only
    reach the Linux terminal once dragged into "Linux files", which is the terminal's home folder."""
    h = home()
    candidates = [h / "Downloads", h / "downloads", h / "Download", Path("/mnt/chromeos/MyFiles/Downloads"), h]
    return [d for d in candidates if d.is_dir()]


def _version_in_zip(path: Path) -> Optional[str]:
    try:
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                if name.endswith("newton/__init__.py") and name.count("/") <= 2:
                    m = re.search(r'__version__\s*=\s*"([^"]+)"', z.read(name).decode("utf-8", "replace"))
                    if m:
                        return m.group(1)
    except (OSError, zipfile.BadZipFile):
        return None
    return None


def newest_download() -> Optional[Tuple[Path, str]]:
    best: Optional[Tuple[Path, str]] = None
    for d in downloads_dirs():
        for f in d.glob("newton*.zip"):
            v = _version_in_zip(f)
            if v and (best is None or parse_version(v) > parse_version(best[1])
                      or (parse_version(v) == parse_version(best[1]) and f.stat().st_mtime > best[0].stat().st_mtime)):
                best = (f, v)
    return best


def _safe_extract(zpath: Path, dest: Path) -> None:
    with zipfile.ZipFile(zpath) as z:
        root = dest.resolve()
        for m in z.infolist():
            target = (dest / m.filename).resolve()
            if root != target and root not in target.parents:
                raise RuntimeError("the archive contains an unsafe path: " + m.filename)
        z.extractall(dest)


def _find_pkg(root: Path) -> Optional[Path]:
    if (root / "cli.py").is_file() and (root / "__init__.py").is_file():
        return root
    for p in root.rglob("cli.py"):
        if p.parent.name == "newton" and (p.parent / "__init__.py").is_file() and (p.parent / "shells").is_dir():
            return p.parent
    return None


def _fetch(url: str, dest: Path) -> None:
    if not url.startswith(("https://", "file://")):
        raise RuntimeError("only https:// addresses are accepted")
    with urllib.request.urlopen(url, timeout=60) as r, open(dest, "wb") as f:
        size = 0
        while True:
            chunk = r.read(1 << 16)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_DOWNLOAD:
                raise RuntimeError("that download is unexpectedly large; refusing it")
            f.write(chunk)


def resolve_source(source: str, work: Path) -> Path:
    """Turns a zip, a folder or an https address into a package directory."""
    if source.startswith(("http://", "https://", "file://")):
        if source.startswith("http://"):
            raise RuntimeError("use an https:// address")
        tmp = work / "download.zip"
        _fetch(source, tmp)
        src = tmp
    else:
        src = Path(os.path.expanduser(source))
    if src.is_dir():
        pkg = _find_pkg(src)
    elif zipfile.is_zipfile(src):
        _safe_extract(src, work / "src")
        pkg = _find_pkg(work / "src")
    else:
        raise RuntimeError(f"{source} is not a Newton zip or folder")
    if not pkg:
        raise RuntimeError("that doesn't look like a Newton download (no newton package inside)")
    return pkg


def update(source: Optional[str], force: bool = False, yes: bool = False) -> int:
    cur = current_version()
    label = source
    if not source:
        found = newest_download()
        if not found:
            fail("Nothing to update from. Download the newest newton.zip, then run: newton update ~/Downloads/newton.zip")
            return 1
        source, label = str(found[0]), f"{found[0]}  (v{found[1]})"
        note(f"found {label}")
    work = Path(tempfile.mkdtemp(prefix="newton-update-"))
    try:
        try:
            pkg = resolve_source(source, work)
        except (RuntimeError, OSError, zipfile.BadZipFile) as e:
            fail(str(e))
            return 1
        new = package_version(pkg)
        if parse_version(new) <= parse_version(cur) and not force:
            ok(f"already up to date (v{cur}). Use --force to reinstall anyway.")
            return 0
        print(f"\n  Update newton {_c('38;5;245', 'v' + cur)} → {_c('38;5;121', 'v' + new)}")
        if not yes:
            try:
                if input("  Continue? [Y/n] ").strip().lower().startswith("n"):
                    return 0
            except (EOFError, KeyboardInterrupt):
                print()
                return 1
        exe = current_executable()
        bin_dir = exe.parent if exe else default_bin_dir()
        # Run the NEW installer, so upgrades can change how installing works.
        r = subprocess.run([sys.executable, str(pkg / "installer.py"), "install", "--no-setup", "--quiet", "--bin-dir", str(bin_dir)])
        if r.returncode != 0:
            fail("the update failed; your current version is untouched.")
            return 1
        ok(f"updated to v{new}. Open a new terminal to pick it up everywhere.")
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ----------------------------------------------------------------------------- uninstall

def uninstall(purge: bool = False, yes: bool = False) -> int:
    exe = current_executable()
    rcs = []
    for shell in SHELLS:
        p = rc_path(shell)
        if p.exists():
            txt = p.read_text(errors="replace")
            if BEGIN in txt or _strip(txt)[0] != txt:
                rcs.append(p)
    data_dirs: List[Path] = []
    if purge:
        try:
            from newton import config as cfgmod
            data_dirs = [d for d in (cfgmod.config_path().parent, cfgmod.cache_dir(), cfgmod.data_dir()) if d.exists()]
        except Exception:
            pass
    print()
    print("  This will remove:")
    print(f"    · {exe}" if exe else "    · (the program was installed with pip: remove it afterwards with `python3 -m pip uninstall newton-cli`)")
    for p in rcs:
        print(f"    · Newton's lines in {p}")
    for d in data_dirs:
        print(f"    · {d}  {_c('38;5;215', '(your settings, saved plans and history)')}")
    if not purge:
        note("Your settings, API key, history and saved plans stay in place. Add --purge to delete those too.")
    if not yes:
        try:
            if not input("\n  Remove Newton? [y/N] ").strip().lower().startswith("y"):
                print("  Nothing was changed.")
                return 0
        except (EOFError, KeyboardInterrupt):
            print()
            return 1
    for p in remove_blocks():
        ok(f"cleaned {p}")
    for d in data_dirs:
        shutil.rmtree(d, ignore_errors=True)
        ok(f"deleted {d}")
    if exe:
        try:
            exe.unlink()
            ok(f"removed {exe}")
        except OSError as e:
            fail(f"could not remove {exe}: {e}")
            return 1
    print("\n  Newton is gone. Open a new terminal for the change to take effect.\n")
    return 0


# ----------------------------------------------------------------------------- script entry point

def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="installer.py", description="Install Newton from this folder.")
    sub = p.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("install")
    i.add_argument("--bin-dir")
    i.add_argument("--no-setup", action="store_true", help="skip the guided setup")
    i.add_argument("--no-path", action="store_true", help="don't edit shell config files")
    i.add_argument("--quiet", action="store_true")
    i.set_defaults(func=cmd_install)
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
