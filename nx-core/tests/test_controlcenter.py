import json, os, sys, tempfile, time, unittest
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from nxsys import actions as ACT, controlcenter as cc

SKIP_EXEC = {17, 18, 23, 41, 50}     # network/slow/spawn: covered by their own tests or deliberately not auto-run


class H(unittest.TestCase):
    def test_every_feature_has_actions(self):
        self.assertEqual(sorted(ACT.R), list(range(1, 51)))
        self.assertEqual(sorted(cc.NAMES), list(range(1, 51)))
        for n, acts in ACT.R.items(): self.assertTrue(acts, n)

    def test_dangerous_actions_refuse_without_confirmation(self):
        d = [a for acts in ACT.R.values() for a in acts if a.danger]
        self.assertGreaterEqual(len(d), 12)
        for a in d:
            with self.assertRaises(PermissionError, msg=a.label):
                ACT.execute(a, {})

    def test_safe_actions_execute_with_defaults(self):
        t = tempfile.mkdtemp(prefix="nx-ح-"); n_ok = 0
        over = {"root": t, "path": t, "src": t, "dst": os.path.join(t, "d"), "dest": os.path.join(t, "dest"), "base": t,
                "iso_dir": t, "grub_cfg": os.path.join(t, "x"), "db": os.path.join(t, "c.json"), "hardware": "HW", "text": "t",
                "title": "T", "body": "B", "name": "n", "to": "a@b.c", "user": "u", "site": "s", "password": "p", "passphrase": "pw",
                "dest_": t, "apps_dir": t, "sink": "none", "device": "/dev/none", "mime": "text/plain", "zpath": os.path.join(t, "a.zip"),
                "files": "", "archive": os.path.join(t, "b.tgz"), "packages": "", "root_dev": "/dev/x", "target_dir": t}
        for n, acts in ACT.R.items():
            if n in SKIP_EXEC: continue
            for a in acts:
                if a.danger: continue
                if a.label.startswith(("Create virtualenv", "Download packages", "Verify pack", "Create ZIP", "Extract", "Inspect a .deb",
                                       "Set volume", "Create web app", "Build e-mail", "Take screenshot", "Create backup", "Set Easy", "Preview migration")):
                    continue                      # need real inputs; exercised in test_features_all / below
                vals = {k: over[k] for k, *_ in a.params if k in over}
                try:
                    ACT.execute(a, vals); n_ok += 1
                except Exception as e:             # a feature may legitimately error on this host; it must not crash the process
                    self.assertNotIsInstance(e, (NameError, TypeError, AttributeError), "%d %s: %r" % (n, a.label, e))
        self.assertGreater(n_ok, 30)

    def test_vault_roundtrip_through_actions(self):
        t = tempfile.mkdtemp(); p = os.path.join(t, "v.bin")
        put = [a for a in ACT.R[38] if a.label.startswith("Save")][0]; get = [a for a in ACT.R[38] if a.label.startswith("Open")][0]
        ACT.execute(put, {"path": p, "passphrase": "m", "site": "s", "user": "u", "password": "p@ss"})
        self.assertEqual(ACT.execute(get, {"path": p, "passphrase": "m", "site": "s", "reveal": False})["password"], "••••••••")
        self.assertEqual(ACT.execute(get, {"path": p, "passphrase": "m", "site": "s", "reveal": True})["password"], "p@ss")
        self.assertIn("error", ACT.execute(get, {"path": p, "passphrase": "bad", "site": "s", "reveal": True}))

    def test_backup_restore_through_actions(self):
        t = tempfile.mkdtemp(); s = os.path.join(t, "src"); os.makedirs(s); open(os.path.join(s, "f"), "w").write("x")
        a = {x.label.split()[0]: x for x in ACT.R[13]}
        r = ACT.execute(a["Create"], {"src": s, "archive": os.path.join(t, "b.tgz")})
        o = os.path.join(t, "o"); os.makedirs(o)
        ACT.execute(a["Restore"], {"archive_path": r["archive"], "dest": o, "sha256": r["sha256"]}, confirmed=True)
        self.assertTrue(os.path.exists(os.path.join(o, "src", "f")))

    def test_gui_pages_for_all_50_and_actions(self):
        try:
            from nxsys.qtshim import QtWidgets
        except ImportError:
            self.skipTest("no Qt binding")
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        import nxcc
        w = nxcc.Center(auto_confirm=True); self.assertEqual(w.list.count(), 50)
        for n in range(1, 51):
            p = w.page(n); self.assertEqual(len(p.boxes), len(ACT.R[n]), n)
        # run a harmless action through the real button path
        w.search.setText("firewall"); self.assertEqual(w.list.count(), 1); w.list.setCurrentRow(0)
        act, fields, conf, btn = w.page(20).boxes[0]; btn.click()
        end = time.time() + 10
        while "ufw default deny incoming" not in w.out.toPlainText() and time.time() < end:
            app.processEvents(); time.sleep(0.05)
        self.assertIn("ufw default deny incoming", w.out.toPlainText())
        # dangerous action: blocked until checkbox ticked, then asks
        act, fields, conf, btn = w.page(20).boxes[1]; w.out.clear(); btn.click(); app.processEvents()
        self.assertIn("tick the confirmation box", w.out.toPlainText())
        w2 = nxcc.Center(auto_confirm=False); act, fields, conf, btn = w2.page(20).boxes[1]; conf.setChecked(True); btn.click(); app.processEvents()
        self.assertIn("Cancelled", w2.out.toPlainText())


if __name__ == "__main__":
    unittest.main()
