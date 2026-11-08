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
# Types that first appeared in .NET 7 / 8 / 9 (TypeRef names). A program referencing one cannot run on .NET 6 by re-pointing references.
POST6_TYPES = {"TimeProvider", "FrozenDictionary`2", "FrozenSet`1", "SearchValues", "SearchValues`1", "CompositeFormat", "UnreachableException",
               "GeneratedRegexAttribute", "LibraryImportAttribute", "IAdditionOperators`3", "INumber`1", "INumberBase`1", "IBinaryInteger`1",
               "IUtf8SpanFormattable", "Lock", "TarFile", "TarReader", "TarWriter", "StringSyntaxAttribute", "NonCryptographicHashAlgorithm",
               "IUtf8SpanParsable`1", "ISpanParsable`1", "IParsable`1", "IShiftOperators`3", "IMinMaxValue`1", "IFloatingPoint`1", "BinaryInteger"}


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


def post6_types(path):
    """Names of known post-.NET-6 types referenced by the assembly (TypeRef table). [] if none / cannot inspect."""
    if dnfile is None:
        return []
    try:
        dn = dnfile.dnPE(path)
        rows = dn.net.mdtables.TypeRef.rows
    except Exception:
        return []
    return sorted({str(r.TypeName) for r in rows if str(r.TypeName) in POST6_TYPES})


def find_nxdecompile():
    here = os.path.dirname(os.path.abspath(__file__))
    for c in (os.environ.get("NXAT_NXDECOMPILE", ""), os.path.join(here, "..", "tools", "nxdecompile", "bin", "NxDecompile.dll"),
              os.path.join(os.path.expanduser("~"), ".local", "share", "nx", "nxdecompile", "NxDecompile.dll"), "/usr/lib/nx/nxdecompile/NxDecompile.dll"):
        if c and os.path.isfile(c):
            return os.path.abspath(c)
    return None


CLEANUPS = ((r"^\[module: RefSafetyRules\(\d+\)\]\s*$", ""), (r"^\[assembly: TargetFramework\([^\n]*\)\]\s*$", ""),
            (r"^\[assembly: CompilationRelaxations\([^\n]*\)\]\s*$", ""), (r"<Main>\$", "Main"))


def clean_decompiled(text):
    """Deterministic fixes for things mcs (C# 7, Mono) cannot compile: net8-only assembly attributes and the top-level-statement entry name."""
    import re
    for pat, rep in CLEANUPS:
        text = re.sub(pat, rep, text, flags=re.M)
    return text
