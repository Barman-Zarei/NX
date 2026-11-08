"""Recover as much source as the available tools allow. Honest by construction: returns what was recovered and which tool did it.
 electron  -> app.asar unpacked (real JavaScript source)         [built in]
 .NET      -> C# via `ilspycmd`                                   [external tool, optional]
 native    -> C via `retdec-decompiler`                           [external tool, optional; output is approximate, rarely rebuildable]
No tool => no source; the pipeline then stays at binary-level adaptation."""
import os, re, shutil, struct, subprocess
from . import unpack as U


EXTRA_PATHS = ("/opt/retdec/bin", "/usr/lib/nx/retdec/bin", "/usr/local/retdec/bin")


def which(name):
    """shutil.which plus the places NX / manual installs put RetDec."""
    p = shutil.which(name)
    if p:
        return p
    for d in EXTRA_PATHS:
        c = os.path.join(d, name)
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return None


def tools():
    return {t: bool(which(t)) for t in ("ilspycmd", "retdec-decompiler", "node", "dotnet", "x86_64-w64-mingw32-gcc")}


def _run(cmd, timeout=900):
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=timeout)
    return r.returncode, r.stdout[-400:]


def _is_gui(exe):
    """PE Subsystem == 2 (WINDOWS_GUI)."""
    try:
        with open(exe, "rb") as f:
            f.seek(0x3C); pe = struct.unpack("<I", f.read(4))[0]
            f.seek(pe + 24 + 68); return struct.unpack("<H", f.read(2))[0] == 2
    except (OSError, struct.error):
        return False


def decompile(root, rep, out):
    """-> dict(kind, src, tool, notes). `src` is a directory with recovered source or None."""
    os.makedirs(out, exist_ok=True)
    res = {"kind": None, "src": None, "tool": None, "notes": []}
    if rep.get("electron"):
        edir = os.path.join(root, rep["electron"]["dir"], "resources")
        asar = os.path.join(edir, "app.asar")
        if os.path.isfile(asar):
            dst = os.path.join(out, "electron-app"); U.read_asar(asar, dst)
            res.update(kind="electron-js", src=dst, tool="builtin-asar", asar=asar)
            return res
        if os.path.isdir(os.path.join(edir, "app")):
            res.update(kind="electron-js", src=os.path.join(edir, "app"), tool="plain-folder", asar=None)
            return res
    exes = sorted(r for r, i in rep["pe"].items() if r.lower().endswith(".exe") and not i["dll"])
    from . import dotnet as DN
    nxd = DN.find_nxdecompile()
    for item in rep.get("dotnet_core", []):                  # .NET (Core) 7+ apps: ILSpy engine -> C# 7.3 -> mcs (.NET Framework 4, runs on Windows 7)
        cfg = os.path.join(root, item["config"]); asm = cfg[:-len(".runtimeconfig.json")] + ".dll"
        if not (nxd and shutil.which("dotnet") and os.path.isfile(asm)):
            res["notes"].append(".NET app: needs the ILSpy engine tool (tools/nxdecompile/setup.sh) and the dotnet runtime to recover C#"); break
        dst = os.path.join(out, "dotnet-src"); os.makedirs(dst, exist_ok=True)
        cs = os.path.join(dst, os.path.basename(asm)[:-4] + ".cs")
        rc, tail = _run(["dotnet", nxd, asm, cs, "7.3"])
        if rc != 0 or not os.path.isfile(cs):
            res["notes"].append("NxDecompile failed: " + tail); break
        with open(cs, encoding="utf-8") as f:
            text = f.read()
        with open(cs, "w", encoding="utf-8") as f:
            f.write(DN.clean_decompiled(text))
        base = cs[:-3]
        apphost = asm[:-4] + ".exe"
        res.update(kind="dotnet-cs", src=dst, tool="NxDecompile (ILSpy 8.2)", asm=asm, exe=apphost, config=cfg, base=os.path.basename(base))
        return res
    from . import pyfrozen as PF
    for rel in exes:
        exe = os.path.join(root, rel)
        if PF.is_pyinstaller(exe):
            if not PF.have_extractor() or not PF.find_pycdc():
                res["notes"].append("frozen Python app: need `pip install pyinstxtractor-ng` and pycdc to recover source"); break
            ext = PF.extract(exe, out)
            if not ext:
                res["notes"].append("PyInstaller archive could not be extracted"); break
            minor = PF.minor_from_extracted(ext)
            r = PF.decompile(ext, os.path.splitext(os.path.basename(exe))[0], minor, os.path.join(out, "python-src")) if minor else None
            if r:
                res.update(kind="python-src", src=r["src"], tool="pyinstxtractor-ng+pycdc", exe=exe, entry_py=r["entry_py"], minor=minor,
                           gui=_is_gui(exe), modules=r["modules"])
                return res
    for rel in exes[:1]:
        info = rep["pe"][rel]
        if info["dotnet"] and shutil.which("ilspycmd"):
            dst = os.path.join(out, "dotnet-src"); os.makedirs(dst, exist_ok=True)
            rc, tail = _run(["ilspycmd", "-p", "-o", dst, os.path.join(root, rel)])
            if rc == 0:
                res.update(kind="dotnet-cs", src=dst, tool="ilspycmd"); return res
            res["notes"].append("ilspycmd failed: " + tail)
        elif which("retdec-decompiler") and not info["dotnet"]:
            dst = os.path.join(out, "native-c"); os.makedirs(dst, exist_ok=True)
            rc, tail = _run([which("retdec-decompiler"), "-o", os.path.join(dst, "out.c"), os.path.join(root, rel)])
            if rc == 0:
                res.update(kind="native-c", src=dst, tool="retdec", exe=os.path.join(root, rel), arch=info["arch"]); return res
            res["notes"].append("retdec failed: " + tail)
    res["notes"].append("no decompiler available for this app (install ilspycmd for .NET or retdec for native code)")
    return res
