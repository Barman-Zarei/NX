"""Runs the PySide2 media-tool dialog logic headless (QT_QPA_PLATFORM=offscreen). Skipped if PySide2 is absent."""
import hashlib, os, sys, tempfile, unittest
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "windows", "media-tool"))
try:
    from PySide2.QtWidgets import QApplication
    import gui
except ImportError:
    gui = None


@unittest.skipIf(gui is None, "PySide2 not installed")
class T(unittest.TestCase):
    def test_verify_window(self):
        app = QApplication.instance() or QApplication([])
        d = tempfile.mkdtemp(); iso = os.path.join(d, "a.iso")
        open(iso, "wb").write(b"hello")
        open(iso + ".sha256", "w").write(hashlib.sha256(b"hello").hexdigest() + "  a.iso\n")
        w = gui.VerifyWindow()
        w.set_files(iso, iso + ".sha256"); w.run_verify()
        self.assertEqual(w.result_label.text()[:2], "OK")
        open(iso + ".sha256", "w").write("0" * 64 + "  a.iso\n")
        w.set_files(iso, iso + ".sha256"); w.run_verify()
        self.assertTrue(w.result_label.text().startswith("MISMATCH"))


if __name__ == "__main__":
    unittest.main()
