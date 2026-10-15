import os, sys, tempfile, time, unittest
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
try:
    from nxcs.gui import Studio, Palette, W, BINDING
    HAVE = True
except ImportError:
    HAVE = False


@unittest.skipUnless(HAVE, "no Qt binding installed")
class G(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = W.QApplication.instance() or W.QApplication([])

    def pump(self, cond, t=8):
        end = time.time() + t
        while time.time() < end and not cond():
            self.app.processEvents(); time.sleep(0.02)
        return cond()

    def test_edit_save_terminal_ai_palette(self):
        d = tempfile.mkdtemp(prefix="nxcs-گرافیک-")
        f = os.path.join(d, "a.py"); open(f, "w", encoding="utf-8").write("print(1)\n")
        s = Studio(d)
        ed = s.open_file(f); self.assertIn("print(1)", ed.toPlainText())
        ed.setPlainText("print(2)\n"); self.assertTrue(s.save_current())
        self.assertEqual(open(f, encoding="utf-8").read(), "print(2)\n")
        s.term_in.setText("python3 a.py" if os.name != "nt" else "python a.py"); s.run_terminal()
        self.assertTrue(self.pump(lambda: "[exit 0]" in s.term_out.toPlainText()))
        self.assertIn("2", s.term_out.toPlainText())
        s.ai_transport = lambda b: {"content": [{"type": "text", "text": "mock-answer"}]}
        s.ai_in.setText("explain"); s.ask_ai()
        self.assertTrue(self.pump(lambda: "mock-answer" in s.ai_out.toPlainText()))
        self.assertIn("[mock]", s.ai_out.toPlainText())
        s.ai_enabled = False; s.ask_ai(); self.assertIn("disabled", s.ai_out.toPlainText())
        p = Palette(list(s.commands)); p.box.setText("git"); self.assertEqual(p.list.count(), 1)
        print("binding:", BINDING)


if __name__ == "__main__":
    unittest.main()
