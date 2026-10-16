import os, sys, tempfile, time, unittest
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
try:
    from nxcs.qt import QtWidgets, BINDING
    from nxcs.gui import Studio
except ImportError as e:
    QtWidgets = None


@unittest.skipIf(QtWidgets is None, "no Qt binding installed")
class G(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def pump(self, ev, t=15):
        end = time.time() + t
        while not ev.is_set() and time.time() < end:
            self.app.processEvents(); time.sleep(0.02)
        self.app.processEvents()
        self.assertTrue(ev.is_set())

    def test_open_edit_save_terminal_ai(self):
        d = tempfile.mkdtemp(prefix="nxcs-گ-")
        p = os.path.join(d, "a.py"); open(p, "w").write("print(1)\n")
        mock = lambda body: {"content": [{"type": "text", "text": "mock-reply"}]}
        w = Studio(d, ai_transport=mock)
        ed = w.open_file(p); self.assertEqual(ed.toPlainText(), "print(1)\n")
        ed.setPlainText("print(2)\n"); self.assertTrue(w.save_current())
        self.assertEqual(open(p).read(), "print(2)\n")
        self.pump(w.run_terminal_cmd("python3 a.py"))
        self.assertIn("2", w.term_out.toPlainText().splitlines()[-1])
        self.pump(w._ai_done if w.ask_ai("explain") is not None and False else w.ask_ai("explain"))
        self.assertIn("[source: mock]", w.ai_out.toPlainText())   # mock is labeled, never shown as real Claude
        w.toggle_ai(); self.pump(w.ask_ai("x"))
        self.assertIn("[error: disabled]", w.ai_out.toPlainText())
        self.assertIn("Command Palette", w.actions_map); self.assertTrue(w.git_view.toPlainText())


if __name__ == "__main__":
    unittest.main()
