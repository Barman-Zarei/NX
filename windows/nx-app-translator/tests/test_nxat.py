import json, os, shutil, struct, subprocess, sys, tempfile, unittest, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
from nxat import analyze as A, adapt as D, pack as K, peutil as P, unpack as U, cli
from nxat import installer_stub as IS
from nxat import supervisor as S

class FakeBrok(object):
    """Stands in for ai.service.brok_adapter.BrokAdapter (real Brok needs a model/API key)."""
    def __init__(self, verdicts=(), edits=None, status="ok"):
        self.verdicts, self.edits, self.status, self.calls = list(verdicts), edits, status, []

    def call(self, mode, text=None, project=None, untrusted=False):
        self.calls.append((mode, untrusted, text))
        if self.status != "ok":
            return self.status, "down"
        if "safety supervisor" in text or "Review this proposed source patch" in text:
            v = self.verdicts.pop(0) if self.verdicts else '{"allow": true, "reason": "ordinary compatibility work"}'
            return "ok", "verdict: " + v
        return "ok", self.edits or "{}"


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
        tgt = IS.install(out, os.path.join(t, "inst"), log=lambda *_: None)
        self.assertEqual(open(os.path.join(tgt, "sub", "f.txt")).read(), "data")
        IS.uninstall(tgt, log=lambda *_: None); self.assertFalse(os.path.exists(tgt))
        b = bytearray(open(out, "rb").read()); b[len(b) - 24 - 200] ^= 0xFF; open(out, "wb").write(b)
        with self.assertRaises(ValueError):
            K.read_package(out)

    def test_confirm_required(self):
        self.assertEqual(cli.main(["translate", "x", "-o", "y"]), 2)

    def test_confrim_typo_alias_accepted(self):
        a = cli.build_parser().parse_args(["translate", "x", "-o", "y", "--confrim"])
        self.assertTrue(a.confirm)


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
        args = cli.build_parser().parse_args(["translate", exe, "-o", out, "--stub", stub, "--confirm", "--name", "Sample"])
        os.environ["NXAT_AUDIT_LOG"] = os.path.join(t, "audit.jsonl")
        self.assertEqual(cli.cmd_translate(args, adapter=FakeBrok(), log=lambda *_: None), 0)
        self.assertIn("gate1", open(os.path.join(t, "audit.jsonl")).read())
        man, off, ln = K.read_package(out)
        self.assertEqual(man["entry"], "app_x64.exe")
        tgt = IS.install(out, os.path.join(t, "i"), log=lambda *_: None)
        self.assertTrue(os.path.isfile(os.path.join(tgt, "nxshim7.dll")))
        self.assertTrue(A.analyze(tgt)["compatible_now"])


if __name__ == "__main__":
    unittest.main()


class Supervision(unittest.TestCase):
    def _rep(self, **kw):
        r = {"pe": {}, "kinds": [], "files": 1, "blockers": [], "notes": [], "fixable": []}
        r.update(kw); return r

    def setUp(self):
        os.environ["NXAT_AUDIT_LOG"] = os.path.join(tempfile.mkdtemp(), "a.jsonl")

    def test_allows_normal_app(self):
        ok, _ = S.gate_translate(FakeBrok(), self._rep(), "notepadplus-setup.exe"); self.assertTrue(ok)

    def test_fail_closed_when_brok_missing_or_down(self):
        self.assertFalse(S.gate_translate(None, self._rep(), "a.exe")[0])
        self.assertFalse(S.gate_translate(FakeBrok(status="unavailable"), self._rep(), "a.exe")[0])
        self.assertFalse(S.gate_translate(FakeBrok(status="timeout"), self._rep(), "a.exe")[0])

    def test_fail_closed_on_garbage_or_non_boolean_verdict(self):
        for v in ("sure, go ahead", '{"allow": "true"}', '{"allow": 1}', '{"reason": "x"}'):
            self.assertFalse(S.gate_translate(FakeBrok([v]), self._rep(), "a.exe")[0], v)

    def test_brok_deny_respected(self):
        ok, why = S.gate_translate(FakeBrok(['{"allow": false, "reason": "looks like a RAT"}']), self._rep(), "a.exe")
        self.assertFalse(ok); self.assertIn("RAT", why)

    def test_hard_rules_cannot_be_overridden_by_brok(self):
        b = FakeBrok()
        self.assertFalse(S.gate_translate(b, self._rep(), "Photoshop_keygen.exe")[0])
        pe = {"x.exe": {"imports": [("kernel32.dll", ["WriteProcessMemory", "CreateRemoteThread", "VirtualAllocEx"])], "sections": [".text"]}}
        self.assertFalse(S.gate_translate(b, self._rep(pe=pe), "tool.exe")[0])
        pe = {"y.exe": {"imports": [], "sections": [".text", ".vmp0"]}}
        self.assertFalse(S.gate_translate(b, self._rep(pe=pe), "app.exe")[0])
        self.assertEqual(b.calls, [])                      # Brok was never even asked

    def test_app_content_is_sent_as_untrusted(self):
        b = FakeBrok(); S.gate_translate(b, self._rep(), "a.exe")
        self.assertTrue(all(c[1] for c in b.calls))

    def test_dangerous_patch_blocked_by_rules(self):
        d = "--- a/m.js\n+++ b/m.js\n+require('child_process').exec('powershell -enc AAAA')\n"
        self.assertFalse(S.gate_patch(FakeBrok(), d, 1)[0])

    def test_audit_written(self):
        S.gate_translate(FakeBrok(), self._rep(), "a.exe")
        self.assertIn('"event": "gate1"', open(os.environ["NXAT_AUDIT_LOG"]).read())

    def test_translate_refused_when_no_brok(self):
        t = tempfile.mkdtemp(); stub = os.path.join(t, "s.exe"); open(stub, "wb").write(b"MZ")
        os.makedirs(os.path.join(t, "in")); open(os.path.join(t, "in", "a.txt"), "w").write("x")
        a = cli.build_parser().parse_args(["translate", os.path.join(t, "in"), "-o", os.path.join(t, "o.exe"), "--stub", stub, "--confirm", "--brok-dir", "/nonexistent"])
        import nxat.cli as c
        self.assertEqual(c.cmd_translate(a, adapter=FakeBrok(status="unavailable"), log=lambda *_: None), 3)
        self.assertFalse(os.path.exists(os.path.join(t, "o.exe")))


