"""Apply the automatic fixes found by analyze(): PE version fields, import redirection (+ shim DLL), Electron runtime swap."""
import os, shutil, urllib.request, zipfile
from . import peutil as P

ELECTRON_URL = "https://github.com/electron/electron/releases/download/v22.3.27/electron-v22.3.27-win32-%s.zip"


def shim_path(arch):
    here = os.path.dirname(os.path.abspath(__file__))
    frozen = getattr(__import__("sys"), "_MEIPASS", here)
    for p in (os.path.join(here, "..", "shim", "bin", arch, P.SHIM_DLL), os.path.join(frozen, "shim", "bin", arch, P.SHIM_DLL)):
        if os.path.isfile(p):
            return os.path.abspath(p)
    raise FileNotFoundError("nxshim7.dll (%s) not built: run shim/build.sh" % arch)


def swap_electron(root, rep, electron_zip=None, arch="x64"):
    """Replace the Electron runtime with 22.3.27, keep resources/ (app code) and the app's own exe name. Returns a note."""
    e = rep.get("electron")
    if not e or e["major"] <= 22:
        return None
    edir = os.path.join(root, e["dir"])
    exe = next((f for f in os.listdir(edir) if f.lower().endswith(".exe") and f.lower() not in ("uninstall.exe", "update.exe")), None)
    if not exe:
        raise RuntimeError("Electron app exe not found")
    if not electron_zip:
        tmp = os.path.join(root, "..", "electron22-%s.zip" % arch)
        urllib.request.urlretrieve(ELECTRON_URL % arch, tmp)
        electron_zip = tmp
    keep = os.path.join(edir, "resources")
    stage = os.path.join(root, "..", "_electron22_stage")
    shutil.rmtree(stage, ignore_errors=True)
    with zipfile.ZipFile(electron_zip) as z:
        z.extractall(stage)
    for n in os.listdir(edir):
        if n.lower() != "resources" and not n.lower().endswith((".json", ".txt")):
            p = os.path.join(edir, n)
            shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
    for n in os.listdir(stage):
        if n.lower() == "resources":
            for r in os.listdir(os.path.join(stage, n)):      # default_app.asar must not shadow app.asar / app/
                if r.lower() != "default_app.asar":
                    shutil.copy2(os.path.join(stage, n, r), os.path.join(keep, r)) if not os.path.exists(os.path.join(keep, r)) else None
            continue
        d = os.path.join(edir, n)
        shutil.copytree(os.path.join(stage, n), d) if os.path.isdir(os.path.join(stage, n)) else shutil.copy2(os.path.join(stage, n), d)
    os.replace(os.path.join(edir, "electron.exe"), os.path.join(edir, exe)) if exe.lower() != "electron.exe" else None
    shutil.rmtree(stage, ignore_errors=True)
    return "Electron %d -> 22.3.27 in %s (exe %s)" % (e["major"], e["dir"], exe)


def adapt(root, rep, electron_zip=None):
    """Mutates files under root. Returns log lines. Never touches files that are already Win7-clean."""
    log = []
    arch_main = None
    for rel, info in sorted(rep["pe"].items()):
        if not info["violations"] or info["arch"] not in ("x86", "x64"):
            continue
        p = os.path.join(root, rel)
        arch_main = arch_main or info["arch"]
        moved = []
        if info["post_win7"]:
            moved = P.redirect_imports(p)
        if P.patch_versions(p):
            log.append("%s: OS/subsystem version -> 6.1" % rel)
        if moved:
            shutil.copy2(shim_path(info["arch"]), os.path.join(os.path.dirname(p), P.SHIM_DLL))
            log.append("%s: %d imports -> %s (%s)" % (rel, len(moved), P.SHIM_DLL, ", ".join(moved)))
    if rep.get("electron"):
        n = swap_electron(root, rep, electron_zip, arch_main or "x64")
        if n:
            log.append(n)
    return log
