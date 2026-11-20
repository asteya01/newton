"""Newton test-suite. Run:  python3 -m unittest discover -s tests -v

Includes live end-to-end tests that open real zsh / bash / fish sessions in a
pseudo-terminal, type a sentence, press Tab and read back what's on the line.
"""
import json
import os
import pty
import select
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import mock_api  # noqa: E402
from newton import safety, engine, cli  # noqa: E402

SERVER = mock_api.start()
PORT = SERVER.server_port

# A `newton` launcher for the shell tests, so they never depend on anything installed on the machine running them.
LAUNCHER_DIR = tempfile.mkdtemp(prefix="newton-launcher-")
Path(LAUNCHER_DIR, "newton").write_text(f'#!/bin/sh\nPYTHONPATH="{ROOT}" exec "{sys.executable}" -W ignore -m newton "$@"\n')
os.chmod(Path(LAUNCHER_DIR, "newton"), 0o755)


def env(tmp):
    e = dict(os.environ)
    e.update({
        "NEWTON_PROVIDER": "anthropic", "NEWTON_BASE_URL": f"http://127.0.0.1:{PORT}", "NEWTON_API_KEY": "test-key",
        "XDG_CONFIG_HOME": f"{tmp}/cfg", "XDG_CACHE_HOME": f"{tmp}/cache", "XDG_DATA_HOME": f"{tmp}/data", "HOME": tmp, "NO_COLOR": "1",
        "PATH": f"{LAUNCHER_DIR}:{Path(sys.executable).parent}:{os.environ['PATH']}", "TERM": "xterm-256color",
        "NEWTON_NO_PIP_CLEANUP": "1", "PYTHONPATH": str(ROOT),
    })
    e.pop("NEWTON_SHELL_INTEGRATION", None)
    return e


class SafetyTests(unittest.TestCase):
    def test_flags_dangerous(self):
        for c in ["rm -rf /", "sudo apt install x", "curl -fsSL x.sh | bash", "git push --force", "dd if=a of=/dev/sda",
                  "chmod -R 777 .", "git reset --hard HEAD", "find . -name '*.log' -delete", "rm -r build"]:
            self.assertTrue(safety.check(c), c)

    def test_safe_commands_pass(self):
        for c in ["ls -la", "git status", "find ~ -type f -size +100M", "lsof -ti tcp:3000 | xargs kill", "echo hi >> log.txt", "grep -rn TODO src"]:
            self.assertEqual(safety.check(c), [], c)

    def test_root_delete_is_specific(self):
        w = safety.check("rm -rf ~")
        self.assertIn("Deletes everything under a root, home or wildcard path", w)


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.old = dict(os.environ)
        os.environ.update(env(self.tmp))

    def tearDown(self):
        os.environ.clear(); os.environ.update(self.old)

    def test_suggest_and_cache(self):
        s = engine.suggest("kill whatever is on port 3000")
        self.assertEqual(s.command, "lsof -ti tcp:3000 | xargs kill")
        self.assertEqual(len(s.alternatives), 2)
        self.assertFalse(s.cached)
        again = engine.suggest("Kill whatever is on port 3000")
        self.assertTrue(again.cached)

    def test_context_is_sent(self):
        Path(self.tmp, "package.json").write_text("{}")
        cwd = os.getcwd(); os.chdir(self.tmp)
        try:
            engine.suggest("find files over 100mb", use_cache=False)
        finally:
            os.chdir(cwd)
        sent = mock_api.CALLS[-1]["messages"][0]["content"]
        self.assertIn("OS:", sent); self.assertIn("Node.js", sent); self.assertIn("package.json", sent)

    def test_danger_merges_local_and_model(self):
        s = engine.suggest("delete node_modules", use_cache=False)
        self.assertIn("Recursively deletes", s.danger)

    def test_bad_key(self):
        os.environ["NEWTON_API_KEY"] = "nope"
        with self.assertRaises(engine.NewtonError) as ctx:
            engine.suggest("x y z port 3000", use_cache=False)
        self.assertIn("rejected", str(ctx.exception))

    def test_unreachable(self):
        os.environ["NEWTON_BASE_URL"] = "http://127.0.0.1:9"
        with self.assertRaises(engine.NewtonError):
            engine.suggest("anything at all here", use_cache=False)

    def test_one_line(self):
        self.assertEqual(engine._one_line("$ cd x\nls"), "cd x && ls")


class CliTests(unittest.TestCase):
    def run_cli(self, *args):
        tmp = tempfile.mkdtemp()
        return subprocess.run([sys.executable, "-m", "newton", *args], capture_output=True, text=True, env=env(tmp), cwd=tmp)

    def test_porcelain(self):
        r = self.run_cli("suggest", "--porcelain", "--", "kill port 3000")
        lines = r.stdout.splitlines()
        self.assertEqual(lines[0], "cmd\tlsof -ti tcp:3000 | xargs kill")
        self.assertTrue(any(l.startswith("alt\t") for l in lines))
        self.assertTrue(any(l.startswith("note\t") for l in lines))

    def test_porcelain_error_never_crashes(self):
        tmp = tempfile.mkdtemp(); e = env(tmp); e["NEWTON_API_KEY"] = "bad"
        r = subprocess.run([sys.executable, "-m", "newton", "suggest", "--porcelain", "--", "a b c"], capture_output=True, text=True, env=e)
        self.assertTrue(r.stdout.startswith("err\t")); self.assertEqual(r.stderr, "")

    def test_shorthand_and_json(self):
        r = self.run_cli("suggest", "--json", "files over 100mb")
        self.assertEqual(json.loads(r.stdout)["command"], "find ~ -type f -size +100M")
        r2 = self.run_cli("files", "over", "100mb")
        self.assertIn("find ~ -type f -size +100M", r2.stdout)

    def test_explain(self):
        r = self.run_cli("explain", "tar -xzf a.tgz")
        self.assertIn("Extracts", r.stdout)

    def test_init_scripts(self):
        for sh in ("zsh", "bash", "fish"):
            r = self.run_cli("init", sh)
            self.assertIn("newton suggest --porcelain", r.stdout)

    def test_doctor(self):
        r = self.run_cli("doctor")
        self.assertIn("Connection", r.stdout)