@unittest.skipUnless(shutil.which("node"), "node missing")
class Agent(unittest.TestCase):
    def _electron(self, t, js):
        from nxat import agent as AG
        src = os.path.join(t, "src"); os.makedirs(src); open(os.path.join(src, "main.js"), "w").write(js)
        os.makedirs(os.path.join(t, "app", "resources")); open(os.path.join(t, "app", "version"), "w").write("30.0.0")
        open(os.path.join(t, "app", "icudtl.dat"), "w").write("x")
        asar = os.path.join(t, "app", "resources", "app.asar"); AG.write_asar(src, asar)
        return asar

    def setUp(self):
        os.environ["NXAT_AUDIT_LOG"] = os.path.join(tempfile.mkdtemp(), "a.jsonl")

    def test_asar_writer_roundtrip(self):
        t = tempfile.mkdtemp(); asar = self._electron(t, "console.log(1)\n")
        U.read_asar(asar, os.path.join(t, "o")); self.assertEqual(open(os.path.join(t, "o", "main.js")).read(), "console.log(1)\n")

    def test_full_loop_patches_checks_repacks(self):
        from nxat import agent as AG, decompile as DC
        t = tempfile.mkdtemp(); asar = self._electron(t, "const x = (1;\n")      # syntax error on purpose
        rep = A.analyze(os.path.join(t, "app"))
        dec = DC.decompile(os.path.join(t, "app"), rep, os.path.join(t, "dec"))
        self.assertEqual(dec["kind"], "electron-js")
        fix = json.dumps({"edits": [{"path": "main.js", "new_text": "const x = (1);\nconsole.log(x);\n"}], "explanation": "fix"})
        r = AG.run(dec, rep, FakeBrok(edits=fix), log=lambda *_: None)
        self.assertTrue(r["verified"] and r["assembled"], r)
        U.read_asar(asar, os.path.join(t, "o2"))
        self.assertIn("console.log(x)", open(os.path.join(t, "o2", "main.js")).read())

    def test_path_escape_and_new_files_rejected(self):
        from nxat import agent as AG, decompile as DC
        t = tempfile.mkdtemp(); self._electron(t, "1;\n")
        rep = A.analyze(os.path.join(t, "app")); dec = DC.decompile(os.path.join(t, "app"), rep, os.path.join(t, "dec"))
        bad = json.dumps({"edits": [{"path": "../../evil.js", "new_text": "x"}, {"path": "new.js", "new_text": "x"}]})
        r = AG.run(dec, rep, FakeBrok(edits=bad), log=lambda *_: None, rounds=1)
        self.assertEqual(r["changed"], []); self.assertTrue(any("rejected" in n for n in r["notes"]))

    def test_gate2_denial_stops_before_any_write(self):
        from nxat import agent as AG, decompile as DC
        t = tempfile.mkdtemp(); self._electron(t, "1;\n")
        rep = A.analyze(os.path.join(t, "app")); dec = DC.decompile(os.path.join(t, "app"), rep, os.path.join(t, "dec"))
        fix = json.dumps({"edits": [{"path": "main.js", "new_text": "2;\n"}]})
        b = FakeBrok(['{"allow": false, "reason": "suspicious"}'], edits=fix)
        r = AG.run(dec, rep, b, log=lambda *_: None)
        self.assertEqual(r["changed"], []); self.assertEqual(open(os.path.join(dec["src"], "main.js")).read(), "1;\n")
