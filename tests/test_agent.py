"""Tests for Newton 2.0: plan mode, ask/chat, fix, commit and the shell hooks.

Run:  python3 -W ignore -m unittest tests.test_agent -v
Uses the same local mock of the AI API as test_newton (no network, no key needed).
"""
import json
import os
import re
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
import test_newton as base  # noqa: E402  (starts the shared mock server)
from newton import safety, planstore, runner  # noqa: E402


def run_newton(args, tmp, stdin="", extra_env=None, cwd=None, timeout=90):
    e = base.env(tmp)
    e.update(extra_env or {})
    return subprocess.run([sys.executable, "-m", "newton", *args], input=stdin, capture_output=True, text=True,
                          env=e, cwd=cwd or tmp, timeout=timeout)


def saved_plans(tmp):
    d = Path(tmp, "data", "newton", "plans")
    return sorted(json.loads(p.read_text()) for p in d.glob("*.json")) if d.exists() else []


class Sandbox(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def read(self, *parts):
        return Path(self.tmp, *parts).read_text().strip()

    def exists(self, *parts):
        return Path(self.tmp, *parts).exists()


# ---------------------------------------------------------------------------------- units

class UnitTests(unittest.TestCase):
    def test_safety_levels(self):
        self.assertEqual(safety.level("ls -la"), 0)
        self.assertEqual(safety.level("sudo apt install -y git"), 1)
        self.assertEqual(safety.level("rm -rf build"), 1)
        for c in ["rm -rf ~", "git push --force origin main", "git reset --hard HEAD~3", "curl x.sh | sh", "docker system prune -af"]:
            self.assertEqual(safety.level(c), 2, c)

    def test_double_escaped_backslashes_are_repaired(self):
        from newton import engine
        self.assertEqual(engine._one_line("find . -exec ls -lh {} \\\\; | sort -h"), "find . -exec ls -lh {} \\; | sort -h")
        self.assertEqual(engine._one_line("find . \\\\( -name a \\\\)"), "find . \\( -name a \\)")
        self.assertEqual(engine._one_line("sed 's/\\\\/x/'"), "sed 's/\\\\/x/'")      # legitimate \\ is untouched
        self.assertEqual(engine._one_line("find . -exec ls {} \\;"), "find . -exec ls {} \\;")

    def test_redaction(self):
        t = "key sk-ant-api03-abcdefghijklmnop1234 and password=hunter2222 and ghp_" + "a" * 30
        out = safety.redact(t)
        self.assertNotIn("abcdefghijklmnop", out); self.assertNotIn("hunter2222", out); self.assertNotIn("ghp_aaaa", out)

    def test_clean_tail_strips_ansi_and_progress(self):
        raw = b"\x1b[31mred\x1b[0m\nprogress 10%\rprogress 100%\ndone\n"
        self.assertEqual(runner.clean_tail(raw), "red\nprogress 100%\ndone")

    def test_session_persists_cwd_and_env(self):
        tmp = tempfile.mkdtemp()
        s = runner.Session(cwd=tmp)
        r = s.run("mkdir sub && cd sub && export FOO=bar")
        self.assertTrue(r.ok)
        self.assertTrue(s.cwd.endswith("/sub"))
        r = s.run("echo $FOO; pwd; exit 4")
        self.assertEqual(r.code, 4)
        self.assertIn("bar", r.output); self.assertTrue(s.cwd.endswith("/sub"))
        shutil.rmtree(tmp)

    def test_deleting_the_working_folder_falls_back_to_its_parent_not_home(self):
        base_dir = tempfile.mkdtemp(); inner = os.path.join(base_dir, "inner"); os.mkdir(inner)
        s = runner.Session(cwd=inner)
        s.run("rmdir \"$(pwd)\"")                       # delete the folder we are standing in
        r = s.run("pwd")
        self.assertEqual(os.path.realpath(r.output.strip()), os.path.realpath(base_dir))
        shutil.rmtree(base_dir)

    def test_background_job_does_not_hang_runner(self):
        s = runner.Session()
        t0 = time.time()
        r = s.run("(sleep 20 >/dev/null 2>&1 &) ; echo started")
        self.assertTrue(r.ok); self.assertLess(time.time() - t0, 8)

    def test_plan_normalisation_raises_risk(self):
        from newton import brain
        steps = brain.norm_steps([{"title": "x", "command": "git push --force", "risk": "safe"},
                                  {"title": "m", "manual": "do a thing"}, {"nothing": 1}], 10)
        self.assertEqual([s["risk"] for s in steps], ["danger", "safe"])
        self.assertEqual(len(steps), 2)

    def test_plan_ids_and_prefix_lookup(self):
        os.environ["XDG_DATA_HOME"] = tempfile.mkdtemp()
        try:
            p = planstore.fresh("g", {"goal": "G", "steps": []}, "/tmp")
            planstore.save(p)
            self.assertEqual(planstore.load(p["id"][:10])["id"], p["id"])
            self.assertEqual(planstore.current()["id"], p["id"])
            self.assertTrue(planstore.delete(p["id"])); self.assertIsNone(planstore.current())
        finally:
            del os.environ["XDG_DATA_HOME"]


# ---------------------------------------------------------------------------------- plan mode

class PlanTests(Sandbox):
    def test_dry_run_saves_nothing(self):
        r = run_newton(["plan", "--dry-run", "a", "static", "site"], self.tmp)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Static site", r.stdout); self.assertIn("Create project folder", r.stdout); self.assertIn("dry run", r.stdout)
        self.assertEqual(saved_plans(self.tmp), [])

    def test_full_run_carries_cwd_env_and_inputs(self):
        # start ⏎ · SITE_NAME=mysite · then ⏎ for each of the 3 steps
        r = run_newton(["plan", "static", "site"], self.tmp, stdin="\nmysite\n\n\n\n")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Plan complete", r.stdout)
        self.assertTrue(self.exists("mysite", "index.html"))
        self.assertTrue(self.read("mysite", "where.txt").endswith("/mysite"))    # cd carried into step 3
        self.assertEqual(self.read("mysite", "built.txt"), "yes")                 # export carried into step 3
        self.assertIn("cd ", r.stdout)                                            # tells you where the plan ended
        self.assertIn("Open index.html in a browser.", r.stdout)
        plan = saved_plans(self.tmp)[0]
        self.assertEqual(plan["status"], "done"); self.assertEqual({s["status"] for s in plan["steps"]}, {"done"})

    def test_checklist_header_shows_progress(self):
        r = run_newton(["plan", "static", "site"], self.tmp, stdin="\nx\n\n\n\n")
        self.assertIn("◆ Static site", r.stdout)
        self.assertIn("step 2 of 3", r.stdout); self.assertIn("66%", r.stdout)
        self.assertRegex(r.stdout, r"✓\s+1\s+Create project folder")
        self.assertRegex(r.stdout, r"▸\s+3\s+Record where we are")

    def test_yes_auto_runs_safe_steps_with_defaults(self):
        r = run_newton(["plan", "-y", "static", "site"], self.tmp, stdin="\n")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("auto-running", r.stdout)
        self.assertTrue(self.exists("demo", "index.html"))

    def test_danger_step_needs_explicit_y_even_with_yes(self):
        r = run_newton(["plan", "-y", "danger", "plan"], self.tmp, stdin="\n" + "\n" + "y\n")
        self.assertIn("marked danger", r.stdout)                                   # plain Enter was refused
        self.assertFalse(self.exists("build"))                                     # then y ran it
        self.assertTrue(self.exists("done.txt")); self.assertIn("Plan complete", r.stdout)

    def test_failure_is_diagnosed_fixed_and_retried(self):
        r = run_newton(["plan", "failing", "plan"], self.tmp, stdin="\n" + "\n" + "\n" + "\n" + "\n")
        self.assertIn("Step failed", r.stdout)
        self.assertIn("missing.txt doesn't exist", r.stdout); self.assertIn("Suggested fix", r.stdout)
        self.assertEqual(self.read("got.txt"), "data")                             # fix ran, then the original step re-ran
        self.assertTrue(self.exists("ok.txt")); self.assertIn("Plan complete", r.stdout)

    def test_skip_pause_status_prompt_and_resume(self):
        r = run_newton(["plan", "failing", "plan"], self.tmp, stdin="\n" + "s\n" + "q\n")
        self.assertIn("Paused", r.stdout)
        plan = saved_plans(self.tmp)[0]
        self.assertEqual([s["status"] for s in plan["steps"]], ["skipped", "pending", "pending"])
        # status / prompt badge / plans listing all reflect it
        st = run_newton(["status"], self.tmp)
        self.assertIn("↷", st.stdout); self.assertIn("▸", st.stdout)
        self.assertEqual(run_newton(["prompt"], self.tmp).stdout.strip(), "◆ Failing plan · 1/3")
        self.assertIn("Failing plan", run_newton(["plans"], self.tmp).stdout)
        md = run_newton(["status", "--md"], self.tmp).stdout
        self.assertIn("- [x] Say hello", md); self.assertIn("- [ ] Finish", md)
        # resume: step 2 fails → fix → retry, then step 3
        r2 = run_newton(["resume"], self.tmp, stdin="\n" + "\n" + "\n")
        self.assertIn("Resuming", r2.stdout); self.assertIn("Plan complete", r2.stdout)
        self.assertFalse(self.exists("hello.txt"))                                 # skipped step never ran
        self.assertTrue(self.exists("ok.txt"))
        self.assertEqual(run_newton(["prompt"], self.tmp).stdout.strip(), "")      # nothing active any more

    def test_manual_step(self):
        r = run_newton(["plan", "manual", "plan"], self.tmp, stdin="\n" + "\n" + "\n")
        self.assertIn("Create a key in your dashboard", r.stdout)
        self.assertTrue(self.exists("marker.txt")); self.assertIn("Plan complete", r.stdout)

    def test_revise_before_starting(self):
        r = run_newton(["plan", "failing", "plan"], self.tmp, stdin="r\n" + "make it shorter\n" + "\n" + "\n")
        self.assertIn("plan updated", r.stdout)
        self.assertTrue(self.exists("revised.txt")); self.assertFalse(self.exists("hello.txt"))

    def test_explain_a_step(self):
        r = run_newton(["plan", "failing", "plan"], self.tmp, stdin="\n" + "?\n" + "q\n")
        self.assertIn("Extracts a gzipped tarball", r.stdout)                      # explain output from the mock

    def test_impossible_goal_is_reported(self):
        r = run_newton(["plan", "impossible", "thing"], self.tmp)
        self.assertEqual(r.returncode, 1); self.assertIn("can't be done from a terminal", r.stderr)

    def test_no_secrets_reach_the_ai_on_failure(self):
        r = run_newton(["plan", "failing", "plan"], self.tmp, stdin="\n" + "\n" + "q\n" + "q\n")
        self.assertEqual(r.returncode, 0)
        sent = json.dumps(mock_api.CALLS[-1])
        self.assertNotIn("test-key", sent)


# ---------------------------------------------------------------------------------- ask / chat / fix / commit

class AskChatTests(Sandbox):
    def test_ask_streams_an_answer(self):
        r = run_newton(["ask", "how", "do", "I", "list", "files"], self.tmp)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("ls -la", r.stdout); self.assertIn("hidden", r.stdout)
        self.assertTrue(mock_api.CALLS[-1].get("stream"))

    def test_ask_redacts_piped_secrets(self):
        r = run_newton(["ask", "what", "is", "wrong"], self.tmp, stdin="error: token=abcd1234secret and sk-ant-api03-zzzzzzzzzzzzzzzz\n")
        self.assertEqual(r.returncode, 0)
        sent = json.dumps(mock_api.CALLS[-1])
        self.assertIn("error:", sent); self.assertNotIn("abcd1234secret", sent); self.assertNotIn("zzzzzzzzzzzzzzzz", sent)

    def test_ask_attaches_files_but_refuses_secret_files(self):
        Path(self.tmp, "app.py").write_text("print('needle-in-file')\n")
        Path(self.tmp, ".env").write_text("API_KEY=nope\n")
        ok = run_newton(["ask", "-f", "app.py", "explain"], self.tmp)
        self.assertEqual(ok.returncode, 0); self.assertIn("needle-in-file", json.dumps(mock_api.CALLS[-1]))
        n = len(mock_api.CALLS)
        bad = run_newton(["ask", "-f", ".env", "explain"], self.tmp)
        self.assertEqual(bad.returncode, 1); self.assertIn("secrets", bad.stderr)
        self.assertEqual(len(mock_api.CALLS), n)                                   # nothing was sent

    def test_chat_answers_and_runs_a_snippet(self):
        r = run_newton(["chat"], self.tmp, stdin="list my files\n/run\n\n/exit\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("ls -la", r.stdout); self.assertIn("/run to execute", r.stdout)
        self.assertIn("exit 0", r.stdout)

    def test_chat_bang_command_is_seen_by_ai(self):
        r = run_newton(["chat"], self.tmp, stdin="!echo hello-from-chat\nwhat did that print\n/exit\n")
        self.assertIn("hello-from-chat", json.dumps(mock_api.CALLS[-1]))
        self.assertEqual(r.returncode, 0)


class FixTests(Sandbox):
    def test_fix_reruns_diagnoses_fixes_and_retries(self):
        r = run_newton(["fix"], self.tmp, stdin="\n" + "\n", extra_env={"NEWTON_LAST_CMD": "cat missing.txt", "NEWTON_LAST_STATUS": "1"})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("missing.txt doesn't exist", r.stdout); self.assertIn("All good", r.stdout)
        self.assertEqual(self.read("missing.txt"), "data")

    def test_fix_reads_the_shell_hook_file(self):
        f = Path(self.tmp, "last"); f.write_text("2\ncat missing.txt\n")
        r = run_newton(["fix"], self.tmp, stdin="q\n", extra_env={"NEWTON_LAST_FILE": str(f)})
        self.assertIn("cat missing.txt", r.stdout); self.assertIn("exit 2", r.stdout)

    def test_fix_says_so_when_last_command_succeeded(self):
        r = run_newton(["fix"], self.tmp, extra_env={"NEWTON_LAST_CMD": "ls", "NEWTON_LAST_STATUS": "0"})
        self.assertIn("succeeded", r.stdout)

    def test_fix_never_reruns_destructive_commands(self):
        r = run_newton(["fix"], self.tmp, extra_env={"NEWTON_LAST_CMD": "git reset --hard HEAD~1", "NEWTON_LAST_STATUS": "1"})
        self.assertIn("won't re-run", r.stdout)

    def test_fix_without_hook_explains_how(self):
        r = run_newton(["fix"], self.tmp, extra_env={"NEWTON_LAST_CMD": "", "NEWTON_LAST_FILE": ""})
        self.assertEqual(r.returncode, 1); self.assertIn("doesn't know your last command", r.stderr)


@unittest.skipUnless(shutil.which("git"), "git not installed")
class CommitTests(Sandbox):
    def git(self, *a):
        return subprocess.run(["git", *a], cwd=self.tmp, capture_output=True, text=True)

    def setUp(self):
        super().setUp()
        self.git("init", "-q"); self.git("config", "user.email", "t@t.t"); self.git("config", "user.name", "T")

    def test_commit_staged(self):
        Path(self.tmp, "hello.sh").write_text("echo hi\n"); self.git("add", "hello.sh")
        r = run_newton(["commit"], self.tmp, stdin="\n")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.git("log", "-1", "--format=%s").stdout.strip(), "Add greeting script")
        self.assertIn("Gives the demo something to run.", self.git("log", "-1", "--format=%b").stdout)

    def test_commit_offers_to_stage_everything(self):
        Path(self.tmp, "a.txt").write_text("a\n")
        r = run_newton(["commit"], self.tmp, stdin="\n" + "\n")
        self.assertIn("Nothing is staged", r.stdout)
        self.assertEqual(self.git("log", "-1", "--format=%s").stdout.strip(), "Add greeting script")

    def test_commit_cancel_keeps_changes_staged(self):
        Path(self.tmp, "b.txt").write_text("b\n"); self.git("add", "b.txt")
        run_newton(["commit"], self.tmp, stdin="q\n")
        self.assertEqual(self.git("log").returncode, 128)                          # still no commits
        self.assertIn("b.txt", self.git("diff", "--cached", "--name-only").stdout)

    def test_commit_outside_repo(self):
        other = tempfile.mkdtemp()
        r = run_newton(["commit"], self.tmp, cwd=other)
        self.assertEqual(r.returncode, 1); self.assertIn("isn't inside a git repository", r.stderr)
        shutil.rmtree(other)


# ---------------------------------------------------------------------------------- live terminals

def wait_for(term, text, timeout=25):
    end = time.time() + timeout
    while time.time() < end:
        if text in base._strip(term.read(0.3)):
            return True
    return False


class LiveTerminalTests(Sandbox):
    def test_plan_mode_with_real_keypresses_in_a_pty(self):
        """Newton in a genuine terminal: single-key prompts (no Enter needed), pty-run steps, live checklist."""
        t = base.Term([sys.executable, "-m", "newton", "plan", "static", "site"], base.env(self.tmp), self.tmp)
        try:
            self.assertTrue(wait_for(t, "start"), base._strip(t.buf.decode(errors="replace"))[-600:])
            t.type("\r", 0.5)                                       # start
            self.assertTrue(wait_for(t, "Site name?"))
            t.type("pty-site\r", 0.5)                               # answer the input
            for _ in range(3):                                      # three steps, each a single ⏎ keypress
                self.assertTrue(wait_for(t, "run"), "no run prompt")
                t.buf = b""
                t.type("\r", 1.2)
            self.assertTrue(wait_for(t, "Plan complete"), base._strip(t.buf.decode(errors="replace"))[-800:])
        finally:
            t.close()
        self.assertTrue(self.exists("pty-site", "index.html"))
        self.assertEqual(self.read("pty-site", "built.txt"), "yes")

    def test_ctrl_c_pauses_instead_of_losing_the_plan(self):
        t = base.Term([sys.executable, "-m", "newton", "plan", "failing", "plan"], base.env(self.tmp), self.tmp)
        try:
            self.assertTrue(wait_for(t, "start"))
            t.type("\r", 0.6)
            self.assertTrue(wait_for(t, "run"))
            t.type("\x03", 1.0)                                     # Ctrl+C at the prompt
            self.assertTrue(wait_for(t, "Paused"), base._strip(t.buf.decode(errors="replace"))[-500:])
        finally:
            t.close()
        self.assertEqual(saved_plans(self.tmp)[0]["status"], "active")


@unittest.skipUnless(shutil.which("zsh") and shutil.which("fish"), "needs zsh + fish")
class ShellHookTests(Sandbox):
    """The shell integration records your last command + exit status to a private file for `newton fix`."""

    def session(self, shell):
        e = base.env(self.tmp); e["SHELL"] = shutil.which(shell)
        if shell == "fish":
            p = Path(e["XDG_CONFIG_HOME"], "fish"); p.mkdir(parents=True)
            p.joinpath("config.fish").write_text("function fish_prompt; echo -n '$ '; end\nset -g fish_greeting\nnewton init fish | source\n")
            argv = ["fish", "-i"]
        elif shell == "zsh":
            Path(self.tmp, ".zshrc").write_text("PS1='$ '\nautoload -Uz compinit && compinit -u\neval \"$(newton init zsh)\"\n")
            argv = ["zsh", "-i"]
        else:
            Path(self.tmp, ".bashrc").write_text("PS1='$ '\neval \"$(newton init bash)\"\n")
            argv = ["bash", "--rcfile", f"{self.tmp}/.bashrc", "-i"]
        return base.Term(argv, e, self.tmp)

    def check(self, shell):
        t = self.session(shell)
        try:
            t.type("false\r", 0.8)
            out = base._strip(t.type("echo LAST=$(cat $NEWTON_LAST_FILE | tr '\\n' '|')\r", 1.2))
            self.assertIn("LAST=1|false|", out, f"{shell}: failed command not recorded\n{out[-500:]}")
            t.type("echo hi\r", 0.8)
            out = base._strip(t.type("echo LAST=$(cat $NEWTON_LAST_FILE | tr '\\n' '|')\r", 1.2))
            self.assertIn("LAST=0|echo hi|", out, f"{shell}: success not recorded\n{out[-500:]}")
            # running newton itself must not overwrite the record
            t.type("newton --version\r", 1.5)
            out = base._strip(t.type("echo LAST=$(cat $NEWTON_LAST_FILE | tr '\\n' '|')\r", 1.2))
            self.assertIn("LAST=0|echo hi|", out, f"{shell}: newton overwrote the record\n{out[-500:]}")
            # pressing Enter on an empty line must not reset a failing status to 0
            t.type("false\r", 0.8); t.type("\r", 0.5); t.type("\r", 0.5)
            out = base._strip(t.type("echo LAST=$(cat $NEWTON_LAST_FILE | tr '\\n' '|')\r", 1.2))
            self.assertIn("LAST=1|false|", out, f"{shell}: empty Enter clobbered the status\n{out[-500:]}")
            # end-to-end: `newton fix` sees the failed command from the file
            Path(self.tmp, "missing.txt").unlink(missing_ok=True)
            t.type("cat missing.txt\r", 0.8)
            t.buf = b""
            t.type("newton fix\r", 2.0)
            out = base._strip(t.buf.decode(errors="replace"))
            self.assertIn("cat missing.txt", out, f"{shell}: fix didn't find the command\n{out[-600:]}")
            self.assertIn("exit 1", out)
            t.type("q", 0.5)
            # no command text leaks into child-process environments
            out = base._strip(t.type("env | grep -c 'missing.txt'\r", 1.0))
            tail = out.split("grep -c 'missing.txt'")[-1]
            self.assertRegex(tail, r"(?<![\d;])0\s*\n", f"{shell}: last command leaked into the environment\n{out[-300:]}")
        finally:
            t.close()

    def test_zsh(self): self.check("zsh")
    def test_bash(self): self.check("bash")
    def test_fish(self): self.check("fish")

    def test_cache_dir_is_owner_only(self):
        self.check("zsh")
        mode = os.stat(Path(self.tmp, "cache", "newton")).st_mode & 0o777
        self.assertEqual(mode, 0o700)


# ---------------------------------------------------------------------------------- 2.1: reliability, preflight, undo, export

class ReliabilityTests(Sandbox):
    def test_unparseable_first_reply_is_retried_strictly(self):
        n = len(mock_api.CALLS)
        r = run_newton(["plan", "--dry-run", "flaky", "thing"], self.tmp)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Flaky plan", r.stdout)
        plan_calls = [c for c in mock_api.CALLS[n:] if "PLAN MODE" in c.get("system", "")]
        self.assertEqual(len(plan_calls), 2)
        self.assertIn("could not be parsed", plan_calls[1]["messages"][-1]["content"])

    def test_invalid_escapes_and_trailing_commas_are_repaired(self):
        r = run_newton(["plan", "--dry-run", "escapes", "demo"], self.tmp)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        j = json.loads(run_newton(["plan", "--json", "escapes", "demo"], self.tmp).stdout)
        self.assertEqual(j["steps"][0]["command"], "find . -name x -exec ls {} \\; | sort")

    def test_bare_string_steps_are_accepted(self):
        j = json.loads(run_newton(["plan", "--json", "stringy", "plan"], self.tmp).stdout)
        self.assertEqual([s["command"] for s in j["steps"]], ["echo one > one.txt", "echo two > two.txt"])


class PreflightAndTimingTests(Sandbox):
    def test_needs_line_marks_missing_tools(self):
        r = run_newton(["plan", "--dry-run", "scaffold"], self.tmp)
        self.assertRegex(r.stdout, r"needs\s+.*definitely-not-installed-xyz")
        self.assertRegex(r.stdout, r"✗ definitely-not-installed-xyz")
        self.assertIn("not found on this machine yet", r.stdout)

    def test_final_summary_shows_step_durations_and_undo_hint(self):
        r = run_newton(["plan", "scaffold"], self.tmp, stdin="\n\n\n\n\n")
        self.assertIn("Plan complete", r.stdout)
        self.assertRegex(r.stdout, r"Add b file\s+1s")                 # the slow step shows its duration
        self.assertIn("newton plans undo", r.stdout)
        self.assertGreater(saved_plans(self.tmp)[0]["steps"][2]["seconds"], 1.0)


class UndoTests(Sandbox):
    def finished_scaffold(self):
        r = run_newton(["plan", "scaffold"], self.tmp, stdin="\n\n\n\n\n")
        self.assertIn("Plan complete", r.stdout, r.stdout + r.stderr)
        self.assertTrue(self.exists("proj", "a.txt"))

    def test_undo_runs_newest_first_in_the_right_folder(self):
        self.finished_scaffold()
        r = run_newton(["plans", "undo"], self.tmp, stdin="\n\n")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertLess(r.stdout.index("Write a file"), r.stdout.index("Create project"))
        self.assertIn("2 of 2 steps undone", r.stdout)
        self.assertIn("No automatic undo for: Add b file", r.stdout)
        self.assertFalse(self.exists("proj"))
        self.assertEqual(saved_plans(self.tmp)[0]["status"], "undone")
        self.assertEqual(run_newton(["prompt"], self.tmp).stdout.strip(), "")
        self.assertIn("rolled back", run_newton(["resume", saved_plans(self.tmp)[0]["id"]], self.tmp).stdout)

    def test_skipping_an_undo_leaves_that_step_alone(self):
        self.finished_scaffold()
        r = run_newton(["plans", "undo"], self.tmp, stdin="\ns\n")          # undo the file, skip undoing the folder
        self.assertIn("left as it is", r.stdout); self.assertIn("1 of 2 steps undone", r.stdout)
        self.assertTrue(self.exists("proj"))                                  # skipped: project folder untouched
        self.assertFalse(self.exists("proj", "a.txt"))                        # not skipped: file removed

    def test_destructive_undo_needs_explicit_y(self):
        run_newton(["plan", "reversible", "thing"], self.tmp, stdin="\n\n")
        r = run_newton(["plans", "undo"], self.tmp, stdin="\ns\n")
        self.assertIn("marked danger", r.stdout); self.assertIn("0 of 1 steps undone", r.stdout)

    def test_nothing_to_undo(self):
        r = run_newton(["plans", "undo"], self.tmp)
        self.assertEqual(r.returncode, 1); self.assertIn("Nothing to undo", r.stderr)


class ExportTests(Sandbox):
    def test_exported_script_is_valid_and_reproduces_the_plan(self):
        run_newton(["plan", "static", "site"], self.tmp, stdin="\nmysite\n\n\n\n")
        out = Path(self.tmp, "setup.sh")
        r = run_newton(["plans", "export", "-o", str(out)], self.tmp)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(os.access(out, os.X_OK))
        self.assertEqual(subprocess.run(["bash", "-n", str(out)]).returncode, 0)
        text = out.read_text()
        self.assertIn("set -euo pipefail", text); self.assertIn(': "${SITE_NAME:=mysite}"', text)
        # run it somewhere else with a different name: it must build the same site
        other = tempfile.mkdtemp()
        try:
            res = subprocess.run(["bash", str(out)], cwd=other, env={**os.environ, "SITE_NAME": "elsewhere"}, capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertTrue(Path(other, "elsewhere", "index.html").exists())
            self.assertEqual(Path(other, "elsewhere", "built.txt").read_text().strip(), "yes")
        finally:
            shutil.rmtree(other, ignore_errors=True)

    def test_exported_script_asks_before_danger_and_notes_manual_steps(self):
        run_newton(["plan", "danger", "plan"], self.tmp, stdin="\n\n\n")
        text = run_newton(["plans", "export"], self.tmp).stdout
        self.assertIn("is marked danger. Continue? [y/N]", text)
        run_newton(["plan", "manual", "plan"], self.tmp, stdin="\n\n\n")
        self.assertIn("MANUAL STEP: Create a key", run_newton(["plans", "export"], self.tmp).stdout)

    def test_export_markdown(self):
        run_newton(["plan", "static", "site"], self.tmp, stdin="\n\n\n\n\n")
        md = run_newton(["plans", "export", "--md"], self.tmp).stdout
        self.assertTrue(md.startswith("# Static site")); self.assertIn("1. [x] **Create project folder**", md); self.assertIn("```sh", md)


class EdgeCaseTests(Sandbox):
    def test_resume_refuses_to_run_in_a_deleted_folder(self):
        work = Path(self.tmp, "work"); work.mkdir()
        run_newton(["plan", "failing", "plan"], self.tmp, stdin="\n" + "q\n", cwd=str(work))
        shutil.rmtree(work)
        r = run_newton(["resume"], self.tmp, stdin="q\n")
        self.assertIn("no longer exists", r.stdout); self.assertIn("Paused", r.stdout)
        self.assertFalse(self.exists("hello.txt"))                          # nothing ran in the wrong place
        r2 = run_newton(["resume"], self.tmp, stdin="h\n" + "\n" + "q\n")
        self.assertTrue(self.exists("hello.txt"))                           # 'continue here' ran in the current folder

    def test_plan_without_goal_when_piped_explains_usage(self):
        r = run_newton(["plan"], self.tmp)
        self.assertEqual(r.returncode, 2); self.assertIn("Describe your goal", r.stderr)


class LiveV21Tests(Sandbox):
    def test_plan_without_goal_offers_to_resume_the_unfinished_plan(self):
        run_newton(["plan", "failing", "plan"], self.tmp, stdin="\n" + "q\n")              # leaves a paused plan behind
        t = base.Term([sys.executable, "-m", "newton", "plan"], base.env(self.tmp), self.tmp)
        try:
            self.assertTrue(wait_for(t, "Unfinished plan: Failing plan"), base._strip(t.buf.decode(errors="replace"))[-400:])
            t.type("\r", 0.8)
            self.assertTrue(wait_for(t, "Resuming"), base._strip(t.buf.decode(errors="replace"))[-400:])
        finally:
            t.close()

    def test_no_goal_prompt_and_tab_title_in_a_real_terminal(self):
        t = base.Term([sys.executable, "-m", "newton", "plan"], base.env(self.tmp), self.tmp)
        try:
            self.assertTrue(wait_for(t, "What do you want to get done?"), base._strip(t.buf.decode(errors="replace"))[-400:])
            t.type("static site\r", 0.5)
            self.assertTrue(wait_for(t, "start"))
            t.type("\r", 0.5)
            self.assertTrue(wait_for(t, "Site name?"))
            t.type("titled\r", 1.0)
            self.assertTrue(wait_for(t, "run"))
            raw = t.buf.decode(errors="replace")
            self.assertIn("\x1b]0;◆ Static site · 0/3\x07", raw)            # progress lives in the tab title
        finally:
            t.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
