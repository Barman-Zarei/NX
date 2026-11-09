"""Static Windows 7 compatibility check for built binaries (PE files). usage: check_win7_compat.py DIR
Fails (exit 1) if any .exe/.dll/.pyd declares a minimum OS/subsystem version above 6.1 (Windows 7) or statically imports an API that
does not exist on Windows 7 SP1. This is a STATIC PROXY: it cannot prove the program runs on Windows 7 (use windows/win7-smoke-test.bat there)."""
import os
import sys

WIN7 = (6, 1)
# APIs introduced after Windows 7 (kernel32/user32/etc.). Static imports of these break loading on Windows 7.
POST_WIN7 = {
    "GetSystemTimePreciseAsFileTime", "SetThreadDescription", "GetThreadDescription", "WaitOnAddress", "WakeByAddressSingle",
    "WakeByAddressAll", "CreateFile2", "GetCurrentPackageFullName", "GetCurrentPackageId", "SetProcessMitigationPolicy",
    "GetDpiForWindow", "GetDpiForSystem", "SetProcessDpiAwarenessContext", "GetSystemMetricsForDpi", "AdjustWindowRectExForDpi",
    "EnableNonClientDpiScaling", "GetAwarenessFromDpiAwarenessContext", "PathCchCanonicalizeEx", "VirtualAlloc2", "MapViewOfFile3",
    "OfferVirtualMemory", "ReclaimVirtualMemory", "GetOverlappedResultEx", "CompareObjectHandles",
}


_TABLE = None


def table():
    """{dll: {function: minimum OS}} for every Win32 function newer than Windows 7 (built by nx-app-translator/tools/build_api_table.py from
    the win32json metadata). Empty if the data file is absent (then only POST_WIN7 above is used)."""
    global _TABLE
    if _TABLE is None:
        import json
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nx-app-translator", "nxat", "data", "win7_missing_apis.json")
        try:
            _TABLE = json.load(open(p))
        except (OSError, ValueError):
            _TABLE = {}
    return _TABLE


def newer_than_win7(pairs):
    """pairs = [(dll_name, function)] -> sorted function names that do not exist on Windows 7. api-ms-win-* contract DLLs are matched by function name."""
    t, out = table(), set()
    allnames = None
    for dll, name in pairs:
        key = dll.lower()[:-4] if dll.lower().endswith(".dll") else dll.lower()
        if name in t.get(key, {}):
            out.add(name)
        elif key.startswith("api-ms-win-") or key.startswith("ext-ms-win-"):
            if allnames is None:
                allnames = {n for d in t.values() for n in d}
            if name in allnames:
                out.add(name)
    return sorted(out)


def violations(os_ver, subsys_ver, imports, pairs=None):
    out = []
    if tuple(os_ver) > WIN7:
        out.append("MajorOS/MinorOS version %d.%d > 6.1" % tuple(os_ver))
    if tuple(subsys_ver) > WIN7:
        out.append("subsystem version %d.%d > 6.1" % tuple(subsys_ver))
    bad = sorted((set(imports) & POST_WIN7) | set(newer_than_win7(pairs or [])))
    if bad:
        out.append("static imports not available on Windows 7: " + ", ".join(bad))
    return out


def scan(root):
    import pefile
    bad = {}
    n = 0
    for d, _, files in os.walk(root):
        for f in files:
            if not f.lower().endswith((".exe", ".dll", ".pyd")):
                continue
            p = os.path.join(d, f)
            try:
                pe = pefile.PE(p, fast_load=False)
            except pefile.PEFormatError:
                continue
            n += 1
            o = pe.OPTIONAL_HEADER
            pairs = [(ent.dll.decode("latin1"), e.name.decode()) for ent in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []) for e in ent.imports if e.name]
            imps = [n for _, n in pairs]
            v = violations((o.MajorOperatingSystemVersion, o.MinorOperatingSystemVersion),
                           (o.MajorSubsystemVersion, o.MinorSubsystemVersion), imps, pairs)
            if v:
                bad[p] = v
            if f.lower().startswith(("msvcp140", "vcruntime140", "python3", "qt5core")):
                info = {s.name: s for s in []}
                print("runtime:", f, "file version", getattr(pe, "FileInfo", None) and "see pefile" or "n/a")
    print("scanned %d binaries" % n)
    return bad


if __name__ == "__main__":
    b = scan(sys.argv[1])
    for p, v in b.items():
        print("INCOMPATIBLE:", p, "; ".join(v))
    sys.exit(1 if b else 0)
