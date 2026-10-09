"""GTK window logic test. Needs python3-gi and a display (CI: xvfb-run). Skipped otherwise."""
import importlib.util, os, sys, unittest
try:
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk
    OK = Gtk.init_check()[0]
except Exception:  # noqa: BLE001
    OK = False
HERE = os.path.join(os.path.dirname(__file__), "..", "..", "software-center")


@unittest.skipUnless(OK, "no GTK or no display")
class T(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location("nxgui", os.path.join(HERE, "nx-software-gui.py"))
        self.m = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.m)
        self.w = self.m.SoftwareWindow()

    def test_populate_and_select(self):
        self.m.nxsoft.info = lambda n: {"Package": n, "Version": "1", "Architecture": "amd64", "Description": "d"}
        self.w.populate([{"name": "vim", "summary": "editor"}])
        self.assertEqual(len(self.w.store), 1)
        self.w.select_name("vim"); self.assertIn("vim 1", self.w.details.get_text())

    def test_cancel_does_not_apply(self):
        called = []
        self.m.nxsoft.apply = lambda *a, **k: called.append(a) or ("done", "")
        self.w.selected = "vim"
        self.assertEqual(self.w.request("install", confirm=lambda c: False), "cancelled"); self.assertEqual(called, [])

    def test_confirm_applies_approved(self):
        seen = []
        self.m.nxsoft.apply = lambda a, n, approved=False, runner=None: seen.append((a, n, approved)) or ("done", "ok")
        self.w.selected = "vim"
        self.assertEqual(self.w.request("install", confirm=lambda c: "apt-get install" in c), "done")
        self.assertEqual(seen, [("install", "vim", True)])

    def test_invalid_name_denied(self):
        self.w.selected = "vim; rm -rf /"
        self.assertEqual(self.w.request("install", confirm=lambda c: True), "denied")


if __name__ == "__main__":
    unittest.main()
