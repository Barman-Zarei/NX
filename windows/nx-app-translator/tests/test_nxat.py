import json, os, shutil, struct, subprocess, sys, tempfile, unittest, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
from nxat import analyze as A, adapt as D, pack as K, peutil as P, unpack as U, cli
from nxat import installer_stub as S

SRC = r"""#define _WIN32_WINNT 0x0A00
#include <windows.h>
int main(void){ FILETIME f; GetSystemTimePreciseAsFileTime(&f); volatile LONG v=1; LONG c=2; WaitOnAddress(&v,&c,4,10); return GetDpiForSystem()>0?0:1; }
"""
CC = {"x64": "x86_64-w64-mingw32-gcc", "x86": "i686-w64-mingw32-gcc"}
SHIM = {a: os.path.join(HERE, "..", "shim", "bin", a, "nxshim7.dll") for a in CC}


def build_sample(tmp, arch):
    c = os.path.join(tmp, "s.c")
    with open(c, "w") as f:
        f.write(SRC)
    exe = os.path.join(tmp, "app_%s.exe" % arch)
    subprocess.check_call([CC[arch], c, "-o", exe, "-lkernel32", "-luser32", "-lsynchronization"])
    return exe


def have(arch):
    import shutil as sh
    return sh.which(CC[arch]) and os.path.isfile(SHIM[arch])


class Pure(unittest.TestCase):
    def test_asar_roundtrip(self):
        t = tempfile.mkdtemp()
        data = b"hello"
        idx = json.dumps({"files": {"a.txt": {"size": 5, "offset": "0"}, "d": {"files": {"b.txt": {"size": 5, "offset": "5"}}}}}).encode()
        pad = (4 - len(idx) % 4) % 4
        hdr = struct.pack("<IIII", 4, len(idx) + pad + 8, len(idx) + pad + 4, len(idx)) + idx + b"\0" * pad
        open(os.path.join(t, "x.asar"), "wb").write(hdr + b"hellohello")
        U.read_asar(os.path.join(t, "x.asar"), os.path.join(t, "out"))
        self.assertEqual(open(os.path.join(t, "out", "d", "b.txt"), "rb").read(), data)

    def test_asar_path_traversal_rejected(self):
        t = tempfile.mkdtemp()
        idx = json.dumps({"files": {"..": {"files": {"evil.txt": {"size": 1, "offset": "0"}}}}}).encode()
        pad = (4 - len(idx) % 4) % 4
        hdr = struct.pack("<IIII", 4, len(idx) + pad + 8, len(idx) + pad + 4, len(idx)) + idx + b"\0" * pad
        open(os.path.join(t, "x.asar"), "wb").write(hdr + b"x")
        with self.assertRaises(U.UnpackError):
            U.read_asar(os.path.join(t, "x.asar"), os.path.join(t, "out"))

    def test_zip_slip_rejected(self):
        t = tempfile.mkdtemp(); z = os.path.join(t, "a.zip")
        with zipfile.ZipFile(z, "w") as f:
            f.writestr("../evil.txt", "x")
        with self.assertRaises(U.UnpackError):
            U.unpack(z, os.path.join(t, "out"))

    def test_python_and_dotnet_blockers(self):
        t = tempfile.mkdtemp()
        open(os.path.join(t, "python311.dll"), "wb").write(b"x")
        json.dump({"runtimeOptions": {"framework": {"name": "Microsoft.NETCore.App", "version": "8.0.0"}}}, open(os.path.join(t, "a.runtimeconfig.json"), "w"))
        r = A.analyze(t)
        self.assertEqual(len(r["blockers"]), 2)
        self.assertFalse(r["compatible_now"])

    def test_electron_detection(self):
        t = tempfile.mkdtemp()
        os.makedirs(os.path.join(t, "resources")); open(os.path.join(t, "version"), "w").write("30.1.0\n"); open(os.path.join(t, "icudtl.dat"), "w").write("x")
        r = A.analyze(t)
        self.assertEqual(r["electron"]["major"], 30)
        self.assertTrue(any(f.startswith("electron-swap") for f in r["fixable"]))

    def test_package_roundtrip_and_tamper(self):
        t = tempfile.mkdtemp()
        os.makedirs(os.path.join(t, "app", "sub")); open(os.path.join(t, "app", "sub", "f.txt"), "w").write("data")
        z = K.make_payload(os.path.join(t, "app"), os.path.join(t, "p.zip"))
        stub = os.path.join(t, "stub.exe"); open(stub, "wb").write(b"MZ-stub")
        out = K.build_installer(stub, z, {"name": "Demo", "entry": "sub/f.txt"}, os.path.join(t, "setup.exe"))
        man, off, ln = K.read_package(out)
        self.assertEqual(man["name"], "Demo")
        tgt = S.install(out, os.path.join(t, "inst"), log=lambda *_: None)
        self.assertEqual(open(os.path.join(tgt, "sub", "f.txt")).read(), "data")
        S.uninstall(tgt, log=lambda *_: None); self.assertFalse(os.path.exists(tgt))
        b = bytearray(open(out, "rb").read()); b[len(b) - 24 - 200] ^= 0xFF; open(out, "wb").write(b)
        with self.assertRaises(ValueError):
            K.read_package(out)

    def test_confirm_required(self):
        self.assertEqual(cli.main(["translate", "x", "-o", "y"]), 2)


