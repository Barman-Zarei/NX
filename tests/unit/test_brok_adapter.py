import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from ai.service.brok_adapter import BrokAdapter

BROK = os.environ.get("NX_BROK_DIR", "/home/claude/Brok")


class T(unittest.TestCase):
    def test_disabled(self):
        self.assertEqual(BrokAdapter(enabled=False).call("ask", "hi")[0], "disabled")

    @unittest.skipIf(os.geteuid() == 0, "adapter refuses root by design; run as a normal user")
    def test_missing_brok(self):
        self.assertEqual(BrokAdapter(brok_dir="/nonexistent").call("ask", "hi")[0], "unavailable")

    @unittest.skipIf(os.geteuid() == 0, "adapter refuses root by design")
    def test_untrusted_cannot_use_agent_mode(self):
        a = BrokAdapter(brok_dir=BROK)
        self.assertEqual(a.call("code", "rm -rf /", untrusted=True)[0], "denied")

    @unittest.skipIf(os.geteuid() == 0, "adapter refuses root by design")
    def test_bad_input(self):
        a = BrokAdapter(brok_dir=BROK)
        self.assertEqual(a.call("shell", "x")[0], "denied")
        self.assertEqual(a.call("ask", "")[0], "denied")

    def test_root_refused(self):
        if os.geteuid() == 0:
            self.assertEqual(BrokAdapter(brok_dir=BROK).call("doctor")[0], "denied")

    @unittest.skipIf(os.geteuid() == 0 or not os.path.isdir(BROK), "needs real Brok and non-root")
    def test_real_brok_doctor_offline(self):
        a = BrokAdapter(brok_dir=BROK, home="/tmp/nx-ai-test-home")
        st = a.provider_status()
        self.assertIn("ollama", st)          # real Brok output parsed
        self.assertFalse(any(st.values()))   # sandbox: no providers reachable

    @unittest.skipIf(os.geteuid() == 0 or not os.path.isdir(BROK), "needs real Brok and non-root")
    def test_real_brok_ask_offline_is_status_not_crash(self):
        a = BrokAdapter(brok_dir=BROK, home="/tmp/nx-ai-test-home", timeout=90)
        st, _ = a.call("ask", "hello")
        self.assertIn(st, ("provider_error", "failed", "timeout"))



class CliT(unittest.TestCase):
    def test_cli_disabled(self):
        import subprocess
        env = dict(os.environ, NX_AI_DISABLED="1")
        p = subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "..", "..", "ai", "service", "nx_ai_cli.py"), "ask", "hi"],
                           env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self.assertEqual(p.returncode, 1); self.assertIn(b"disabled", p.stdout)


if __name__ == "__main__":
    unittest.main()
