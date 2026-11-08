"""Brok-driven source adaptation loop, executed through NX Studio Code's core (conflict-safe patch apply, Safe Run).
Brok only PROPOSES whole-file replacements as JSON; it never writes files or runs commands itself. NX validates paths/sizes, shows the
diff to the supervisor (gate 2), applies with NX Studio Code's patch core, then checks with ALLOWLISTED commands (not model-chosen).
Final artifact assembly is implemented for Electron apps (asar repack). For .NET / native sources the loop edits and checks the recovered
source in the workspace, but no automatic rebuild into the installer exists yet (reported)."""
import json, os, re, struct, tempfile

from . import studio, supervisor as S

MAX_FILES, MAX_BYTES = 8, 400000
TEXT_EXT = (".js", ".mjs", ".cjs", ".json", ".cs", ".c", ".h", ".cpp", ".py")


def write_asar(src_dir, dst):
    """Pure-python asar writer (no integrity block; Electron 22 accepts that)."""
    files, blobs, off = {}, [], 0
    root = {"files": files}
    for d, dirs, fs in os.walk(src_dir):
        dirs.sort()
        node = root
        rel = os.path.relpath(d, src_dir)
        if rel != ".":
            for part in rel.split(os.sep):
                node = node["files"].setdefault(part, {"files": {}})
        for f in sorted(fs):
            data = open(os.path.join(d, f), "rb").read()
            ent = {"size": len(data), "offset": str(off)}
            if os.access(os.path.join(d, f), os.X_OK):
                ent["executable"] = True
            node["files"][f] = ent; blobs.append(data); off += len(data)
    js = json.dumps(root, separators=(",", ":")).encode()
    pad = (4 - len(js) % 4) % 4
    hdr = struct.pack("<IIII", 4, len(js) + pad + 8, len(js) + pad + 4, len(js)) + js + b"\0" * pad
    with open(dst, "wb") as o:
        o.write(hdr)
        for b in blobs:
            o.write(b)


def _safe_rel(src, rel):
    p = os.path.realpath(os.path.join(src, str(rel)))
    return p.startswith(os.path.realpath(src) + os.sep) and os.path.isfile(p)


def _objects(text):
    """Every JSON object in free text (models add prose / code fences around it). Scans each '{' with raw_decode."""
    dec, out, i = json.JSONDecoder(), [], 0
    text = text or ""
    while True:
        i = text.find("{", i)
        if i < 0:
            return out
        try:
            v, n = dec.raw_decode(text, i)
        except ValueError:
            i += 1; continue
        if isinstance(v, dict):
            out.append(v)
        i += n


def _parse_need(text):
    for v in _objects(text):
        if isinstance(v.get("need"), list) and "edits" not in v:
            return [str(x) for x in v["need"]][:10]
    return []


def parse_edits(text):
    for v in _objects(text):
        if isinstance(v.get("edits"), list):
            return v["edits"][:MAX_FILES], str(v.get("explanation", ""))[:300]
    return [], ""


def _confine(src, rel):
    p = os.path.realpath(os.path.join(src, rel))
    if not p.startswith(os.path.realpath(src) + os.sep) or not rel.lower().endswith(TEXT_EXT):
        raise ValueError("path not allowed: " + rel)
    if not os.path.isfile(p):
        raise ValueError("file does not exist (new files are not accepted): " + rel)
    return p


def _dotnet_refs(dec):
    """-r: for the app's own non-framework dependency DLLs (System.* / Microsoft.* come from Mono's .NET Framework 4 class library)."""
    if not dec or not dec.get("asm"):
        return []
    d = os.path.dirname(dec["asm"])
    return ["-r:" + os.path.join(d, f) for f in sorted(os.listdir(d))
            if f.lower().endswith(".dll") and not f.lower().startswith(("system.", "microsoft.")) and os.path.join(d, f) != dec["asm"]]


