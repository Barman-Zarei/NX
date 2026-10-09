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


def violations(os_ver, subsys_ver, imports):
    out = []
    if tuple(os_ver) > WIN7:
        out.append("MajorOS/MinorOS version %d.%d > 6.1" % tuple(os_ver))
    if tuple(subsys_ver) > WIN7:
        out.append("subsystem version %d.%d > 6.1" % tuple(subsys_ver))
    bad = sorted(set(imports) & POST_WIN7)
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
            imps = [e.name.decode() for ent in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []) for e in ent.imports if e.name]
            v = violations((o.MajorOperatingSystemVersion, o.MinorOperatingSystemVersion),
                           (o.MajorSubsystemVersion, o.MinorSubsystemVersion), imps)
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
