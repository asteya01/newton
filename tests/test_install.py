"""Installer, updater and uninstaller tests. Every test uses a throwaway HOME; nothing touches the real machine.

Run:  python3 -W ignore -m unittest tests.test_install -v
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import test_newton as base  # noqa: E402  (starts the shared mock AI server)

BEGIN, END = "# >>> newton >>>", "# <<< newton <<<"


def make_zip(dest: Path, version: str = None) -> Path:
    """A download laid out like the real newton.zip: newton/install.sh + newton/newton/<package>."""
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(ROOT / "install.sh", "newton/install.sh")
        z.write(ROOT / "pyproject.toml", "newton/pyproject.toml")
        for f in sorted((ROOT / "newton").rglob("*")):
            if f.is_dir() or "__pycache__" in f.parts or f.suffix == ".pyc":
                continue
            rel = f.relative_to(ROOT).as_posix()
            data = f.read_bytes()
            if version and rel == "newton/__init__.py":
                data = data.decode().replace(base_version(), version).encode()
            z.writestr("newton/" + rel, data)
    return dest


def base_version() -> str:
    import re
    return re.search(r'__version__ = "([^"]+)"', (ROOT / "newton" / "__init__.py").read_text()).group(1)


class Home(unittest.TestCase):
    """A clean fake home directory + helpers to run the installer and the installed program."""

    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix="newton-home-"))
        self.bin = self.home / ".local" / "bin"
        self.exe = self.bin / "newton"

    def tearDown(self):
        shutil.rmtree(self.home, ignore_errors=True)

    def env(self, shell="bash", with_bin=False, **extra):
        e = base.env(str(self.home))
        for k in ("XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME", "NEWTON_SHELL_INTEGRATION", "ZDOTDIR", "PYTHONPATH"):
            e.pop(k, None)
        e["PATH"] = os.pathsep.join(p for p in os.environ["PATH"].split(os.pathsep))        # no launcher, no newton
        if with_bin:
            e["PATH"] = f"{self.bin}{os.pathsep}{e['PATH']}"
        e["SHELL"] = shutil.which(shell) or f"/bin/{shell}"
        e.update(extra)
        return e

    def install(self, *args, shell="bash", sh="sh", stdin="", cwd=None, **extra):
        return subprocess.run([sh, str(ROOT / "install.sh"), "--no-setup", *args], input=stdin, capture_output=True, text=True,
                              env=self.env(shell, **extra), cwd=cwd or str(self.home), timeout=120)

    def newton(self, *args, stdin="", shell="bash", with_bin=True, **extra):
        return subprocess.run([str(self.exe), *args], input=stdin, capture_output=True, text=True,
                              env=self.env(shell, with_bin=with_bin, **extra), cwd=str(self.home), timeout=120)

    def read(self, rel):
        return (self.home / rel).read_text()


# ---------------------------------------------------------------------------------- the single-file install

class InstallTests(Home):
    def test_fresh_install_gives_one_working_executable(self):
        r = self.install()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(os.access(self.exe, os.X_OK))
        self.assertEqual(self.exe.read_bytes()[:21], b"#!/usr/bin/env python")
        v = self.newton("--version")
        self.assertEqual(v.stdout.strip(), "newton " + base_version())
        self.assertEqual([p.name for p in self.bin.iterdir()], ["newton"])              # nothing else left behind

    def test_installed_file_runs_everything_without_the_source_folder(self):
        self.install()
        for argv in (["init", "zsh"], ["init", "bash"], ["init", "fish"]):                # shell scripts are read from inside the file
            r = self.newton(*argv)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("Think it. Tab it. Done.", r.stdout)
        self.assertIn("--dry-run", self.newton("plan", "--help").stdout)

    def test_bash_login_gets_a_path_block_and_nothing_else_is_created(self):
        (self.home / ".bashrc").write_text("# mine\nalias ll='ls -l'\n")
        r = self.install(shell="bash")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        rc = self.read(".bashrc")
        self.assertTrue(rc.startswith("# mine\nalias ll='ls -l'\n"))                       # user content untouched
        self.assertEqual(rc.count(BEGIN), 1); self.assertEqual(rc.count(END), 1)
        self.assertIn('export PATH="$HOME/.local/bin:$PATH"', rc)
        self.assertFalse((self.home / ".zshrc").exists()); self.assertFalse((self.home / ".config" / "fish").exists())

    def test_zsh_and_fish_get_their_own_syntax(self):
        self.install(shell="zsh")
        self.assertIn('export PATH="$HOME/.local/bin:$PATH"', self.read(".zshrc"))
        self.install(shell="fish")
        fish = self.read(".config/fish/config.fish")
        self.assertIn("contains -- $HOME/.local/bin $PATH; or set -gx PATH $HOME/.local/bin $PATH", fish)
        self.assertNotIn("export PATH", fish)

    def test_other_shells_with_existing_config_are_covered_too(self):
        (self.home / ".bashrc").write_text("# bash\n")
        self.install(shell="zsh")
        self.assertIn(BEGIN, self.read(".bashrc")); self.assertIn(BEGIN, self.read(".zshrc"))

    def test_running_it_twice_changes_nothing(self):
        (self.home / ".bashrc").write_text("# mine\n")
        self.install(); first = self.read(".bashrc")
        r = self.install()
        self.assertEqual(r.returncode, 0); self.assertEqual(self.read(".bashrc"), first); self.assertEqual(first.count(BEGIN), 1)

    def test_file_permissions_of_the_users_config_are_preserved(self):
        rc = self.home / ".bashrc"; rc.write_text("# private\n"); os.chmod(rc, 0o600)
        self.install()
        self.assertEqual(os.stat(rc).st_mode & 0o777, 0o600)

    def test_old_style_lines_from_earlier_versions_are_migrated_not_duplicated(self):
        (self.home / ".bashrc").write_text('# mine\n\n# Newton — Think it. Tab it. Done.\neval "$(newton init bash)"\n')
        self.install()
        rc = self.read(".bashrc")
        self.assertEqual(rc.count("newton init bash"), 1)                                  # loaded once, inside the block
        self.assertNotIn("Think it. Tab it. Done.", rc)
        self.assertIn('command -v newton >/dev/null 2>&1 && eval "$(newton init bash)"', rc)

    def test_no_path_flag_leaves_shell_config_alone(self):
        r = self.install("--no-path")
        self.assertEqual(r.returncode, 0); self.assertTrue(self.exe.exists()); self.assertFalse((self.home / ".bashrc").exists())

    def test_custom_bin_dir(self):
        target = self.home / "tools"
        r = self.install("--bin-dir", str(target))
        self.assertEqual(r.returncode, 0, r.stderr); self.assertTrue((target / "newton").exists())
        self.assertIn('export PATH="$HOME/tools:$PATH"', self.read(".bashrc"))                  # inside HOME → portable $HOME form
        outside = Path(tempfile.mkdtemp(prefix="newton-out-"))
        try:
            self.assertEqual(self.install("--bin-dir", str(outside)).returncode, 0)
            self.assertIn(f'export PATH="{outside}:$PATH"', self.read(".bashrc"))               # outside HOME → absolute path
        finally:
            shutil.rmtree(outside, ignore_errors=True)

    def test_path_with_spaces_in_home(self):
        spaced = Path(tempfile.mkdtemp()) / "my home"; spaced.mkdir()
        try:
            e = self.env(); e["HOME"] = str(spaced)
            r = subprocess.run(["sh", str(ROOT / "install.sh"), "--no-setup"], capture_output=True, text=True, env=e, cwd=str(spaced), timeout=120)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(subprocess.run([str(spaced / ".local/bin/newton"), "--version"], capture_output=True, text=True, env=e).returncode, 0)
        finally:
            shutil.rmtree(spaced.parent, ignore_errors=True)

    def test_warns_about_another_copy_that_would_confuse(self):
        other = self.home / "elsewhere"; other.mkdir()
        (other / "newton").write_text("#!/bin/sh\necho old\n"); os.chmod(other / "newton", 0o755)
        r = self.install(PATH=f"{other}{os.pathsep}{os.environ['PATH']}")
        self.assertIn("another copy exists at", r.stdout)

    @unittest.skipUnless(shutil.which("dash"), "dash not installed")
    def test_works_in_dash(self):
        r = self.install(sh="dash")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr); self.assertTrue(self.exe.exists())

    def test_script_is_valid_posix_sh(self):
        for sh in ("sh", "dash", "bash"):
            if shutil.which(sh):
                self.assertEqual(subprocess.run([sh, "-n", str(ROOT / "install.sh")]).returncode, 0, sh)

    def test_missing_python_gives_a_helpful_message(self):
        r = subprocess.run(["/bin/sh", str(ROOT / "install.sh")], capture_output=True, text=True, env={"HOME": str(self.home), "PATH": "/nonexistent"})
        self.assertEqual(r.returncode, 1)
        self.assertIn("needs Python 3.9", r.stderr); self.assertIn("Install it, then run this again", r.stderr)

    def test_run_from_the_wrong_place_explains_itself(self):
        lone = Path(tempfile.mkdtemp()); shutil.copy(ROOT / "install.sh", lone / "install.sh")
        try:
            r = subprocess.run(["sh", str(lone / "install.sh"), "--no-setup"], capture_output=True, text=True, env=self.env(), cwd=str(lone))
            self.assertEqual(r.returncode, 1); self.assertIn("unzipped Newton folder", r.stderr)
        finally:
            shutil.rmtree(lone, ignore_errors=True)

    def test_curl_pipe_style_install_downloads_then_installs(self):
        zip_path = make_zip(self.home / "release.zip")
        empty = self.home / "empty"; empty.mkdir()
        r = subprocess.run(["sh", "-s", "--", "--no-setup"], input=(ROOT / "install.sh").read_text(), capture_output=True, text=True,
                           env=self.env(NEWTON_URL="file://" + str(zip_path)), cwd=str(empty), timeout=120)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.newton("--version").stdout.strip(), "newton " + base_version())

    def test_download_over_plain_http_is_refused(self):
        empty = self.home / "empty"; empty.mkdir()
        r = subprocess.run(["sh", "-s", "--", "--no-setup"], input=(ROOT / "install.sh").read_text(), capture_output=True, text=True,
                           env=self.env(NEWTON_URL="http://example.invalid/newton.zip"), cwd=str(empty))
        self.assertNotEqual(r.returncode, 0); self.assertFalse(self.exe.exists())

    def test_a_broken_build_never_replaces_a_working_install(self):
        self.install(); before = self.exe.read_bytes()
        broken = Path(tempfile.mkdtemp()) / "newton"; shutil.copytree(ROOT / "newton", broken, ignore=shutil.ignore_patterns("__pycache__"))
        (broken / "cli.py").write_text("def main(:\n")                                       # syntax error
        try:
            r = subprocess.run([sys.executable, str(broken / "installer.py"), "install", "--no-setup", "--bin-dir", str(self.bin)],
                               capture_output=True, text=True, env=self.env())
            self.assertEqual(r.returncode, 1)
            self.assertEqual(self.exe.read_bytes(), before)                                 # untouched
            self.assertEqual([p.name for p in self.bin.iterdir()], ["newton"])               # and no temp file left over
        finally:
            shutil.rmtree(broken.parent, ignore_errors=True)


# ---------------------------------------------------------------------------------- setup + doctor

class SetupAndDoctorTests(Home):
    def test_setup_enables_tab_inside_the_same_block_and_survives_reinstall(self):
        self.install()
        r = self.newton("setup", stdin="1\n\n\n")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        rc = self.read(".bashrc")
        self.assertEqual(rc.count(BEGIN), 1)
        self.assertIn('eval "$(newton init bash)"', rc)
        self.install()                                                                       # reinstall must keep Tab enabled
        self.assertIn('eval "$(newton init bash)"', self.read(".bashrc"))
        self.assertEqual(self.read(".bashrc").count("newton init bash"), 1)

    def test_doctor_reports_the_install_and_path_problems(self):
        self.install()
        good = self.newton("doctor").stdout
        self.assertIn("single file", good); self.assertNotIn("isn't on your PATH", good)
        bad = self.newton("doctor", with_bin=False).stdout
        self.assertIn("isn't on your PATH", bad)


# ---------------------------------------------------------------------------------- update

class UpdateTests(Home):
    def setUp(self):
        super().setUp()
        self.install()
        self.dl = self.home / "Downloads"; self.dl.mkdir()

    def test_update_picks_the_newest_download_and_replaces_itself(self):
        make_zip(self.dl / "newton.zip")                                                     # same version as installed
        make_zip(self.dl / "newton (1).zip", "9.0.0")
        make_zip(self.dl / "newton (2).zip", "9.9.9")
        r = self.newton("update", "-y")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("9.9.9", r.stdout)
        self.assertEqual(self.newton("--version").stdout.strip(), "newton 9.9.9")
        self.assertEqual([p.name for p in self.bin.iterdir()], ["newton"])

    def test_update_finds_a_zip_dragged_into_the_home_folder_like_on_a_chromebook(self):
        make_zip(self.home / "newton.zip", "9.8.7")                                         # no Downloads folder content, just ~/
        r = self.newton("update", "-y")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr); self.assertEqual(self.newton("--version").stdout.strip(), "newton 9.8.7")

    def test_update_when_already_current_does_nothing_unless_forced(self):
        make_zip(self.dl / "newton.zip")
        self.assertIn("already up to date", self.newton("update", "-y").stdout)
        self.assertIn("updated to", self.newton("update", "-y", "--force").stdout)

    def test_update_never_downgrades(self):
        make_zip(self.dl / "old.zip", "0.0.1")
        r = self.newton("update", str(self.dl / "old.zip"), "-y")
        self.assertIn("already up to date", r.stdout); self.assertEqual(self.newton("--version").stdout.strip(), "newton " + base_version())

    def test_update_asks_first_and_can_be_declined(self):
        make_zip(self.dl / "newton.zip", "9.9.9")
        r = self.newton("update", stdin="n\n")
        self.assertIn("Continue?", r.stdout); self.assertEqual(self.newton("--version").stdout.strip(), "newton " + base_version())

    def test_update_from_an_explicit_path_with_spaces_and_from_a_file_url(self):
        z = make_zip(self.dl / "newton (3).zip", "9.1.0")
        self.assertEqual(self.newton("update", str(z), "-y").returncode, 0)
        self.assertEqual(self.newton("--version").stdout.strip(), "newton 9.1.0")
        z2 = make_zip(self.home / "net.zip", "9.2.0")
        self.assertEqual(self.newton("update", "file://" + str(z2), "-y").returncode, 0)
        self.assertEqual(self.newton("--version").stdout.strip(), "newton 9.2.0")

    def test_plain_http_updates_are_refused(self):
        r = self.newton("update", "http://example.invalid/newton.zip", "-y")
        self.assertEqual(r.returncode, 1); self.assertIn("https", r.stdout + r.stderr)

    def test_nothing_to_update_from_explains_what_to_do(self):
        r = self.newton("update", "-y")
        self.assertEqual(r.returncode, 1); self.assertIn("newton update ~/Downloads/newton.zip", r.stdout + r.stderr)

    def test_garbage_and_hostile_archives_are_rejected_and_leave_the_install_alone(self):
        (self.dl / "newton.zip").write_text("not a zip")
        r = self.newton("update", str(self.dl / "newton.zip"), "-y")
        self.assertEqual(r.returncode, 1); self.assertIn("not a Newton zip", r.stdout + r.stderr)
        evil = f"evil-{os.getpid()}.txt"
        with zipfile.ZipFile(self.dl / "slip.zip", "w") as z:
            z.writestr("../" + evil, "x"); z.writestr("newton/newton/__init__.py", '__version__ = "9.9.9"\n')
        r = self.newton("update", str(self.dl / "slip.zip"), "-y")
        self.assertEqual(r.returncode, 1); self.assertIn("unsafe path", r.stdout + r.stderr)
        self.assertFalse(Path(tempfile.gettempdir(), evil).exists()); self.assertFalse((self.home / evil).exists())
        self.assertEqual(self.newton("--version").stdout.strip(), "newton " + base_version())

    def test_update_keeps_tab_enabled_and_user_config(self):
        self.newton("setup", stdin="1\n\n\n")
        make_zip(self.dl / "newton.zip", "9.9.9")
        self.newton("update", "-y")
        self.assertIn('eval "$(newton init bash)"', self.read(".bashrc"))
        self.assertEqual(self.read(".bashrc").count(BEGIN), 1)


# ---------------------------------------------------------------------------------- uninstall

class UninstallTests(Home):
    def setUp(self):
        super().setUp()
        (self.home / ".bashrc").write_text("# mine\nalias ll='ls -l'\n")
        self.install()
        self.newton("setup", stdin="1\n\n\n")
        self.newton("config", "alternatives", "3")                                           # creates a config file

    def test_uninstall_removes_the_program_and_only_newtons_lines(self):
        r = self.newton("uninstall", "-y")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse(self.exe.exists())
        self.assertEqual(self.read(".bashrc"), "# mine\nalias ll='ll'\n".replace("'ll'", "'ls -l'"))
        self.assertTrue((self.home / ".config" / "newton").exists())                          # settings are kept by default

    def test_purge_also_deletes_settings(self):
        self.assertEqual(self.newton("uninstall", "--purge", "-y").returncode, 0)
        self.assertFalse((self.home / ".config" / "newton").exists())

    def test_declining_changes_nothing(self):
        r = self.newton("uninstall", stdin="n\n")
        self.assertIn("Nothing was changed", r.stdout); self.assertTrue(self.exe.exists()); self.assertIn(BEGIN, self.read(".bashrc"))

    def test_uninstall_cleans_old_style_lines_too(self):
        (self.home / ".zshrc").write_text('# Newton — Think it. Tab it. Done.\neval "$(newton init zsh)"\nexport A=1\n')
        self.newton("uninstall", "-y")
        self.assertEqual(self.read(".zshrc"), "export A=1\n")


# ---------------------------------------------------------------------------------- command-word routing

class RoutingTests(unittest.TestCase):
    def run_cli(self, *words):
        tmp = tempfile.mkdtemp()
        try:
            return subprocess.run([sys.executable, "-m", "newton", *words], capture_output=True, text=True, env=base.env(tmp), cwd=tmp, timeout=60)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_update_as_an_english_word_still_reaches_the_ai(self):
        r = self.run_cli("update", "all", "my", "brew", "packages")
        self.assertEqual(r.returncode, 0, r.stderr); self.assertNotIn("Nothing to update from", r.stdout + r.stderr)
        self.assertIn("ok", r.stdout)

    def test_bare_update_and_flags_are_the_command(self):
        r = self.run_cli("update", "-y")
        self.assertIn("Nothing to update from", r.stdout + r.stderr)

def _strip(s):
    return base._strip(s)


def _wait(term, text, timeout=25):
    end = time.time() + timeout
    while time.time() < end:
        if text in _strip(term.read(0.3)):
            return True
    return False


class GuidedSetupTests(Home):
    """The installer launches `newton setup` itself, in a real terminal, including when the script arrives on stdin."""

    def _drive(self, argv, cwd, **extra):
        (self.home / ".bashrc").write_text("# mine\n")
        t = base.Term(argv, self.env("bash", **extra), cwd)
        try:
            self.assertTrue(_wait(t, "Choice"), _strip(t.buf.decode(errors="replace"))[-600:])
            t.type("1\r", 0.5)
            self.assertTrue(_wait(t, "Paste key"), _strip(t.buf.decode(errors="replace"))[-600:])
            t.type("\r", 0.5)                                                                # leave the key blank (the mock AI needs none)
            self.assertTrue(_wait(t, "Your shell"), _strip(t.buf.decode(errors="replace"))[-600:])
            t.type("\r", 0.5)
            self.assertTrue(_wait(t, "Add Newton to"), _strip(t.buf.decode(errors="replace"))[-600:])
            t.type("\r", 0.5)
            self.assertTrue(_wait(t, "Open a new terminal"), _strip(t.buf.decode(errors="replace"))[-600:])
        finally:
            t.close()
        rc = self.read(".bashrc")
        self.assertIn('eval "$(newton init bash)"', rc); self.assertEqual(rc.count(BEGIN), 1)
        self.assertTrue(self.exe.exists())

    def test_installer_runs_setup_in_a_terminal(self):
        self._drive(["sh", str(ROOT / "install.sh")], str(self.home))

    def test_installer_piped_from_curl_still_asks_questions_through_the_terminal(self):
        zip_path = make_zip(self.home / "release.zip")
        empty = self.home / "empty"; empty.mkdir()
        self._drive(["sh", "-c", f"sh -s < '{ROOT / 'install.sh'}'"], str(empty), NEWTON_URL="file://" + str(zip_path))


# ---------------------------------------------------------------------------------- the whole journey in real shells

@unittest.skipUnless(shutil.which("zsh") and shutil.which("fish") and shutil.which("bash"), "needs zsh, bash and fish")
class JourneyTests(Home):
    """install → setup → open a brand-new terminal → type a sentence → Tab. `newton` is only reachable through
    the PATH lines the installer wrote, so this proves the lines work, in each shell."""

    def journey(self, shell):
        pre = {
            "bash": (".bashrc", ["PS1='$ '"]),
            "zsh": (".zshrc", ["PS1='$ '", "autoload -Uz compinit && compinit -u"]),
            "fish": (".config/fish/config.fish", ["function fish_prompt; echo -n '$ '; end", "set -g fish_greeting"]),
        }[shell]
        rc = self.home / pre[0]; rc.parent.mkdir(parents=True, exist_ok=True); rc.write_text("\n".join(pre[1]) + "\n")
        r = self.install(shell=shell)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        r = self.newton("setup", stdin="1\n\n\n", shell=shell)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        e = self.env(shell, with_bin=False)                                                   # the new terminal does NOT start with ~/.local/bin on PATH
        argv = {"bash": ["bash", "-i"], "zsh": ["zsh", "-i"], "fish": ["fish", "-i"]}[shell]
        t = base.Term(argv, e, str(self.home))
        try:
            t.type("kill whatever is using port 3000", 0.3)
            screen = _strip(t.type("\t", 2.5))
            self.assertIn("lsof -ti tcp:3000 | xargs kill", screen, f"{shell}: Tab produced nothing after a fresh install\n{screen[-700:]}")
            t.buf = b""
            t.type("\x15", 0.3)                                                               # clear the line
            out = _strip(t.type("command -v newton\r", 1.0))
            self.assertIn(".local/bin/newton", out)
        finally:
            t.close()

    def test_bash(self): self.journey("bash")
    def test_zsh(self): self.journey("zsh")
    def test_fish(self): self.journey("fish")


if __name__ == "__main__":
    unittest.main(verbosity=2)
