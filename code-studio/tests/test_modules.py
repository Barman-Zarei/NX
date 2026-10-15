import os, sys, tempfile, unittest, subprocess, json, urllib.request
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from nxcs import debugger, profiler, depguard, forge, profiles, logexp, preview, releasepilot, review, agent, claude, workspace, testintel


class M(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="nxcs-ماژول-")

    def w(self, n, t):
        p = os.path.join(self.d, n); os.makedirs(os.path.dirname(p), exist_ok=True); workspace.write_text_atomic(p, t); return p

    def test_debugger_breakpoint_step_vars_continue(self):
        p = self.w("s.py", "x = 1\ny = x + 1\nz = y * 10\nprint(z)\n")
        d = debugger.Debugger()
        self.assertEqual(d.start(p, breakpoints=[3]), "paused")
        self.assertEqual(d.location()[1], 3); self.assertEqual(d.variables()["y"], "2")
        self.assertEqual(d.evaluate("x + y"), "3")
        d.command("next"); self.assertEqual(d.location()[1], 4); self.assertEqual(d.variables()["z"], "20")
        self.assertEqual(d.command("continue"), "finished"); self.assertIsNone(d.error)

    def test_debugger_function_stack_and_exception(self):
        p = self.w("f.py", "def f(a):\n    b = a * 2\n    return b\nf(21)\nraise ValueError('boom')\n")
        d = debugger.Debugger(); d.start(p, breakpoints=[2])
        self.assertEqual(d.stack()[0][0], "f"); self.assertEqual(d.variables()["a"], "21")
        d.command("continue")
        while not d.finished and d.state == "paused":
            d.command("continue")
        self.assertIn("ValueError", d.error or d.exception or "")

    def test_profiler(self):
        p = self.w("p.py", "def work():\n    return sum(i*i for i in range(50000))\nwork()\n")
        r = profiler.profile_script(p); self.assertIsNone(r["error"]); self.assertGreater(r["peak_kib"], 0)
        self.assertTrue(any("work" in x["function"] for x in r["top"]))

    def test_forge_templates_actually_work(self):
        dest = os.path.join(self.d, "proj"); forge.create("python", dest, "mylib")
        r = testintel.run_unittest(dest, start="tests"); self.assertTrue(r["ok"], r["output"])
        with self.assertRaises(FileExistsError): forge.create("python", dest, "mylib")
        dest2 = os.path.join(self.d, "c"); forge.create("c", dest2, "hello")
        if subprocess.run(["which", "make"], capture_output=True).returncode == 0 and subprocess.run(["which", "cc"], capture_output=True).returncode == 0:
            self.assertEqual(subprocess.run(["make", "-C", dest2], capture_output=True).returncode, 0)
            self.assertEqual(subprocess.run([os.path.join(dest2, "hello")], capture_output=True, text=True).stdout.strip(), "hello")
        dest3 = os.path.join(self.d, "cli"); forge.create("cli", dest3, "tool")
        self.assertTrue(testintel.run_unittest(dest3, start="tests")["ok"])

    def test_profiles_change_real_settings_and_reject_secrets(self):
        sp = os.path.join(self.d, "s", "settings.json")
        r = profiles.apply("low-resource", sp); self.assertEqual(json.load(open(sp))["terminal_limit_mb"], 256)
        self.assertEqual(r["profile"], "low-resource")
        with self.assertRaises(ValueError): profiles.validate_shared_config({"api_key": "x"})

    def test_logexp(self):
        t = "INFO a\nERROR b secret=abc123\nDEBUG c\nWARNING d /home/bob/x\n"
        self.assertEqual([n for n, _ in logexp.filter_lines(t, "WARNING")], [2, 4])
        s = logexp.sanitize(t); self.assertNotIn("abc123", s); self.assertNotIn("bob", s)

    def test_preview_localhost_only(self):
        self.w("index.html", "<h1>hi</h1>")
        pv = preview.Preview(self.d); url = pv.start()
        try:
            self.assertTrue(pv.port_open()); self.assertIn(b"<h1>hi</h1>", urllib.request.urlopen(url).read())
            self.assertEqual(pv.httpd.server_address[0], "127.0.0.1"); self.assertTrue(pv.log)
        finally:
            pv.stop()

    def test_release_pilot(self):
        self.assertEqual(releasepilot.bump("1.2.3", "minor"), "1.3.0")
        subprocess.run(["git", "init", "-q", self.d], check=True)
        for k, v in (("user.email", "t@t"), ("user.name", "t")): subprocess.run(["git", "-C", self.d, "config", k, v], check=True)
        self.w("a", "1"); subprocess.run(["git", "-C", self.d, "add", "."], check=True); subprocess.run(["git", "-C", self.d, "commit", "-qm", "init"], check=True)
        self.assertIn("init", releasepilot.changelog(self.d))
        cl = dict(releasepilot.checklist(self.d, True, "1.0.0")); self.assertTrue(cl["working tree clean"])

    def test_review_confirmed_findings(self):
        p = self.w("r.py", "import subprocess\ntry:\n    pass\nexcept:\n    pass\nsubprocess.run('ls', shell=True)\nAPI_KEY = 'abcdef123456'\neval('1')\n")
        msgs = [(f["line"], f["msg"]) for f in review.review_python(p)]
        self.assertEqual([l for l, _ in msgs], [4, 6, 7, 8])
        mock = lambda b: {"content": [{"type": "text", "text": "maybe"}]}
        self.assertEqual(review.ai_review(claude.Client(transport=mock), p)["kind"], "speculative")

    def test_agent_requires_approval_and_protects_user_edits(self):
        proj = os.path.join(self.d, "p"); forge.create("python", proj, "lib")
        target = os.path.join(proj, "lib", "__init__.py")
        mock = lambda b: {"content": [{"type": "text", "text": '__version__ = "0.2.0"\n'}]}
        a = agent.Agent(claude.Client(transport=mock), proj, approve=lambda d: False)
        r = a.run("bump", "lib/__init__.py"); self.assertEqual(r["status"], "rejected")
        self.assertIn("0.1.0", workspace.read_text(target))            # nothing written without approval
        a = agent.Agent(claude.Client(transport=mock), proj, approve=lambda d: True)
        r = a.run("bump", "lib/__init__.py")
        self.assertEqual(r["status"], "applied"); self.assertEqual(r["source"], "mock")
        self.assertFalse(r["tests"]["ok"])                              # test expects 0.1.0 -> reported honestly
        def approve_and_edit(d):
            workspace.write_text_atomic(target, "# user edit meanwhile\n"); return True
        a = agent.Agent(claude.Client(transport=lambda b: {"content": [{"type": "text", "text": '__version__ = "0.3.0"\n'}]}), proj, approve_and_edit)
        r = a.run("bump", "lib/__init__.py"); self.assertEqual(r["status"], "conflict")
        self.assertIn("user edit", workspace.read_text(target))

    def test_depguard_preview(self):
        self.assertIn("major", depguard.preview_upgrade("x", "1.0", "2.0")["risk"])


if __name__ == "__main__":
    unittest.main()
