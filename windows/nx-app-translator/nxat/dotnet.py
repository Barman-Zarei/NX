"""EXPERIMENTAL .NET (Core / 5+) downgrade for Windows 7: .NET 7+ cannot run on Windows 7, .NET 6 can.
We re-point AssemblyRef versions of System.*/Microsoft.* (> 6.0) to 6.0.0.0 and set the runtimeconfig framework to 6.0.0.
This works only if the program really uses nothing newer than .NET 6 APIs: that is NOT verified (no source, no .NET runtime here).
.NET Framework apps (mscorlib references) already run on Windows 7 SP1 up to 4.8 and are left alone. Needs `dnfile` (pure Python)."""
import json, os, struct

try:
    import dnfile
except ImportError:      # analysis degrades to "cannot inspect"
    dnfile = None

MAX_WIN7_MAJOR = 6


def refs(path):
    """-> [(name, (maj, min, build, rev), offset_of_version_fields)] or None if not a managed assembly / dnfile missing."""
    if dnfile is None:
        return None
    try:
        dn = dnfile.dnPE(path)
        rows = dn.net.mdtables.AssemblyRef.rows
    except Exception:
        return None
    out = []
    for r in rows:
        off = r.struct.get_field_absolute_offset("MajorVersion")
        out.append((str(r.Name), (r.MajorVersion, r.MinorVersion, r.BuildNumber, r.RevisionNumber), off))
    return out


def is_framework(rs):
    return bool(rs) and any(n == "mscorlib" for n, _, _ in rs)


def needs_downgrade(rs):
    return [n for n, v, _ in (rs or []) if (n.startswith("System") or n.startswith("Microsoft")) and v[0] > MAX_WIN7_MAJOR]


def retarget_refs(path):
    """Patch in place. Returns the list of re-pointed reference names."""
    rs = refs(path)
    if not rs:
        return []
    with open(path, "r+b") as f:
        data = f.read()
        done = []
        for n, v, off in rs:
            if (n.startswith("System") or n.startswith("Microsoft")) and v[0] > MAX_WIN7_MAJOR:
                if struct.unpack_from("<4H", data, off) != v:
                    raise ValueError("unexpected metadata layout in " + path)
                f.seek(off); f.write(struct.pack("<4H", 6, 0, 0, 0)); done.append(n)
    return done


def retarget_runtimeconfig(path):
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
    fw = cfg.get("runtimeOptions", {}).get("framework", {})
    frameworks = [fw] if fw else cfg.get("runtimeOptions", {}).get("frameworks", [])
    changed = False
    for x in frameworks:
        try:
            major = int(str(x.get("version", "0")).split(".")[0])
        except ValueError:
            continue
        if major > MAX_WIN7_MAJOR and "NETCore" in x.get("name", ""):
            x["version"] = "6.0.0"; changed = True
    if changed:
        cfg["runtimeOptions"].setdefault("rollForward", "LatestPatch")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    return changed