def _proc_runner(argv_prefix, timeout=30):
    def run(path):
        import subprocess
        try:
            p = subprocess.Popen(argv_prefix + [path], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            out = p.communicate(input=b"\n", timeout=timeout)[0]
            return p.returncode, out.replace(b"\r\n", b"\n")
        except (OSError, subprocess.TimeoutExpired):
            return None
    return run


def assemble_dotnet(dec, saferun):
    """Compile the (Brok-adapted) C# with mcs into a .NET Framework 4 exe (runs on Windows 7 with .NET Framework 4.x installed), compare its
    behaviour with the original (`dotnet X.dll` vs `mono X.exe`), and only then replace the apphost, X.dll, X.runtimeconfig.json, X.deps.json."""
    import shutil
    mcs, mono, dotnet = shutil.which("mcs"), shutil.which("mono"), shutil.which("dotnet")
    if not mcs:
        return False, "mcs (mono-mcs) missing: not rebuilt"
    srcs = [os.path.join(d, f) for d, _, fs in os.walk(dec["src"]) for f in fs if f.endswith(".cs")]
    new = dec["exe"] + ".nxat-new"
    r = saferun.run([mcs, "-warn:0", "-target:exe", "-out:" + new] + _dotnet_refs(dec) + srcs, timeout=600, no_network=True)
    if r["returncode"] != 0 or not os.path.isfile(new):
        return False, "mcs build failed: " + r["output"][-300:]
    if not (mono and dotnet):
        os.remove(new); return False, "rebuilt .NET Framework exe NOT used: cannot compare behaviour here (needs `mono` and `dotnet`)"
    want, got = _proc_runner([dotnet])(dec["asm"]), _proc_runner([mono])(new)
    if want is None or got is None or want != got:
        os.remove(new)
        return False, "rebuilt .NET exe REJECTED: behaviour differs from the original (original %r vs rebuilt %r)" % (want and want[0], got and got[0])
    os.replace(new, dec["exe"])
    stem = dec["asm"][:-4]
    for ext in (".dll", ".runtimeconfig.json", ".deps.json", ".pdb"):
        if os.path.isfile(stem + ext):
            os.remove(stem + ext)
    return True, "rebuilt as .NET Framework 4 exe with mcs (differential run identical: exit code and output); needs .NET Framework 4.x on Windows 7"


def check(kind, src, saferun, log, dec_for_check=None):
    """Allowlisted verification. -> (ok, output)."""
    import shutil
    bad, out = False, []
    if kind == "electron-js":
        node = shutil.which("node")
        if not node:
            return False, "node not installed: cannot verify JavaScript"
        for d, _, fs in os.walk(src):
            for f in fs:
                if f.endswith((".js", ".cjs", ".mjs")) and "node_modules" not in d:
                    r = saferun.run([node, "--check", os.path.join(d, f)], timeout=60, no_network=True)
                    if r["returncode"] != 0:
                        bad = True; out.append(os.path.relpath(os.path.join(d, f), src) + ": " + r["output"][-300:])
    elif kind == "python-src":
        from . import pyfrozen as PF
        argv = PF.py38_argv()
        if not argv:
            return False, "Python 3.8 not available (python3.8, `uv`, or Wine + Windows Python 3.8): cannot verify"
        for d, _, fs in os.walk(src):
            for f in fs:
                if f.endswith(".py"):
                    p = os.path.join(d, f)
                    if "Decompyle incomplete" in open(p, encoding="utf-8", errors="replace").read():
                        bad = True; out.append(os.path.relpath(p, src) + ": still contains 'Decompyle incomplete' (a function was not recovered - rewrite it using the bytecode listing)"); continue
                    r = saferun.run(argv + ["-m", "py_compile", p], timeout=120, no_network=True)
                    if r["returncode"] != 0:
                        bad = True; out.append(os.path.relpath(p, src) + ": " + r["output"][-300:])
    elif kind == "dotnet-cs":
        mcs = shutil.which("mcs")
        if not mcs:
            return False, "mono's mcs (apt: mono-mcs) not installed: cannot verify C#"
        srcs = [os.path.join(d, f) for d, _, fs in os.walk(src) for f in fs if f.endswith(".cs")]
        r = saferun.run([mcs, "-warn:0", "-nowarn:1591", "-out:" + os.path.join(tempfile.mkdtemp(prefix="nxat_cs_"), "chk.exe")] + _dotnet_refs(dec_for_check) + srcs, timeout=300, no_network=True)
        if r["returncode"] != 0:
            bad = True; out.append(r["output"][-1500:])
    elif kind == "native-c":
        gcc = shutil.which("x86_64-w64-mingw32-gcc")
        if not gcc:
            return False, "mingw-w64 not installed: cannot verify C"
        for d, _, fs in os.walk(src):
            for f in fs:
                if f.endswith(".c"):
                    r = saferun.run([gcc, "-fsyntax-only", "-D_WIN32_WINNT=0x0601", os.path.join(d, f)], timeout=120, no_network=True)
                    if r["returncode"] != 0:
                        bad = True; out.append(f + ": " + r["output"][-300:])
    else:
        return False, "no verifier for " + str(kind)
    return (not bad), "\n".join(out)


def wine_runner(exe, timeout=30):
    """-> (returncode, stdout) of running `exe` with no input under Wine, or None if Wine is not available (cannot verify)."""
    import shutil, subprocess, tempfile
    wine = shutil.which("wine")
    if not wine:
        return None
    env = dict(os.environ, WINEDEBUG="-all")
    cwd = tempfile.mkdtemp(prefix="nxat_run_")
    try:
        p = subprocess.Popen([wine, os.path.abspath(exe)], cwd=cwd, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        out = p.communicate(input=b"\n", timeout=timeout)[0]          # a valid stdin handle: frozen Python apps fail to start under Wine with NUL
        return p.returncode, out.replace(b"\r\n", b"\n")
    except subprocess.TimeoutExpired:
        p.kill(); p.communicate()
        return None          # a program that does not finish by itself (GUI, server) cannot be compared: "unverifiable", never "identical"
    finally:
        import shutil as sh
        sh.rmtree(cwd, ignore_errors=True)


def assemble_native_c(dec, saferun, runner=wine_runner):
    """Rebuild the program from the (patched) recovered C with mingw-w64 (Windows 7 target). Decompiled code is often SILENTLY WRONG (lost
    register arguments, wrong types), so the new exe replaces the original only if a differential run shows the same exit code and output.
    If the behaviour cannot be compared (no Wine / no runner) nothing is replaced."""
    import shutil
    gcc = shutil.which("i686-w64-mingw32-gcc" if dec.get("arch") == "x86" else "x86_64-w64-mingw32-gcc")
    srcs = [os.path.join(d, f) for d, _, fs in os.walk(dec["src"]) for f in fs if f.endswith(".c")]
    if not gcc or not srcs or not dec.get("exe"):
        return False, "mingw-w64 / sources / original exe missing"
    out = dec["exe"] + ".nxat-new"
    from . import cfix
    import tempfile
    work = tempfile.mkdtemp(prefix="nxat_rebuild_")
    flags = ["-D_WIN32_WINNT=0x0601", "-Wl,--major-os-version=6", "-Wl,--minor-os-version=1", "-Wl,--major-subsystem-version=6", "-Wl,--minor-subsystem-version=1"]
    if len(srcs) == 1:                                    # a single RetDec file: deterministic repair first
        tmp = os.path.join(work, "single.c"); shutil.copy2(srcs[0], tmp)
        ok, err = cfix.rebuild(tmp, gcc, out, flags)
        if not ok:
            return False, "rebuild failed after deterministic repair: " + err[-300:]
    else:
        r = saferun.run([gcc, "-w", "-O2", "-o", out] + flags + srcs + ["-luser32", "-lgdi32", "-lkernel32", "-ladvapi32", "-lshell32"], timeout=600, no_network=True)
        if r["returncode"] != 0 or not os.path.isfile(out):
            return False, "build failed: " + r["output"][-300:]
    want = runner(dec["exe"]) if runner else None
    got = runner(out) if runner else None
    if want is None or got is None:
        os.remove(out)
        return False, "rebuilt exe NOT used: cannot verify its behaviour here (needs Wine or another runner)"
    if want != got:
        os.remove(out)
        return False, "rebuilt exe REJECTED: behaviour differs from the original (original %r vs rebuilt %r); decompiled code is not equivalent" % (want[0], got[0])
    os.replace(out, dec["exe"])
    return True, "rebuilt %s (differential run identical: exit code and output)" % os.path.basename(dec["exe"])


def run(dec, rep, adapter, log=print, rounds=3):
    """dec = decompile() result. -> dict(changed, verified, assembled, notes)."""
    res = {"changed": [], "verified": False, "assembled": False, "notes": []}
    if not dec.get("src"):
        res["notes"].append("no recovered source: Brok/Studio loop skipped"); return res
    patch, saferun, workspace = studio.load()
    src, kind = dec["src"], dec["kind"]
    task = ("Adapt this program's source so it runs on Windows 7 SP1 (for Electron: Electron 22; for frozen Python: CPython 3.8, so no match statements, "
            "no str.removeprefix/removesuffix, no PEP 604 'int | None' at runtime, no dict union operators, etc.). Complete any function marked 'Decompyle incomplete' "
            "using its bytecode listing. Replace APIs newer than that target and keep behaviour identical. "
            "Reply with ONE JSON object: {\"edits\":[{\"path\":\"<relative existing file>\",\"new_text\":\"<complete new file text>\"}],\"explanation\":\"...\"}. "
            "At most %d files. Program data follows inside the fence." % MAX_FILES)
    feedback, needed = "", []
    task += ' If you need to see more files first, reply {"need": ["relative/path"]} instead.'
    for n in range(1, rounds + 1):
        files = []
        for d, _, fs in os.walk(src):
            for f in sorted(fs):
                if f.endswith(TEXT_EXT) and "node_modules" not in d:
                    files.append(os.path.join(d, f))
        listing = "\n".join(os.path.relpath(f, src) for f in files[:200])
        body = "FILES:\n" + listing + "\nFINDINGS:\n" + "\n".join(rep.get("fixable", []) + rep.get("notes", [])[:10]) + "\nLAST CHECK OUTPUT:\n" + feedback
        shown, budget = [], 60000
        want = [w for w in needed if _safe_rel(src, w)] + [os.path.relpath(f, src) for f in sorted(files, key=os.path.getsize)]
        for rel in want:
            p = os.path.join(src, rel)
            if rel in shown or not os.path.isfile(p) or os.path.getsize(p) > budget:
                continue
            body += "\n=== FILE %s ===\n%s" % (rel, workspace.read_text(p)); budget -= os.path.getsize(p); shown.append(rel)
            dis = p[:-3] + ".dis.txt" if rel.endswith(".py") else None
            if dis and os.path.isfile(dis) and os.path.getsize(dis) < budget:
                body += "\n=== BYTECODE LISTING of %s (reference only, do not edit; the .py above is incomplete) ===\n%s" % (rel, open(dis, encoding="utf-8", errors="replace").read()); budget -= os.path.getsize(dis)
        st, out = adapter.call("ask", S.wrap(task, body)[0], untrusted=False)
        if st != "ok":
            res["notes"].append("Brok unavailable (%s): stopped" % st); return res
        asked = _parse_need(out)
        if asked:
            needed = asked; feedback = "files you asked for are included now"; res["notes"].append("round %d: Brok asked for %s" % (n, asked)); continue
        edits, why = parse_edits(out)
        if not edits:
            res["notes"].append("round %d: Brok proposed no edits" % n)
            break
        plan, diff_all = [], ""
        try:
            for e in edits:
                p = _confine(src, str(e["path"]))
                new = str(e["new_text"])
                if len(new.encode()) > MAX_BYTES:
                    raise ValueError("edit too large: " + e["path"])
                old = workspace.read_text(p)
                plan.append((p, old, new)); diff_all += patch.diff(old, new, os.path.relpath(p, src).replace(os.sep, "/"))
        except (ValueError, KeyError, TypeError) as ex:
            feedback = "your last answer was rejected: %s" % ex; res["notes"].append("round %d rejected: %s" % (n, ex)); continue
        ok, reason = S.gate_patch(adapter, diff_all, n)
        if not ok:
            res["notes"].append("round %d patch DENIED by supervision: %s" % (n, reason)); return res
        for p, old, new in plan:
            r = patch.apply_to_file(p, old, new)
            if r["applied"]:
                res["changed"].append(os.path.relpath(p, src))
        good, feedback = check(kind, src, saferun, log, dec)
        log("  round %d: %d file(s) patched, check %s" % (n, len(plan), "PASS" if good else "FAIL"))
        if good:
            res["verified"] = True; break
    if res["verified"] and kind == "electron-js" and dec.get("asar"):
        write_asar(src, dec["asar"]); res["assembled"] = True
    elif res["verified"] and kind == "dotnet-cs":
        ok, msg = assemble_dotnet(dec, saferun)
        res["assembled"] = ok; res["notes"].append(msg)
    elif res["verified"] and kind == "python-src":
        from . import pyfrozen as PF
        ok, msg = PF.rebuild(dec, saferun, wine_runner)
        res["assembled"] = ok; res["notes"].append(msg)
    elif res["verified"] and kind == "native-c":
        ok, msg = assemble_native_c(dec, saferun)
        res["assembled"] = ok; res["notes"].append(msg)
    elif res["verified"]:
        res["notes"].append("source verified in workspace, but automatic rebuild into the installer is not implemented for " + str(kind))
    return res
