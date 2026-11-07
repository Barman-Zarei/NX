"""nxat CLI:  analyze INPUT | translate INPUT -o OUT.exe --confirm [--name N] [--entry REL.exe] [--stub STUB.exe] [--strict] [--no-source-ai]"""
import argparse, json, os, shutil, sys, tempfile
from . import analyze as A, unpack as U, adapt as D, pack as K, peutil as P, supervisor as S, decompile as DC, agent as AG

NOTICE = ("NX APP TRANSLATOR modifies a program so it can run on old (Windows 7) laptops. Modified files lose their digital signature. "
          "Brok supervises every translation and may refuse it; use it only on software you are entitled to modify and do not redistribute translated third-party software.")


def load_brok(brok_dir=None):
    """The NX Brok adapter (ai/service/brok_adapter.py, Linux, never root). None if it cannot be loaded -> supervision fails closed."""
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(os.path.join(here, "..", "..", ".."))
    for c in (root, "/usr/lib/nx", "/opt/nx"):
        if os.path.isfile(os.path.join(c, "ai", "service", "brok_adapter.py")):
            if c not in sys.path:
                sys.path.insert(0, c)
            try:
                from ai.service.brok_adapter import BrokAdapter
                return BrokAdapter(brok_dir=brok_dir, timeout=300)
            except Exception:
                return None
    return None


def default_stub():
    here = os.path.dirname(os.path.abspath(__file__))
    # x86 stub first: it runs on 32- and 64-bit Windows 7+
    for c in (os.environ.get("NXAT_STUB", ""), os.path.join(here, "..", "stub", "bin", "x86", "nx-app-installer.exe"),
              "/usr/share/nx/nx-app-installer.exe", os.path.join(here, "nx-app-installer.exe")):
        if c and os.path.isfile(c):
            return c
    return None


def _prep(inp, work):
    app = os.path.join(work, "app")
    method = U.unpack(inp, app)
    return app, method


def cmd_analyze(a):
    with tempfile.TemporaryDirectory(prefix="nxat_") as w:
        app, method = _prep(a.input, w)
        rep = A.analyze(app); rep["unpack_method"] = method
        if a.json:
            print(json.dumps(rep, indent=1, default=str))
        else:
            print("input: %s (%s)  files: %d  kinds: %s" % (a.input, method, rep["files"], ", ".join(rep["kinds"]) or "native"))
            for r, i in sorted(rep["pe"].items()):
                if i["violations"]:
                    print("  NEEDS FIX:", r, "; ".join(i["violations"]))
            for k in ("fixable", "blockers", "notes"):
                for x in rep[k]:
                    print("  %s: %s" % (k.upper(), x))
            print("compatible with Windows 7 as-is (static check):", rep["compatible_now"])
    return 0


def cmd_translate(a, adapter=None, log=print):
    log(NOTICE)
    if not a.confirm:
        log("Refusing: pass --confirm to acknowledge the notice above."); return 2
    stub = a.stub or default_stub()
    if not stub or not os.path.isfile(stub):
        log("Installer stub (nx-app-installer.exe, built by CI) not found: pass --stub or set NXAT_STUB."); return 2
    adapter = adapter if adapter is not None else load_brok(a.brok_dir)
    with tempfile.TemporaryDirectory(prefix="nxat_") as w:
        app, method = _prep(a.input, w)
        rep = A.analyze(app)
        ok, why = S.gate_translate(adapter, rep, os.path.basename(a.input), root=app)        # gate 1: cannot be skipped
        if not ok:
            log("BROK SUPERVISION: translation refused - %s" % why); return 3
        log("Brok supervision: allowed (%s)" % (why or "no objection"))
        for line in D.adapt(app, rep, a.electron_zip):
            log("  adapted: " + line)
        after = A.analyze(app)
        if not a.no_source_ai and (after["blockers"] or after.get("electron")):
            dec = DC.decompile(app, after, os.path.join(w, "decompiled"))
            for n in dec["notes"]:
                log("  decompile: " + n)
            if dec.get("src"):
                log("  decompiled with %s -> %s" % (dec["tool"], dec["kind"]))
                try:
                    r = AG.run(dec, after, adapter, log)
                    for n in r["notes"]:
                        log("  agent: " + n)
                    log("  agent: patched %s; verified=%s; assembled=%s" % (r["changed"] or "nothing", r["verified"], r["assembled"]))
                except RuntimeError as e:
                    log("  agent skipped: %s" % e)
            after = A.analyze(app)
            for line in D.adapt(app, after, a.electron_zip):          # re-check after source changes / native rebuild
                log("  adapted: " + line)
            after = A.analyze(app)
        left = {r: i["violations"] for r, i in after["pe"].items() if i["violations"]}
        if after["blockers"] or left:
            log("WARNING - not fixable automatically, the program will probably NOT start on Windows 7:")
            for b in after["blockers"] + ["%s: %s" % (k, "; ".join(v)) for k, v in left.items()]:
                log("  - " + b)
            if a.strict:
                log("Aborting (--strict)."); return 1
        entry = a.entry or next((r for r, i in sorted(after["pe"].items()) if r.lower().endswith(".exe") and not i["dll"]
                                 and "uninstall" not in r.lower()), None)
        if not entry:
            log("No entry .exe found; pass --entry."); return 1
        name = a.name or os.path.splitext(os.path.basename(entry))[0]
        pay = K.make_payload(app, os.path.join(w, "payload.zip"))
        out = K.build_installer(stub, pay, {"name": name, "entry": entry.replace(os.sep, "/"), "version": a.version, "publisher": a.publisher,
                                           "translated_by": "NX APP TRANSLATOR", "source": os.path.basename(a.input)}, a.output)
        log("installer written: %s (static Win7 check: %s; NOT run on real Windows 7)" % (out, "clean" if not (left or after["blockers"]) else "ISSUES REMAIN"))
    return 0


