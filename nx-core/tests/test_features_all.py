import io, json, os, sys, tarfile, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from nxsys import sysfeatures_a as A, sysfeatures_b as B, sysfeatures_c as C


class F(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="nx-ف-")

    def mk(self, name, text="x"):
        p = os.path.join(self.d, name); os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "w").write(text); return p

    # 1,21
    def test_selfheal_requires_confirm_and_allowlist(self):
        with self.assertRaises(PermissionError): A.repair({"repair": ["dpkg", "--configure", "-a"]})
        r = A.repair({"repair": ["rm", "-rf", "/"]}, confirm=True)
        self.assertFalse(r["ran"])
        self.assertIsInstance(A.diagnose(), list)

    def test_recovery_validator_reports_missing(self):
        r = A.validate_recovery(grub_cfg=os.path.join(self.d, "nope"), iso_dir=self.d)
        self.assertFalse(r["ready"]); self.assertIn("does not guarantee", r["note"])
        self.assertEqual(len(A.rescue_plan("/dev/sdX")), 5)

    # 3
    def test_offline_pack_manifest_verify(self):
        self.mk("pk/a.deb", "aaa")
        m = A.manifest(os.path.join(self.d, "pk")); self.assertTrue(A.verify_pack(os.path.join(self.d, "pk"), m)["ok"])
        open(os.path.join(self.d, "pk/a.deb"), "w").write("tampered")
        self.assertEqual(A.verify_pack(os.path.join(self.d, "pk"), m)["bad"], ["a.deb"])

    # 5
    def test_easy_mode_keeps_settings(self):
        p = os.path.join(self.d, "s.json"); json.dump({"theme": "dark"}, open(p, "w"))
        self.assertEqual(A.set_mode(p, "easy"), {"theme": "dark", "mode": "easy"})
        self.assertEqual(A.visible_features("easy", ["a", "b"], ["b"]), ["a"])
        self.assertEqual(A.visible_features("advanced", ["a", "b"], ["b"]), ["a", "b"])
        with self.assertRaises(ValueError): A.set_mode(p, "x")

    # 6
    def test_inspect_deb(self):
        r = A.inspect_deb("/nonexistent.deb")
        self.assertTrue("available" in r)

    # 7
    def test_safe_update_says_no_rollback(self):
        r = A.preview_updates()
        if r.get("available"): self.assertIn("NOT provided", r["rollback"])

    # 8
    def test_permission_map(self):
        p = self.mk("w.txt"); os.chmod(p, 0o666)
        self.assertIn(p, A.permission_map(self.d)["world_writable"])
        with self.assertRaises(PermissionError): A.set_mode_path(p, 0o600)
        A.set_mode_path(p, 0o600, confirm=True); self.assertEqual(os.stat(p).st_mode & 0o777, 0o600)

    # 9
    def test_devkit(self):
        s = A.devkit_status(); self.assertIsNotNone(s["python3"]["path"])
        v = os.path.join(self.d, "venv"); self.assertTrue(A.create_venv(v)["ok"]); self.assertTrue(os.path.isdir(v))

    # 11
    def test_migration_preserves_originals(self):
        s = os.path.join(self.d, "src"); self.mk("src/a.txt", "1"); self.mk("src/sub/b.txt", "2")
        dst = os.path.join(self.d, "dst")
        pv = A.migrate_preview(s, dst); self.assertEqual(len(pv["copy"]), 2); self.assertFalse(os.path.exists(dst))
        with self.assertRaises(PermissionError): A.migrate_apply(s, dst)
        A.migrate_apply(s, dst, confirm=True)
        self.assertTrue(os.path.exists(os.path.join(s, "a.txt"))); self.assertTrue(os.path.exists(os.path.join(dst, "sub/b.txt")))
        self.assertEqual(len(A.migrate_preview(s, dst)["copy"]), 0)   # existing files are skipped, not overwritten

    # 13
    def test_backup_restore_and_unsafe_archive(self):
        s = os.path.join(self.d, "data"); self.mk("data/f.txt", "hello")
        arc = os.path.join(self.d, "b.tgz"); b = A.backup(s, arc)
        out = os.path.join(self.d, "out"); os.makedirs(out)
        with self.assertRaises(PermissionError): A.restore(arc, out)
        with self.assertRaises(ValueError): A.restore(arc, out, expected_sha256="0" * 64, confirm=True)
        A.restore(arc, out, expected_sha256=b["sha256"], confirm=True)
        self.assertEqual(open(os.path.join(out, "data/f.txt")).read(), "hello")
        evil = os.path.join(self.d, "evil.tgz")
        with tarfile.open(evil, "w:gz") as t:
            ti = tarfile.TarInfo("../escape.txt"); ti.size = 1; t.addfile(ti, io.BytesIO(b"x"))
        with self.assertRaises(ValueError): A.restore(evil, out, confirm=True)
        self.assertFalse(os.path.exists(os.path.join(self.d, "escape.txt")))

    # 22
    def test_config_audit(self):
        p = self.mk("sshd_config", "PermitRootLogin yes\nPasswordAuthentication no\n")
        f = A.audit_sshd(p)["findings"]; self.assertEqual(len(f), 1); self.assertEqual(f[0]["severity"], "high")

    # 12,14,19
    def test_driver_compat_db(self):
        self.assertIn("available", B.detect_drivers())
        db = B.CompatDB(os.path.join(self.d, "c.json"))
        db.add("ThinkPad T420", "0.0.1", "works", source="tested"); db.add("Foo X1", "0.0.1", "works")
        self.assertEqual(len(db.query("thinkpad", verified_only=True)), 1); self.assertEqual(len(db.query("foo", verified_only=True)), 0)
        self.assertEqual(len(B.CompatDB(os.path.join(self.d, "c.json")).rows), 2)
        self.assertTrue(B.system_requirements(1, 0.001)["disk_ok"])

    # 15
    def test_performance(self):
        s = B.snapshot(); self.assertGreaterEqual(s["cpus"], 1); self.assertIn("proposals", s)

    # 16
    def test_disk_manager_guards(self):
        p = B.plan_format("/dev/does-not-exist"); self.assertTrue(p["blocked"])
        with self.assertRaises(PermissionError): B.format_device("/dev/x", "ext4", "/dev/x")
        with self.assertRaises(PermissionError): B.format_device("/dev/x", "ext4", "wrong", confirm=True)
        with self.assertRaises(PermissionError): B.format_device("/dev/does-not-exist", "ext4", "/dev/does-not-exist", confirm=True)

    # 20
    def test_firewall(self):
        p = B.firewall_preview("public"); self.assertIn("ufw default deny incoming", p["commands"])
        with self.assertRaises(PermissionError): B.firewall_apply("public")

    # 24
    def test_app_test_bench_really_runs(self):
        r = B.run_app_test(["echo", "hi"]); self.assertEqual(r["rc"], 0); self.assertIn("hi", r["out"]); self.assertEqual(r["kind"], "actual execution")

    # 25,26
    def test_language_power(self):
        self.assertIn("installed", B.locales())
        p = os.path.join(self.d, "l.json"); json.dump({"keep": 1}, open(p, "w"))
        with self.assertRaises(PermissionError): B.set_locale_pref(p, "fa_IR.UTF-8")
        self.assertEqual(B.set_locale_pref(p, "fa_IR.UTF-8", confirm=True), {"keep": 1, "LANG": "fa_IR.UTF-8"})
        self.assertIn("note", B.power_profiles())

    # 28
    def test_clipboard_privacy(self):
        c = B.Clipboard(limit=2)
        self.assertTrue(c.add("hello")); self.assertFalse(c.add("sk-ant-abcdefghijklmnopqrstuv")); self.assertFalse(c.add("pw", sensitive=True))
        c.add("b"); c.add("c"); self.assertEqual(c.items, ["c", "b"]); c.clear(); self.assertEqual(c.items, [])

    # 31,33
    def test_fonts_docs(self):
        self.assertIn("families", B.list_fonts())
        with self.assertRaises(ValueError): B.install_font(self.mk("a.exe"), self.d, confirm=True)
        self.assertIn("available", B.default_app("text/plain"))

    # 29,46
    def test_screenshot_record_honest(self):
        r = C.screenshot(os.path.join(self.d, "s.png")); self.assertIn("ok", r)
        self.assertIn("available", C.record_command(os.path.join(self.d, "r.mp4")))

    # 30
    def test_notifications(self):
        n = C.Notifications(os.path.join(self.d, "n.log")); n.send("عنوان", "متن", deliver=False)
        self.assertEqual(n.history()[0]["title"], "عنوان")

    # 34,35,37
    def test_audio_display_nightlight(self):
        self.assertIn("available", C.audio_sinks()); self.assertIn("available", C.displays())
        self.assertEqual(C.night_light_cmd(3400)["gammastep"][-1], "3400")
        with self.assertRaises(ValueError): C.night_light_cmd(100)

    # 36,49
    def test_pairing_usb(self):
        with self.assertRaises(PermissionError): C.pair("AA:BB:CC:DD:EE:FF")
        with self.assertRaises(ValueError): C.pair("bad", confirm=True)
        self.assertIn("available", C.usb_devices())
        self.assertFalse(C.safe_to_eject("/dev/__none__")["allowed"] is False)

    # 38
    def test_vault_encrypts(self):
        v = C.Vault(os.path.join(self.d, "v.bin"))
        v.save({"site": {"user": "u", "pw": "s3cretاز"}}, "master")
        raw = open(v.path, "rb").read()
        self.assertNotIn(b"s3cret", raw); self.assertEqual(os.stat(v.path).st_mode & 0o777, 0o600)
        self.assertEqual(v.load("master")["site"]["pw"], "s3cretاز")
        with self.assertRaises(ValueError): v.load("wrong")

    # 39,40
    def test_privacy_scheduler(self):
        self.assertIn("note", C.privacy_report()); self.assertIn("available", C.list_tasks())
        with self.assertRaises(PermissionError): C.add_task("* * * * *", "echo hi")
        with self.assertRaises(ValueError): C.add_task("bad", "echo", confirm=True)

    # 43,44,45
    def test_securedelete_webapps_gamemode(self):
        r = C.secure_delete_advice(self.d); self.assertFalse(r["guarantee"]); self.assertTrue(r["advice"])
        p = C.create_webapp("وب اپ", "https://example.org", self.d)
        self.assertIn("xdg-open https://example.org", open(p, encoding="utf-8").read())
        with self.assertRaises(ValueError): C.create_webapp("x", "file:///etc/passwd", self.d)
        g = C.game_mode_plan(); self.assertIn("firewall", g["never_touches"])

    # 47,48
    def test_share_a11y(self):
        self.assertIn("files", C.share_targets())
        self.assertEqual(C.share_email(self.mk("s.txt"), "a@b.c")[:2], ["xdg-email", "--attach"])
        self.assertIn("available", C.a11y_status())


if __name__ == "__main__":
    unittest.main()
