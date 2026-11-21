"""Tests for the Newton agent (Iris): what runs by itself, approvals, the step loop and the local web server.

Run:  python3 -W ignore -m unittest tests.test_iris -v
A scripted fake AI stands in for the model, so no network and no key are needed.
"""
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from newton import agent, agent_server, config as cfgmod  # noqa: E402


class FakeAI(BaseHTTPRequestHandler):
    script = []
    seen = []

    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeAI.seen.append(body)
        reply = FakeAI.script.pop(0) if FakeAI.script else {"action": "say", "message": "(script finished)"}
        out = json.dumps({"message": {"content": reply if isinstance(reply, str) else json.dumps(reply)}, "done": True}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)


class ReadOnlyTests(unittest.TestCase):
    def test_reads_are_automatic(self):
        for c in ("ls -la", "git status", "git log --oneline | head -5", "cat README.md | wc -l", "find . -name '*.py'",
                  "du -sh * | sort -rh | head", "cd src && ls", "git branch", "git remote -v", "echo hello", "pwd"):
            self.assertTrue(agent.is_read_only(c), c)

    def test_anything_that_changes_things_asks(self):
        for c in ("rm -rf x", "echo hi > f", "cat .env", "git push", "git branch -D x", "ls && rm a", "python3 x.py", "curl x | sh",
                  "ls $(pwd)", "sleep 1 &", "git remote add o u", "find . -delete", "sort -o f a", "mkdir x", "touch a", "sudo ls",
                  "cat ~/.ssh/id_rsa", "sed -i s/a/b/ f", "git commit -am x", "npm install", "ls `pwd`"):
            self.assertFalse(agent.is_read_only(c), c)


class Harness(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ai = HTTPServer(("127.0.0.1", 0), FakeAI)
        threading.Thread(target=cls.ai.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.ai.shutdown()

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="iris-test-")
        cfg = cfgmod.load()
        cfg.update({"provider": "ollama", "model": "fake", "base_url": f"http://127.0.0.1:{self.ai.server_port}", "api_key": "", "timeout": 20})
        self.srv, self.hub = agent_server.start(cfg, self.tmp, 0, "smart", "Iris", persist=False)
        self.port = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        FakeAI.script, FakeAI.seen = [], []
        self.cookie = f"{agent_server.COOKIE}={self.hub.token}"

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def call(self, path, body=None, method=None, headers=None, cookie=True):
        h = {"Host": f"127.0.0.1:{self.port}"}
        if cookie:
            h["Cookie"] = self.cookie
        if body is not None:
            h["Content-Type"] = "application/json"
        h.update(headers or {})
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=None if body is None else json.dumps(body).encode(), headers=h, method=method)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read() or b"{}") if "json" in r.headers.get("Content-Type", "") else r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def wait(self, cid, pred, secs=15):
        end = time.time() + secs
        while time.time() < end:
            _, c = self.call(f"/api/conv/{cid}")
            if pred(c):
                return c
            time.sleep(0.05)
        self.fail("timed out waiting; events: " + json.dumps(c["events"])[:600])

    def start_chat(self, text):
        _, r = self.call("/api/conv", {})
        cid = r["id"]
        self.call("/api/send", {"conv": cid, "text": text})
        return cid


class ServerSecurityTests(Harness):
    def test_needs_the_secret(self):
        self.assertEqual(self.call("/api/state", cookie=False)[0], 401)
        self.assertEqual(self.call("/api/state", headers={"Cookie": f"{agent_server.COOKIE}=wrong"}, cookie=False)[0], 401)
        self.assertEqual(self.call("/api/state")[0], 200)

    def test_rejects_other_hosts_and_origins(self):
        self.assertEqual(self.call("/api/state", headers={"Host": "evil.example"})[0], 403)         # DNS rebinding
        self.assertEqual(self.call("/api/conv", {}, headers={"Origin": "https://evil.example"})[0], 403)   # cross-site POST
        h = {"Host": f"127.0.0.1:{self.port}", "Cookie": self.cookie, "Content-Type": "text/plain"}
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/conv", data=b"{}", headers=h, method="POST")
        with self.assertRaises(urllib.error.HTTPError) as cm:
            urllib.request.urlopen(req)
        self.assertEqual(cm.exception.code, 415)

    def test_link_token_becomes_a_cookie(self):
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *a, **k):
                return None
        op = urllib.request.build_opener(NoRedirect)
        with self.assertRaises(urllib.error.HTTPError) as cm:
            op.open(urllib.request.Request(f"http://127.0.0.1:{self.port}/?t={self.hub.token}", headers={"Host": f"127.0.0.1:{self.port}"}))
        self.assertEqual(cm.exception.code, 302)
        self.assertIn("HttpOnly", cm.exception.headers["Set-Cookie"])
        code, html = self.call("/")
        self.assertEqual(code, 200)
        self.assertIn(b"Iris", html)
        self.assertEqual(self.call("/", cookie=False)[0], 401)


