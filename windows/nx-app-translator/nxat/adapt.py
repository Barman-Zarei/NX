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
    """Replace the Electron runtime with 22.3.27 (last Windows 7 line), keep resources/ (the app) and the app's own exe name.
    Files of the old runtime that also exist in the new one are replaced; leftovers that 22 does not use stay harmlessly. Returns a note."""
    e = rep.get("electron")
    if not e or e["major"] <= 22:
        return None
    edir = os.path.join(root, e["dir"])
    skip = ("uninstall.exe", "update.exe", "squirrel.exe", "crashpad_handler.exe")
    exes = [f for f in os.listdir(edir) if f.lower().endswith(".exe") and f.lower() not in skip]
    if not exes:
        raise RuntimeError("Electron app exe not found")
    exe = max(exes, key=lambda f: os.path.getsize(os.path.join(edir, f)))
    if not electron_zip:
        electron_zip = os.path.join(os.path.dirname(os.path.abspath(root)), "electron22-%s.zip" % arch)
        urllib.request.urlretrieve(ELECTRON_URL % arch, electron_zip)
    stage = os.path.join(os.path.dirname(os.path.abspath(root)), "_electron22_stage")
    shutil.rmtree(stage, ignore_errors=True)
    with zipfile.ZipFile(electron_zip) as z:
        z.extractall(stage)
    new_names = {n.lower() for n in os.listdir(stage)} - {"resources"}
    for n in os.listdir(edir):
        if n.lower() in new_names or n.lower() == exe.lower():
            p = os.path.join(edir, n)
            shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
    for n in os.listdir(stage):
        if n.lower() == "resources":
            continue
        src, dst = os.path.join(stage, n), os.path.join(edir, exe if n.lower() == "electron.exe" else n)
        shutil.copytree(src, dst) if os.path.isdir(src) else shutil.copy2(src, dst)
    shutil.rmtree(stage, ignore_errors=True)
    return "Electron %d -> 22.3.27 in %s (exe %s)" % (e["major"], e["dir"], exe)


def adapt(root, rep, electron_zip=None):
    """Mutates files under root. Returns log lines. Never touches files that are already Win7-clean.
    Electron runtime is swapped FIRST (its binaries are replaced), then the remaining binaries are analysed again and patched."""
    from . import analyze as A
    log = []
    if rep.get("electron") and rep["electron"]["major"] > 22:
        arch = next((i["arch"] for i in rep["pe"].values() if i["arch"] in ("x86", "x64")), "x64")
        n = swap_electron(root, rep, electron_zip, arch)
        if n:
            log.append(n)
        rep = A.analyze(root)
    for rel, info in sorted(rep["pe"].items()):
        if not info["violations"] or info["arch"] not in ("x86", "x64"):
            continue
        p = os.path.join(root, rel)
        moved = []
        if info["post_win7"]:
            moved = P.redirect_imports(p)
        if P.patch_versions(p):
            log.append("%s: OS/subsystem version -> 6.1" % rel)
        if moved:
            shutil.copy2(shim_path(info["arch"]), os.path.join(os.path.dirname(p), P.SHIM_DLL))
            log.append("%s: %d imports -> %s (%s)" % (rel, len(moved), P.SHIM_DLL, ", ".join(moved)))
    return log
