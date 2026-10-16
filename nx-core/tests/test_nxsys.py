import os, sys, tempfile, unittest, zipfile, tarfile, io
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from nxsys import hwlab, preflight, storage, archive, netdiag, procs, bugreport, power, startup


class T(unittest.TestCase):
    def setUp(self): self.d = tempfile.mkdtemp(prefix="nxsys-آزمون-")
    def w(self, n, b):
        p = os.path.join(self.d, n); os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "wb").write(b); return p

    def test_hwlab_preflight(self):
        r = hwlab.report(); self.assertTrue(r["mem_total_mib"] and r["cpu_threads"]); self.assertEqual(r["diagnostics_run"], [])
        p = preflight.run(self.d, check_network=False); self.assertEqual({c[0] for c in p["checks"]}, {"ram", "disk_space", "firmware", "data_loss_notice"})
        self.assertFalse(preflight.run(self.d, min_disk_gib=10**9, check_network=False)["ok"])

    def test_storage_and_duplicates_never_delete(self):
        a = self.w("a/x.bin", b"same" * 100); b = self.w("b/y.bin", b"same" * 100); self.w("c/z.bin", b"diff" * 100)
        g = storage.find_duplicates(self.d); self.assertEqual(g, [sorted([a, b])])
        self.assertTrue(os.path.exists(a) and os.path.exists(b))
        self.assertEqual(len(storage.large_files(self.d, top=2)), 2)

    def test_archive_safety(self):
        z = os.path.join(self.d, "evil.zip")
        with zipfile.ZipFile(z, "w") as zf: zf.writestr("../escape.txt", "x")
        with self.assertRaises(archive.UnsafeArchive): archive.extract(z, os.path.join(self.d, "o"))
        self.assertFalse(os.path.exists(os.path.join(self.d, "escape.txt")))
        t = os.path.join(self.d, "l.tar")
        with tarfile.open(t, "w") as tf:
            i = tarfile.TarInfo("ln"); i.type = tarfile.SYMTYPE; i.linkname = "/etc/passwd"; tf.addfile(i)
        with self.assertRaises(archive.UnsafeArchive): archive.extract(t, os.path.join(self.d, "o2"))
        f = self.w("ok/f.txt", "héllo".encode()); good = os.path.join(self.d, "ok.zip"); archive.create_zip(good, [f], self.d)
        self.assertEqual(archive.extract(good, os.path.join(self.d, "o3")), ["ok/f.txt"])

    def test_netdiag_shapes(self):
        for c in netdiag.run_all(): self.assertIn(c["status"], ("pass", "fail", "tool_unavailable"))
        self.assertEqual(netdiag.tcp("127.0.0.1", 1)["status"], "fail")

    def test_process_manager_protection(self):
        ps = procs.list_processes(); self.assertTrue(any(p["pid"] == os.getpid() for p in ps))
        with self.assertRaises(PermissionError): procs.terminate(1, confirm=True)
        with self.assertRaises(PermissionError): procs.terminate(os.getpid())

    def test_bugreport_sanitizes(self):
        t = bugreport.build("token=abc123 from 10.1.2.3 in /home/bob/x")
        for s in ("abc123", "10.1.2.3", "bob"): self.assertNotIn(s, t)

    def test_power_and_startup(self):
        self.assertIn("supported", power.status())
        ud = os.path.join(self.d, "as"); startup.disable("foo.desktop", ud)
        self.assertTrue(startup.entries([ud])[0]["hidden"])


if __name__ == "__main__":
    unittest.main()
