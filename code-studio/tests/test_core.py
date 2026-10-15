import os, sys, tempfile, threading, time, unittest, subprocess, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from nxcs import workspace, saferun, claude, patch, gitcc, intel, testintel, taskgraph, pipeline


class T(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="nxcs-تست-")   # non-ASCII path on purpose

    def w(self, name, text):
        p = os.path.join(self.d, name)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        workspace.write_text_atomic(p, text)
        return p

    def test_atomic_write_unicode_and_search_replace(self):
        p = self.w("سلام.txt", "hello سلام\nbye\n")
        self.assertEqual(workspace.read_text(p), "hello سلام\nbye\n")
        self.assertEqual(len(workspace.search(self.d, "bye")), 1)
        n, _ = workspace.replace_in_file(p, "bye", "ciao", dry_run=True)
        self.assertEqual(n, 1); self.assertIn("bye", workspace.read_text(p))
        workspace.replace_in_file(p, "bye", "ciao", dry_run=False)
        self.assertIn("ciao", workspace.read_text(p))

    def test_terminal_executes_real_command(self):
        r = saferun.run(["echo", "real-output"], restricted=False)
        self.assertEqual(r["returncode"], 0); self.assertIn("real-output", r["output"])

    def test_saferun_timeout_and_env_scrub(self):
        os.environ["NXCS_SECRET"] = "topsecret"
        r = saferun.run(["env"], restricted=True)
        self.assertNotIn("topsecret", r["output"]); self.assertIn("env-scrubbed", r["isolation"])
        t = time.time()
        r = saferun.run(["sleep", "30"], timeout=1, restricted=True)
        self.assertTrue(r["timed_out"]); self.assertLess(time.time() - t, 10)

    def test_saferun_cancel(self):
        j = saferun.Job(["sleep", "30"], timeout=60, restricted=False)
        threading.Timer(0.5, j.cancel).start()
        r = j.run(); self.assertTrue(r["cancelled"])

    def test_claude_disabled_nokey_mock_and_errors(self):
        with self.assertRaises(claude.ClaudeError) as c:
            claude.Client(enabled=False).ask("x")
        self.assertEqual(c.exception.kind, "disabled")
        os.environ.pop("ANTHROPIC_API_KEY", None)
        with self.assertRaises(claude.ClaudeError) as c:
            claude.Client(api_key=None).ask("x") if not os.path.exists(claude.KEY_FILE) else (_ for _ in ()).throw(claude.ClaudeError("no_key", ""))
        self.assertEqual(c.exception.kind, "no_key")
        mock = lambda body: {"content": [{"type": "text", "text": "hi"}], "usage": {"input_tokens": 1}}
        r = claude.Client(transport=mock).ask("q", context_files={"a.py": "x=1"})
        self.assertEqual(r["source"], "mock"); self.assertEqual(r["text"], "hi")

    def test_key_file_permissions(self):
        kf = os.path.join(self.d, "k"); claude.save_key("sk-test-123", kf)
        os.environ.pop("ANTHROPIC_API_KEY", None)
        self.assertEqual(oct(os.stat(kf).st_mode & 0o777), "0o600")
        self.assertEqual(claude.load_key(kf), "sk-test-123")
        os.chmod(kf, 0o644)
        with self.assertRaises(claude.ClaudeError): claude.load_key(kf)
        self.assertEqual(claude.redact("err sk-test-123", "sk-test-123"), "err ***")

    def test_patch_selective_and_conflict_protection(self):
        old = "a\nb\nc\nd\ne\n"; new = "A\nb\nc\nd\nE\n"
        self.assertEqual(len(patch.hunks(old, new)), 2)
        self.assertEqual(patch.apply_selected(old, new, {0}), "A\nb\nc\nd\ne\n")
        p = self.w("f.txt", old)
        workspace.write_text_atomic(p, old + "user edit\n")   # user edits during AI run
        r = patch.apply_to_file(p, old, new)
        self.assertFalse(r["applied"]); self.assertIn("user edit", workspace.read_text(p))
        workspace.write_text_atomic(p, old)
        self.assertTrue(patch.apply_to_file(p, old, new, accept=[1])["applied"])
        self.assertEqual(workspace.read_text(p), "a\nb\nc\nd\nE\n")

    def test_git_center(self):
        subprocess.run(["git", "init", "-q", self.d], check=True)
        for k, v in (("user.email", "t@t"), ("user.name", "t")):
            subprocess.run(["git", "-C", self.d, "config", k, v], check=True)
        p = self.w("a.txt", "1\n"); r = gitcc.Repo(self.d)
        self.assertEqual(r.status()["files"][0][0], "??")
        r.stage("a.txt"); sha = r.commit("first"); self.assertEqual(len(sha), 40)
        workspace.write_text_atomic(p, "2\n"); self.assertIn("+2", r.diff())
        with self.assertRaises(gitcc.GitError): r.discard("a.txt")
        r.discard("a.txt", confirm=True); self.assertEqual(workspace.read_text(p), "1\n")
        with self.assertRaises(gitcc.GitError): r.push(force=True)
        r.create_branch("feat"); self.assertIn("feat", r.branches())

    def test_intel_and_test_intelligence(self):
        self.w("pkg/m.py", "import os, json\nclass A:\n    pass\ndef f():\n    pass\nif __name__ == '__main__':\n    f()\n")
        self.w("tests/test_x.py", "import unittest\nclass X(unittest.TestCase):\n    def test_ok(self): self.assertTrue(True)\n    def test_bad(self): self.assertEqual(1, 2)\n")
        self.w("requirements.txt", "requests\n")
        a = intel.analyze(self.d)
        self.assertEqual(a["languages"]["Python"], 2); self.assertEqual(a["entry_points"], [os.path.join("pkg", "m.py")])
        s = intel.python_symbols(os.path.join(self.d, "pkg/m.py"))["symbols"]
        self.assertEqual([x[1] for x in s], ["A", "f"])
        self.assertEqual(intel.python_imports(os.path.join(self.d, "pkg/m.py")), {"os", "json"})
        self.assertIn("error", intel.python_symbols(self.w("bad.py", "def (:\n")) and intel.python_symbols(os.path.join(self.d, "bad.py")))
        self.assertEqual(testintel.discover(self.d), [os.path.join("tests", "test_x.py")])
        r = testintel.run_unittest(self.d, start="tests")
        self.assertEqual(r["ran"], 2); self.assertFalse(r["ok"]); self.assertEqual(len(r["failed"]), 1)

    def test_taskgraph_order_parallel_failure_cancel(self):
        order, lock = [], threading.Lock()
        def mk(n, delay=0.0, ok=True):
            def f():
                time.sleep(delay)
                with lock: order.append(n)
                return None if ok else 1
            return f
        g = taskgraph.Graph(); g.add("lint", mk("lint", .3)); g.add("fmt", mk("fmt", .3))
        g.add("build", mk("build"), ["lint", "fmt"]); g.add("pkg", mk("pkg"), ["build"])
        t = time.time(); st = g.run(); el = time.time() - t
        self.assertEqual(st, {"lint": "ok", "fmt": "ok", "build": "ok", "pkg": "ok"})
        self.assertLess(el, 0.55)   # lint+fmt ran concurrently
        self.assertLess(order.index("build"), order.index("pkg"))
        g2 = taskgraph.Graph(); g2.add("a", mk("a", 0, False)); g2.add("b", mk("b"), ["a"])
        self.assertEqual(g2.run(), {"a": "failed", "b": "skipped"})
        g3 = taskgraph.Graph(); g3.add("x", lambda: None, ["y"]); g3.add("y", lambda: None, ["x"])
        with self.assertRaises(taskgraph.CycleError): g3.validate()

    def test_pipeline_inspect_and_run(self):
        if pipeline.yaml is None: self.skipTest("PyYAML missing")
        wf = self.w("ci.yml", "name: t\non: push\njobs:\n  a:\n    runs-on: ubuntu-24.04\n    steps:\n      - uses: actions/checkout@v4\n      - run: echo hi-from-step\n      - run: exit 3\n      - run: echo never\n")
        info = pipeline.inspect(wf)
        self.assertTrue(any("actions/checkout" in u for u in info["unsupported"]))
        res = pipeline.run_job(info, "a", self.d)
        self.assertEqual([r["returncode"] for r in res], [0, 3])   # stops at failure


if __name__ == "__main__":
    unittest.main()
