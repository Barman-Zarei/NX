"""Recover as much source as the available tools allow. Honest by construction: returns what was recovered and which tool did it.
 electron  -> app.asar unpacked (real JavaScript source)         [built in]
 .NET      -> C# via `ilspycmd`                                   [external tool, optional]
 native    -> C via `retdec-decompiler`                           [external tool, optional; output is approximate, rarely rebuildable]
No tool => no source; the pipeline then stays at binary-level adaptation."""
import os, shutil, subprocess
from . import unpack as U


def tools():
    return {t: bool(shutil.which(t)) for t in ("ilspycmd", "retdec-decompiler", "node", "dotnet", "x86_64-w64-mingw32-gcc")}


def _run(cmd, timeout=900):
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=timeout)
    return r.returncode, r.stdout[-400:]


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
    for rel in exes[:1]:
        info = rep["pe"][rel]
        if info["dotnet"] and shutil.which("ilspycmd"):
            dst = os.path.join(out, "dotnet-src"); os.makedirs(dst, exist_ok=True)
            rc, tail = _run(["ilspycmd", "-p", "-o", dst, os.path.join(root, rel)])
            if rc == 0:
                res.update(kind="dotnet-cs", src=dst, tool="ilspycmd"); return res
            res["notes"].append("ilspycmd failed: " + tail)
        elif shutil.which("retdec-decompiler") and not info["dotnet"]:
            dst = os.path.join(out, "native-c"); os.makedirs(dst, exist_ok=True)
            rc, tail = _run(["retdec-decompiler", "-o", os.path.join(dst, "out.c"), os.path.join(root, rel)])
            if rc == 0:
                res.update(kind="native-c", src=dst, tool="retdec"); return res
            res["notes"].append("retdec failed: " + tail)
    res["notes"].append("no decompiler available for this app (install ilspycmd for .NET or retdec for native code)")
    return res