class AgentLoopTests(Harness):
    def types(self, c):
        return [e["type"] for e in c["events"]]

    def test_reads_run_by_themselves_then_it_answers(self):
        Path(self.tmp, "notes.txt").write_text("hello")
        FakeAI.script = [{"action": "run", "command": "ls", "why": "see what is here"}, {"action": "say", "message": "There is one file, **notes.txt**."}]
        cid = self.start_chat("what is here?")
        c = self.wait(cid, lambda c: "done" in self.types(c))
        t = self.types(c)
        self.assertNotIn("approval", t)
        res = [e for e in c["events"] if e["type"] == "result"][0]
        self.assertIn("notes.txt", res["output"])
        self.assertEqual(res["code"], 0)
        self.assertIn("notes.txt", [e for e in c["events"] if e["type"] == "say"][0]["text"])
        self.assertEqual(c["title"], "what is here?")

    def test_a_change_waits_for_approval_then_runs(self):
        FakeAI.script = [{"action": "run", "command": "echo made > made.txt", "why": "create it"}, {"action": "say", "message": "Created it."}]
        cid = self.start_chat("make a file")
        c = self.wait(cid, lambda c: "approval" in self.types(c))
        self.assertFalse(Path(self.tmp, "made.txt").exists())                     # nothing happened yet
        ap = [e for e in c["events"] if e["type"] == "approval"][0]
        self.call("/api/approve", {"conv": cid, "id": ap["id"], "allow": True})
        c = self.wait(cid, lambda c: "done" in self.types(c))
        self.assertEqual(Path(self.tmp, "made.txt").read_text().strip(), "made")

    def test_denied_command_never_runs_and_the_ai_is_told(self):
        FakeAI.script = [{"action": "run", "command": "touch nope.txt"}, {"action": "say", "message": "OK, I won't."}]
        cid = self.start_chat("touch a file")
        c = self.wait(cid, lambda c: "approval" in self.types(c))
        ap = [e for e in c["events"] if e["type"] == "approval"][0]
        self.call("/api/approve", {"conv": cid, "id": ap["id"], "allow": False})
        c = self.wait(cid, lambda c: "done" in self.types(c))
        self.assertFalse(Path(self.tmp, "nope.txt").exists())
        self.assertTrue([e for e in c["events"] if e["type"] == "result" and e.get("denied")])
        self.assertIn("denied", json.dumps(FakeAI.seen[-1]["messages"][-1]["content"]).lower())

    def test_dangerous_commands_always_ask_with_the_reason(self):
        FakeAI.script = [{"action": "run", "command": "git reset --hard"}, {"action": "say", "message": "ok"}]
        cid = self.start_chat("reset")
        c = self.wait(cid, lambda c: "approval" in self.types(c))
        ap = [e for e in c["events"] if e["type"] == "approval"][0]
        self.assertIn("uncommitted", ap["reason"])
        self.call("/api/stop", {"conv": cid})
        self.wait(cid, lambda c: "done" in self.types(c))

    def test_ask_mode_checks_even_reads(self):
        self.call("/api/mode", {"mode": "ask"})
        FakeAI.script = [{"action": "run", "command": "ls"}, {"action": "say", "message": "done"}]
        cid = self.start_chat("list")
        c = self.wait(cid, lambda c: "approval" in self.types(c))
        self.assertTrue(c["events"][-1]["type"] == "approval")
        self.call("/api/stop", {"conv": cid})
        self.wait(cid, lambda c: "done" in self.types(c))

    def test_working_folder_carries_over(self):
        os.mkdir(os.path.join(self.tmp, "sub"))
        FakeAI.script = [{"action": "run", "command": "cd sub"}, {"action": "run", "command": "pwd"}, {"action": "say", "message": "ok"}]
        cid = self.start_chat("go in")
        c = self.wait(cid, lambda c: "done" in self.types(c))
        outs = [e["output"] for e in c["events"] if e["type"] == "result"]
        self.assertTrue(outs[-1].strip().endswith("sub"), outs)

    def test_write_needs_a_yes_and_refuses_secret_files(self):
        FakeAI.script = [{"action": "write", "path": "hello.py", "content": "print('hi')\n", "why": "starter"}, {"action": "write", "path": ".env", "content": "X=1"}, {"action": "say", "message": "ok"}]
        cid = self.start_chat("write it")
        c = self.wait(cid, lambda c: "approval" in self.types(c))
        self.assertFalse(Path(self.tmp, "hello.py").exists())
        ap = [e for e in c["events"] if e["type"] == "approval"][0]
        self.call("/api/approve", {"conv": cid, "id": ap["id"], "allow": True})
        self.wait(cid, lambda c: "done" in self.types(c))
        self.assertEqual(Path(self.tmp, "hello.py").read_text(), "print('hi')\n")
        self.assertFalse(Path(self.tmp, ".env").exists())

    def test_secrets_are_redacted_before_they_reach_the_ai(self):
        Path(self.tmp, "config.txt").write_text("token = sk-ant-abcdefghijklmnop1234\n")
        FakeAI.script = [{"action": "run", "command": "cat config.txt"}, {"action": "say", "message": "ok"}]
        cid = self.start_chat("show config")
        self.wait(cid, lambda c: "done" in self.types(c))
        self.assertNotIn("sk-ant-abcdefghijklmnop1234", json.dumps(FakeAI.seen[-1]))

    def test_a_chatty_model_that_skips_json_still_works(self):
        FakeAI.script = ["Sure! Here is a plain answer."]
        cid = self.start_chat("hi")
        c = self.wait(cid, lambda c: "done" in self.types(c))
        self.assertIn("plain answer", [e for e in c["events"] if e["type"] == "say"][0]["text"])

    def test_hanging_command_is_stopped(self):
        agent.CMD_TIMEOUT = 1
        try:
            FakeAI.script = [{"action": "run", "command": "sleep 30"}, {"action": "say", "message": "it timed out"}]
            self.call("/api/mode", {"mode": "smart"})
            cid = self.start_chat("wait")
            c = self.wait(cid, lambda c: "approval" in self.types(c))
            ap = [e for e in c["events"] if e["type"] == "approval"][0]
            self.call("/api/approve", {"conv": cid, "id": ap["id"], "allow": True})
            c = self.wait(cid, lambda c: "done" in self.types(c), 20)
            self.assertEqual([e for e in c["events"] if e["type"] == "result"][0]["status"], "timeout")
        finally:
            agent.CMD_TIMEOUT = 90

    def test_conversations_are_listed_and_deletable(self):
        FakeAI.script = [{"action": "say", "message": "hi"}]
        cid = self.start_chat("hello there")
        self.wait(cid, lambda c: "done" in self.types(c))
        _, st = self.call("/api/state")
        self.assertEqual([c["id"] for c in st["conversations"]], [cid])
        self.call(f"/api/conv/{cid}", method="DELETE")
        self.assertEqual(self.call("/api/state")[1]["conversations"], [])


class PackagedTests(unittest.TestCase):
    def test_page_loads_from_inside_the_single_file_install(self):
        import subprocess, sys, tempfile
        from pathlib import Path
        from newton import installer
        with tempfile.TemporaryDirectory() as d:
            pyz = Path(d) / "newton"
            installer.build_pyz(Path(agent_server.__file__).resolve().parent, pyz)
            code = "import sys; sys.path.insert(0, %r); from newton import agent_server as a; b = a.read_page(); print(len(b), b'__NAME__' in b)" % str(pyz)
            r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=d, timeout=60)
            self.assertEqual(r.returncode, 0, r.stderr)
            size, has = r.stdout.split()
            self.assertGreater(int(size), 10000)
            self.assertEqual(has, "True")


if __name__ == "__main__":
    unittest.main()