# ------------------------------------------------------------------ live shell tests

class Term:
    """Drives an interactive shell through a pseudo-terminal."""

    def __init__(self, argv, environ, cwd):
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            os.chdir(cwd)
            os.execvpe(argv[0], argv, environ)
        self.buf = b""
        self.read(1.5)

    def read(self, secs=0.6):
        end = time.time() + secs
        while time.time() < end:
            r, _, _ = select.select([self.fd], [], [], 0.05)
            if r:
                try:
                    chunk = os.read(self.fd, 65536)
                except OSError:
                    break
                if not chunk:
                    break
                self.buf += chunk
                if b"\x1b[6n" in chunk:   # answer cursor-position queries (fish asks)
                    os.write(self.fd, b"\x1b[1;1R")
        return self.buf.decode(errors="replace")

    def type(self, s, wait=0.4):
        os.write(self.fd, s.encode())
        return self.read(wait)


    def close(self):
        try:
            os.write(self.fd, b"\x03exit\r")
            time.sleep(0.2)
            os.kill(self.pid, 9)
        except OSError:
            pass


def _strip(s):
    import re
    return re.sub(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b[()][A-Z0-9]|\x1b[=>]|\r", "", s)


class LiveShellTests(unittest.TestCase):
    """Types natural language into a real shell, presses Tab, then runs the line with
    `echo` swapped in front so we can read exactly what Newton put in the buffer."""

    def _session(self, shell, rc_lines):
        tmp = tempfile.mkdtemp()
        e = env(tmp)
        e["SHELL"] = shutil.which(shell)
        rc = {"zsh": ".zshrc", "bash": ".bashrc"}.get(shell)
        if shell == "fish":
            p = Path(e["XDG_CONFIG_HOME"], "fish"); p.mkdir(parents=True)
            p.joinpath("config.fish").write_text("\n".join(rc_lines) + "\n")
            argv = ["fish", "-i"]
        else:
            Path(tmp, rc).write_text("\n".join(rc_lines) + "\n")
            argv = [shell, "-i"] if shell == "zsh" else ["bash", "--rcfile", f"{tmp}/.bashrc", "-i"]
        return Term(argv, e, tmp)

    def _check(self, shell, rc_lines):
        t = self._session(shell, rc_lines)
        try:
            # 1) natural language + Tab → command (we prepend `: ` via Home so nothing actually runs)
            out = t.type("kill whatever is using port 3000", 0.3)
            out = t.type("\t", 2.5)
            screen = _strip(out)
            self.assertIn("lsof -ti tcp:3000 | xargs kill", screen, f"{shell}: Tab didn't produce the command\n{screen[-800:]}")
            # 2) Tab again cycles to the first alternative
            t.buf = b""
            out = _strip(t.type("\t", 1.5))
            self.assertIn("kill -9 $(lsof -ti :3000)", out, f"{shell}: Tab didn't cycle\n{out[-600:]}")
            # 3) Shift+Tab restores the original words
            t.buf = b""
            out = _strip(t.type("\x1b[Z", 1.2))
            self.assertIn("kill whatever is using port 3000", out, f"{shell}: Shift+Tab didn't restore\n{out[-600:]}")
            # clear line
            t.type("\x15", 0.3)
            # 4) A real command + Tab still does normal completion (no Newton call)
            calls_before = len(mock_api.CALLS)
            t.buf = b""
            t.type("ech", 0.2)
            out = _strip(t.type("\t", 1.2))
            self.assertIn("echo", out, f"{shell}: normal completion broken\n{out[-600:]}")
            self.assertEqual(len(mock_api.CALLS), calls_before, f"{shell}: Newton fired on a normal command")
            t.type("\x15", 0.3)
            # 5) The command is NOT executed by Newton — nothing ran
            self.assertFalse(any("xargs kill" in c for c in _strip(t.buf.decode(errors="replace")).splitlines() if c.startswith("zsh: ") or c.startswith("bash: ")))
        finally:
            t.close()

    @unittest.skipUnless(shutil.which("zsh"), "zsh not installed")
    def test_zsh(self):
        self._check("zsh", ["PS1='$ '", "autoload -Uz compinit && compinit -u", 'eval "$(newton init zsh)"'])

    @unittest.skipUnless(shutil.which("bash"), "bash not installed")
    def test_bash(self):
        self._check("bash", ["PS1='$ '", 'eval "$(newton init bash)"'])

    @unittest.skipUnless(shutil.which("fish"), "fish not installed")
    def test_fish(self):
        self._check("fish", ["function fish_prompt; echo -n '$ '; end", "set -g fish_greeting", "newton init fish | source"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