class WithCompiler(unittest.TestCase):
    def _run(self, arch):
        if not have(arch):
            self.skipTest("mingw or shim not built for " + arch)
        t = tempfile.mkdtemp(); exe = build_sample(t, arch)
        r = A.analyze(os.path.dirname(exe))
        self.assertFalse(r["compatible_now"])
        app = os.path.join(t, "app"); os.makedirs(app); shutil.copy2(exe, app)
        rep = A.analyze(app)
        log = D.adapt(app, rep)
        self.assertTrue(any("nxshim7.dll" in l for l in log), log)
        self.assertTrue(os.path.isfile(os.path.join(app, "nxshim7.dll")))
        after = A.analyze(app)
        self.assertTrue(after["compatible_now"], after)
        info = P.read_info(os.path.join(app, os.path.basename(exe)))
        self.assertIn("nxshim7.dll", [d for d, _ in info["imports"]])
        self.assertEqual(sorted(n for d, ns in info["imports"] if d == "nxshim7.dll" for n in ns),
                         ["GetDpiForSystem", "GetSystemTimePreciseAsFileTime", "WaitOnAddress"])
        wine = shutil.which("wine")
        if wine and os.environ.get("NXAT_WINE") == "1":
            env = dict(os.environ, WINEDEBUG="-all", WINEPREFIX=os.path.join(t, "wp"))
            self.assertEqual(subprocess.run([wine, os.path.join(app, os.path.basename(exe))], env=env, timeout=180).returncode, 0)

    def test_x64(self): self._run("x64")
    def test_x86(self): self._run("x86")

    def test_shim_exports_cover_shimmed(self):
        if not have("x64"):
            self.skipTest("shim not built")
        import pefile
        pe = pefile.PE(SHIM["x64"])
        ex = {e.name.decode() for e in pe.DIRECTORY_ENTRY_EXPORT.symbols if e.name}
        self.assertEqual(P.SHIMMED - ex, set())

    def test_full_translate_cli(self):
        if not have("x64"):
            self.skipTest("shim not built")
        t = tempfile.mkdtemp(); exe = build_sample(t, "x64")
        stub = os.path.join(t, "stub.exe"); open(stub, "wb").write(b"MZ-stub")
        out = os.path.join(t, "setup.exe")
        self.assertEqual(cli.main(["translate", exe, "-o", out, "--stub", stub, "--confirm", "--name", "Sample"]), 0)
        man, off, ln = K.read_package(out)
        self.assertEqual(man["entry"], "app_x64.exe")
        tgt = S.install(out, os.path.join(t, "i"), log=lambda *_: None)
        self.assertTrue(os.path.isfile(os.path.join(tgt, "nxshim7.dll")))
        self.assertTrue(A.analyze(tgt)["compatible_now"])


if __name__ == "__main__":
    unittest.main()
