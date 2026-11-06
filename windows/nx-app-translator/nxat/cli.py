"""nxat CLI:  analyze INPUT | translate INPUT -o OUT.exe --name NAME --entry REL.exe --confirm [--stub STUB.exe] [--electron-zip Z]"""
import argparse, json, os, shutil, sys, tempfile
from . import analyze as A, unpack as U, adapt as D, pack as K, peutil as P

NOTICE = ("NX APP TRANSLATOR modifies a program's binaries. Use it only on software you are entitled to modify (your own, open-source, or "
          "licensed for it) and for your own machines; do not redistribute translated third-party software. Modified files lose their digital signature.")


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


def cmd_translate(a):
    print(NOTICE)
    if not a.confirm:
        print("Refusing: pass --confirm to acknowledge the notice above."); return 2
    stub = a.stub or os.environ.get("NXAT_STUB")
    if not stub or not os.path.isfile(stub):
        print("Installer stub (nx-app-installer.exe, built by CI) not found: pass --stub or set NXAT_STUB."); return 2
    with tempfile.TemporaryDirectory(prefix="nxat_") as w:
        app, method = _prep(a.input, w)
        rep = A.analyze(app)
        if rep["blockers"]:
            print("BLOCKERS (cannot be fixed automatically):")
            for b in rep["blockers"]:
                print("  -", b)
            if not a.force:
                print("Aborting. Use --force to build anyway (the result will probably not start on Windows 7)."); return 1
        for line in D.adapt(app, rep, a.electron_zip):
            print("  adapted:", line)
        after = A.analyze(app)
        left = {r: i["violations"] for r, i in after["pe"].items() if i["violations"]}
        if left:
            print("STILL INCOMPATIBLE after adaptation:", left)
            if not a.force:
                return 1
        entry = a.entry or next((r for r, i in sorted(after["pe"].items()) if r.lower().endswith(".exe") and not i["dll"]
                                 and "uninstall" not in r.lower()), None)
        if not entry:
            print("No entry .exe found; pass --entry."); return 1
        name = a.name or os.path.splitext(os.path.basename(entry))[0]
        pay = K.make_payload(app, os.path.join(w, "payload.zip"))
        out = K.build_installer(stub, pay, {"name": name, "entry": entry.replace(os.sep, "/"), "version": a.version, "publisher": a.publisher,
                                           "translated_by": "NX APP TRANSLATOR", "source": os.path.basename(a.input)}, a.output)
        print("installer written:", out, "(static Win7 check: %s; NOT run on real Windows 7)" % ("clean" if not left else "FAILED"))
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="nxat", description=__doc__)
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("analyze"); x.add_argument("input"); x.add_argument("--json", action="store_true"); x.set_defaults(f=cmd_analyze)
    t = s.add_parser("translate"); t.add_argument("input"); t.add_argument("-o", "--output", required=True)
    t.add_argument("--name"); t.add_argument("--entry"); t.add_argument("--version", default=""); t.add_argument("--publisher", default="")
    t.add_argument("--stub"); t.add_argument("--electron-zip"); t.add_argument("--confirm", action="store_true"); t.add_argument("--force", action="store_true")
    t.set_defaults(f=cmd_translate)
    a = p.parse_args(argv)
    try:
        return a.f(a)
    except (U.UnpackError, FileNotFoundError) as e:
        print("error:", e); return 1


if __name__ == "__main__":
    sys.exit(main())
