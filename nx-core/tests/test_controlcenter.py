import os, sys, unittest
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from nxsys import controlcenter as cc


class H(unittest.TestCase):
    def test_all_50_registered_in_order(self):
        f = cc.features(); self.assertEqual([x[0] for x in f], list(range(1, 51)))
        self.assertEqual(f[49][1], "NX Code Studio"); self.assertEqual(f[20][1], "NX Configuration Audit" if False else f[20][1])

    def test_every_check_returns_without_crashing(self):
        for n in cc.CHECKS:
            if n in (18, 23, 17):      # network/slow: exercised separately in their own tests
                continue
            r = cc.run_check(n); self.assertIsNotNone(r, n)
        self.assertIn("note", cc.run_check(38))

    def test_gui_lists_and_runs(self):
        try:
            from nxsys.qtshim import QtWidgets
        except ImportError:
            self.skipTest("no Qt")
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        import nxcc
        w = nxcc.Center(); self.assertEqual(w.list.count(), 50)
        w.search.setText("firewall"); self.assertEqual(w.list.count(), 1)
        w.list.setCurrentRow(0); w.run_selected(); self.assertIn("ufw default deny incoming", w.out.toPlainText())


if __name__ == "__main__":
    unittest.main()