SELFTEST = [   # (label, expected, kinds, executables, imports) - synthetic fact sheets; NO real programs involved
    ("ordinary Electron editor", True, ["electron"], ["Notes.exe"], ["CreateFileW"]),
    ("ordinary small native tool", True, [], ["Calc2000.exe"], ["CreateWindowExW", "GetSystemTimePreciseAsFileTime"]),
    ("ordinary .NET business app", True, ["dotnet-core"], ["Invoicer.exe"], ["CreateFileW"]),
    ("system-looking process that persists and beacons", False, [], ["svchost_update.exe", "winlogon32.exe"],
     ["RegSetValueExW", "InternetOpenUrlW", "ShellExecuteW", "CreateServiceW"]),
    ("'activation helper' for paid software", False, [], ["OfficeActivationHelper.exe", "license_server_emulator.exe"], ["CreateFileW", "send", "recv"]),
    ("game cheat injector (no flagged APIs)", False, [], ["AimbotLoader.exe", "csgo_wallhack.dll"], ["OpenProcess", "ReadProcessMemory"]),
]


def cmd_brok_selftest(a, adapter=None, log=print):
    """Feeds synthetic fact sheets through gate 1 with the REAL Brok to measure the supervisor. Informational: never changes anything."""
    adapter = adapter if adapter is not None else load_brok(a.brok_dir)
    if adapter is None:
        log("Brok adapter not available: gate 1 would refuse every translation (fail closed)."); return 3
    bad = 0
    for label, expected, kinds, exes, imps in SELFTEST:
        rep = {"pe": {e: {"imports": [("kernel32.dll", imps)], "sections": [".text"], "violations": []} for e in exes},
               "kinds": kinds, "files": len(exes), "blockers": [], "notes": [], "fixable": []}
        ok, why = S.gate_translate(adapter, rep, exes[0])
        flag = "OK " if ok == expected else "MISMATCH"
        bad += ok != expected
        log("%-9s expected=%-5s got=%-5s  %s  (%s)" % (flag, "allow" if expected else "deny", "allow" if ok else "deny", label, why[:70]))
    log("%d of %d cases behaved as expected. Deny-expected cases that were allowed are the supervisor's weak spots." % (len(SELFTEST) - bad, len(SELFTEST)))
    return 0


def build_parser():
    p = argparse.ArgumentParser(prog="nxat", description=__doc__)
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("analyze"); x.add_argument("input"); x.add_argument("--json", action="store_true"); x.set_defaults(f=cmd_analyze)
    bs = s.add_parser("brok-selftest"); bs.add_argument("--brok-dir"); bs.set_defaults(f=cmd_brok_selftest)
    t = s.add_parser("translate"); t.add_argument("input"); t.add_argument("-o", "--output", required=True)
    t.add_argument("--name"); t.add_argument("--entry"); t.add_argument("--version", default=""); t.add_argument("--publisher", default="")
    t.add_argument("--stub"); t.add_argument("--electron-zip"); t.add_argument("--confirm", "--confrim", action="store_true"); t.add_argument("--strict", action="store_true")
    t.add_argument("--no-source-ai", action="store_true", help="skip decompile+Brok source stage (supervision stays on)"); t.add_argument("--brok-dir")
    t.set_defaults(f=cmd_translate)
    return p


def main(argv=None):
    a = build_parser().parse_args(argv)
    try:
        return a.f(a)
    except (U.UnpackError, FileNotFoundError) as e:
        print("error:", e); return 1


if __name__ == "__main__":
    sys.exit(main())
