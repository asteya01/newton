"""A tiny fake Anthropic Messages API used by the test-suite (no network, no key needed)."""
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

ANSWERS = {
    "port 3000": {"command": "lsof -ti tcp:3000 | xargs kill", "alternatives": ["kill -9 $(lsof -ti :3000)", "npx kill-port 3000"],
                  "explanation": "Finds the process listening on port 3000 and stops it.", "danger": None},
    "100mb": {"command": "find ~ -type f -size +100M", "alternatives": ["du -ah ~ | sort -rh | head -20"],
              "explanation": "Lists files in your home folder larger than 100 MB.", "danger": None},
    "delete": {"command": "rm -rf node_modules", "alternatives": [], "explanation": "Deletes the node_modules folder.", "danger": "Permanently deletes files"},
    "ping": {"command": "ok", "alternatives": [], "explanation": "", "danger": None},
}

PLANS = {
    "static site": {
        "goal": "Static site", "summary": "A folder with an index page, built step by step.", "assumptions": ["bash is available"],
        "inputs": [{"name": "SITE_NAME", "prompt": "Site name?", "default": "demo"}],
        "steps": [
            {"title": "Create project folder", "why": "Makes a home for the site.", "command": "mkdir -p \"$SITE_NAME\" && cd \"$SITE_NAME\"", "verify": "", "risk": "safe"},
            {"title": "Write the index page", "why": "A minimal page.", "command": "echo '<h1>hi</h1>' > index.html && export BUILT=yes", "verify": "test -f index.html", "risk": "safe"},
            {"title": "Record where we are", "why": "Proves cwd and env carry over.", "command": "pwd > where.txt && echo $BUILT > built.txt", "risk": "safe"}],
        "after": "Open index.html in a browser."},
    "failing": {
        "goal": "Failing plan", "summary": "Second step fails until fixed.", "assumptions": [], "inputs": [],
        "steps": [
            {"title": "Say hello", "why": "Warm up.", "command": "echo hello > hello.txt", "risk": "safe"},
            {"title": "Read the config", "why": "Needs missing.txt.", "command": "cat missing.txt > got.txt", "risk": "safe"},
            {"title": "Finish", "why": "Last step.", "command": "echo ok > ok.txt", "risk": "safe"}]},
    "danger": {
        "goal": "Danger plan", "summary": "Has a destructive step.", "assumptions": [], "inputs": [],
        "steps": [
            {"title": "Make a build dir", "command": "mkdir -p build && touch build/x", "risk": "safe"},
            {"title": "Delete build dir", "command": "rm -rf build", "risk": "danger"},
            {"title": "Mark done", "command": "echo done > done.txt", "risk": "safe"}]},
    "manual": {
        "goal": "Manual plan", "summary": "Has a manual step.", "assumptions": [], "inputs": [],
        "steps": [
            {"title": "Get an API key", "manual": "Create a key in your dashboard and note it down.", "command": "", "risk": "safe"},
            {"title": "Write marker", "command": "echo ok > marker.txt", "risk": "safe"}]},
    "scaffold": {
        "goal": "Scaffold", "summary": "Makes a project with an undoable history.", "assumptions": [],
        "requires": ["git", "definitely-not-installed-xyz"],
        "inputs": [{"name": "PROJ", "prompt": "Project folder?", "default": "proj"}],
        "steps": [
            {"title": "Create project", "command": "mkdir -p \"$PROJ\" && cd \"$PROJ\"", "undo": "rm -rf \"$PROJ\"", "risk": "safe"},
            {"title": "Write a file", "command": "echo hi > a.txt", "undo": "rm -f a.txt", "risk": "safe"},
            {"title": "Add b file", "command": "sleep 1.1 && echo x > b.txt", "risk": "safe"}],
        "after": "cd into it."},
    "reversible": {
        "goal": "Undo danger", "summary": "Its undo is destructive.", "assumptions": [], "inputs": [],
        "steps": [{"title": "Make file", "command": "echo hi > f.txt", "undo": "git push --force origin nothing", "risk": "safe"}]},
    "stringy": {"goal": "Stringy", "summary": "Steps are bare strings.", "steps": ["echo one > one.txt", "echo two > two.txt"]},
    "impossible": {"goal": "", "summary": "That can't be done from a terminal.", "steps": []},
}

