"""Brok-driven source adaptation loop, executed through NX Studio Code's core (conflict-safe patch apply, Safe Run).
Brok only PROPOSES whole-file replacements as JSON; it never writes files or runs commands itself. NX validates paths/sizes, shows the
diff to the supervisor (gate 2), applies with NX Studio Code's patch core, then checks with ALLOWLISTED commands (not model-chosen).
Final artifact assembly is implemented for Electron apps (asar repack). For .NET / native sources the loop edits and checks the recovered
source in the workspace, but no automatic rebuild into the installer exists yet (reported)."""
import json, os, re, struct

from . import studio, supervisor as S

MAX_FILES, MAX_BYTES = 8, 400000
TEXT_EXT = (".js", ".mjs", ".cjs", ".json", ".cs", ".c", ".h", ".cpp")


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


def check(kind, src, saferun, log):
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


def assemble_native_c(dec, saferun):
    """Rebuild the program from the (patched) recovered C with mingw-w64 for Windows 7 and replace the original exe. Decompiler output
    rarely compiles back into a working program; this only reports success when the compiler produced an exe."""
    import shutil
    gcc = shutil.which("i686-w64-mingw32-gcc" if dec.get("arch") == "x86" else "x86_64-w64-mingw32-gcc")
    srcs = [os.path.join(d, f) for d, _, fs in os.walk(dec["src"]) for f in fs if f.endswith(".c")]
    if not gcc or not srcs or not dec.get("exe"):
        return False, "mingw-w64 / sources / original exe missing"
    out = dec["exe"] + ".nxat-new"
    r = saferun.run([gcc, "-O2", "-D_WIN32_WINNT=0x0601", "-Wl,--major-os-version=6", "-Wl,--minor-os-version=1", "-Wl,--major-subsystem-version=6",
                     "-Wl,--minor-subsystem-version=1", "-o", out] + srcs + ["-luser32", "-lgdi32", "-lkernel32", "-ladvapi32", "-lshell32"], timeout=600, no_network=True)
    if r["returncode"] != 0 or not os.path.isfile(out):
        return False, "build failed: " + r["output"][-300:]
    os.replace(out, dec["exe"])
    return True, "rebuilt " + os.path.basename(dec["exe"])


def run(dec, rep, adapter, log=print, rounds=3):
    """dec = decompile() result. -> dict(changed, verified, assembled, notes)."""
    res = {"changed": [], "verified": False, "assembled": False, "notes": []}
    if not dec.get("src"):
        res["notes"].append("no recovered source: Brok/Studio loop skipped"); return res
    patch, saferun, workspace = studio.load()
    src, kind = dec["src"], dec["kind"]
    task = ("Adapt this program's source so it runs on Windows 7 SP1 with Electron 22 / old hardware: replace APIs newer than that, keep behaviour. "
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
        good, feedback = check(kind, src, saferun, log)
        log("  round %d: %d file(s) patched, check %s" % (n, len(plan), "PASS" if good else "FAIL"))
        if good:
            res["verified"] = True; break
    if res["verified"] and kind == "electron-js" and dec.get("asar"):
        write_asar(src, dec["asar"]); res["assembled"] = True
    elif res["verified"] and kind == "native-c":
        ok, msg = assemble_native_c(dec, saferun)
        res["assembled"] = ok; res["notes"].append(msg)
    elif res["verified"]:
        res["notes"].append("source verified in workspace, but automatic rebuild into the installer is not implemented for " + str(kind))
    return res
