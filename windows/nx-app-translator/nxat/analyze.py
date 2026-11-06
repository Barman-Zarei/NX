"""Scan an app folder and classify what keeps it from running on Windows 7 SP1, and what can be fixed automatically."""
import json, os, re
from . import peutil as P

ELECTRON_WIN7_MAX = 22      # Electron 23+ dropped Windows 7
PY_WIN7_MAX = (3, 8)        # CPython 3.9+ dropped Windows 7
DOTNET_WIN7_MAX = 6         # .NET 7+ dropped Windows 7 (6 is out of support but runs)


def _electron_version(root):
    """Electron distributions contain a `version` file next to the exe, plus resources/ and icudtl.dat or ffmpeg.dll."""
    for d, _, fs in os.walk(root):
        low = [x.lower() for x in fs]
        if "version" in low and ("icudtl.dat" in low or "ffmpeg.dll" in low) and os.path.isdir(os.path.join(d, "resources")):
            try:
                t = open(os.path.join(d, fs[low.index("version")]), errors="ignore").read(40).strip()
            except OSError:
                continue
            m = re.match(r"^v?(\d+)\.\d+\.\d+", t)
            if m:
                return int(m.group(1)), d
    return None, None


def analyze(root):
    """-> report dict: {pe: {relpath: info}, blockers, fixable, notes, kind}."""
    rep = {"root": root, "files": 0, "pe": {}, "kinds": [], "fixable": [], "blockers": [], "notes": []}
    ev, edir = _electron_version(root)
    if ev:
        rep["kinds"].append("electron")
        rep["electron"] = {"major": ev, "dir": os.path.relpath(edir, root)}
        if ev > ELECTRON_WIN7_MAX:
            rep["fixable"].append("electron-swap: runtime %d -> 22.3.27 (last Win7 build); JS code must not use APIs newer than Electron 22" % ev)
    for d, _, fs in os.walk(root):
        for f in fs:
            p = os.path.join(d, f); rel = os.path.relpath(p, root); rep["files"] += 1
            low = f.lower()
            if low.endswith(".node"):
                rep["notes"].append("native Node module %s: must be rebuilt for Electron 22 ABI (not done automatically)" % rel)
            if low.endswith(".runtimeconfig.json"):
                try:
                    fw = json.load(open(p)).get("runtimeOptions", {}).get("framework", {})
                    v = int(str(fw.get("version", "0")).split(".")[0])
                    rep["kinds"].append("dotnet-core")
                    if v > DOTNET_WIN7_MAX and "NETCore" in fw.get("name", ""):
                        rep["blockers"].append("%s targets .NET %d (no Windows 7 support); rebuild from source for net6.0 or older" % (rel, v))
                except (ValueError, OSError):
                    pass
            m = re.match(r"^python3(\d+)\.dll$", low)
            if m:
                rep["kinds"].append("python-frozen")
                if (3, int(m.group(1))) > PY_WIN7_MAX:
                    rep["blockers"].append("frozen Python 3.%s (%s): Python 3.9+ does not run on Windows 7; app must be re-frozen with 3.8" % (m.group(1), rel))
            if not low.endswith((".exe", ".dll", ".pyd", ".node", ".ocx", ".sys")):
                continue
            info = P.read_info(p)
            if not info:
                continue
            imp = [n for dll, ns in info["imports"] if dll.lower() != P.SHIM_DLL for n in ns]
            viol = P.W7.violations(info["os"], info["subsystem"], imp)
            post = sorted(set(imp) & P.W7.POST_WIN7)
            info["post_win7"] = post
            info["unshimmable"] = [n for n in post if n not in P.SHIMMED]
            info["violations"] = viol
            info["path"] = rel
            rep["pe"][rel] = info
            if info["dotnet"] and "dotnet-fw" not in rep["kinds"]:
                rep["kinds"].append("dotnet-fw-or-core")
            if info["delay"] and viol:
                rep["notes"].append("%s has delay-load imports (not rewritten)" % rel)
            if info["unshimmable"]:
                rep["blockers"].append("%s imports %s: no shim available" % (rel, ", ".join(info["unshimmable"])))
            if info["arch"] == "other":
                rep["notes"].append("%s: unsupported architecture" % rel)
    need = [r for r, i in rep["pe"].items() if i["violations"]]
    if need:
        rep["fixable"].append("pe-patch: %d binaries (version fields / import redirection to nxshim7.dll)" % len(need))
    rep["kinds"] = sorted(set(rep["kinds"]))
    rep["compatible_now"] = not need and not rep["blockers"] and not any(f.startswith("electron-swap") for f in rep["fixable"])
    return rep