CALLS = []
STREAM_TEXT = "Try this:\n\n```bash\nls -la\n```\n\nThat lists everything, including **hidden** files.\n"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, ans):
        data = json.dumps({"content": [{"type": "text", "text": json.dumps(ans)}]}).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _raw(self, text):
        data = json.dumps({"content": [{"type": "text", "text": text}]}).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _stream(self, text):
        self.send_response(200)
        self.send_header("content-type", "text/event-stream")
        self.end_headers()
        w = self.wfile.write
        w(b'event: message_start\ndata: {"type":"message_start"}\n\n')
        for i in range(0, len(text), 9):
            ev = {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": text[i:i + 9]}}
            w(("event: content_block_delta\ndata: " + json.dumps(ev) + "\n\n").encode())
        w(b'event: message_stop\ndata: {"type":"message_stop"}\n\n')

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["content-length"])))
        CALLS.append(body)
        if self.headers.get("x-api-key") != "test-key":
            self.send_response(401); self.end_headers()
            self.wfile.write(b'{"error":{"message":"invalid x-api-key"}}'); return
        system = body.get("system", "")
        user = body["messages"][-1]["content"].lower()
        if body.get("stream"):
            return self._stream(STREAM_TEXT)
        if "PLAN MODE" in system:
            first = body["messages"][0]["content"].lower()
            goal = first.split("goal:")[-1]
            if "flaky" in goal and len(body["messages"]) == 1:        # first reply is junk; the strict retry gets a real plan
                return self._raw("Sure! Here's the plan: {\"goal\": \"Flaky\", \"steps\": [ {oops")
            if "escapes" in goal:                                      # valid plan, but with the invalid JSON escape \\; inside
                return self._raw('{"goal": "Escapes", "summary": "s", "steps": [{"title": "List", "command": "find . -name x -exec ls {} \\; | sort", "risk": "safe"},]}')
            ans = next((v for k, v in PLANS.items() if k in goal), PLANS["static site"])
            if "flaky" in goal:
                ans = {**PLANS["failing"], "goal": "Flaky plan"}
            return self._json(ans)
        if "REVISE MODE" in system:
            return self._json({"steps": [{"title": "Revised step", "why": "As requested.", "command": "echo revised > revised.txt", "risk": "safe"}]})
        if "DIAGNOSE MODE" in system:
            if "missing.txt" in user:
                return self._json({"diagnosis": "missing.txt doesn't exist in this folder.", "confidence": "high", "then": "retry",
                                   "fix": {"title": "Create the missing file", "command": "echo data > missing.txt", "risk": "safe"}})
            return self._json({"diagnosis": "Can't tell from the output; check the command name.", "fix": None, "then": "retry"})
        if "COMMIT MODE" in system:
            return self._json({"subject": "Add greeting script.", "body": "Gives the demo something to run."})
        if "command:" in user and "parts" in system:
            ans = {"summary": "Extracts a gzipped tarball.", "parts": [{"part": "-x", "meaning": "extract"}, {"part": "-z", "meaning": "gunzip"}], "danger": None}
        else:
            ans = next((v for k, v in ANSWERS.items() if k in user.split("request:")[-1]), ANSWERS["ping"])
        self._json(ans)


def start(port=0):
    srv = HTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


if __name__ == "__main__":
    s = start(int(sys.argv[1]) if len(sys.argv) > 1 else 8765)
    print(f"mock API on :{s.server_port}", flush=True)
    threading.Event().wait()
