import json, os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from ai.service.broker import Broker, Tool, DEFAULT_TOOLS, PRIVILEGED, DESTRUCTIVE


def fake(argv):
    return 0, "ran:" + " ".join(argv)


class T(unittest.TestCase):
    def mk(self, **kw):
        tools = dict(DEFAULT_TOOLS)
        tools["install_pkg"] = Tool("install_pkg", ["apt-get", "install", "-y"], PRIVILEGED, lambda a: a.isalnum())
        tools["wipe"] = Tool("wipe", ["echo", "wipe"], DESTRUCTIVE)
        self.log = os.path.join(tempfile.mkdtemp(), "audit.jsonl")
        return Broker(tools, self.log, fake)

    def test_safe_runs(self):
        self.assertEqual(self.mk().request("kernel")[0], "done")

    def test_unknown_tool_denied(self):
        self.assertEqual(self.mk().request("rm_rf")[0], "denied")

    def test_shell_injection_arg_denied(self):
        self.assertEqual(self.mk().request("install_pkg", "vim; rm -rf /", approved=True)[0], "denied")

    def test_privileged_needs_approval_then_runs(self):
        b = self.mk()
        self.assertEqual(b.request("install_pkg", "vim")[0], "needs_approval")
        self.assertEqual(b.request("install_pkg", "vim", approved=True)[0], "done")

    def test_untrusted_source_never_runs_risky(self):
        self.assertEqual(self.mk().request("wipe", approved=True, untrusted_source=True)[0], "denied")

    def test_invalid_tool_type(self):
        self.assertEqual(self.mk().request(["a"])[0], "denied")

    def test_audit_written(self):
        b = self.mk(); b.request("kernel"); b.request("nope")
        lines = [json.loads(l) for l in open(self.log)]
        self.assertEqual([l["status"] for l in lines], ["done", "denied"])

    def test_runner_failure(self):
        b = self.mk(); b.runner = lambda a: (_ for _ in ()).throw(OSError("boom"))
        self.assertEqual(b.request("kernel")[0], "failed")


if __name__ == "__main__":
    unittest.main()
