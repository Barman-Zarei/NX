"""PE helpers: reading imports and rewriting them so post-Windows-7 APIs resolve to nxshim7.dll (no source code needed)."""
import os, struct, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import check_win7_compat as W7   # single source of truth for the post-Win7 API list
import pefile

SHIM_DLL = "nxshim7.dll"
# APIs nxshim7.dll implements (subset of W7.POST_WIN7). Anything in POST_WIN7 not here cannot be fixed by import redirection.
SHIMMED = {"GetSystemTimePreciseAsFileTime", "SetThreadDescription", "GetThreadDescription", "WaitOnAddress", "WakeByAddressSingle",
           "WakeByAddressAll", "CreateFile2", "GetCurrentPackageFullName", "GetCurrentPackageId", "SetProcessMitigationPolicy",
           "GetDpiForWindow", "GetDpiForSystem", "SetProcessDpiAwarenessContext", "GetSystemMetricsForDpi", "AdjustWindowRectExForDpi",
           "EnableNonClientDpiScaling", "GetAwarenessFromDpiAwarenessContext", "PathCchCanonicalizeEx", "VirtualAlloc2", "MapViewOfFile3",
           "OfferVirtualMemory", "ReclaimVirtualMemory", "GetOverlappedResultEx", "CompareObjectHandles",
           "GetCurrentThreadStackLimits", "IsWow64Process2", "GetProcessMitigationPolicy", "GetThreadInformation", "SetThreadInformation", "GetProcessInformation",
           "SetProcessInformation", "PrefetchVirtualMemory", "DiscardVirtualMemory", "GetThreadDpiAwarenessContext", "GetWindowDpiAwarenessContext",
           "AreDpiAwarenessContextsEqual", "IsValidDpiAwarenessContext", "GetDpiFromDpiAwarenessContext", "GetSystemDpiForProcess", "IsImmersiveProcess",
           "EnableMouseInPointer", "IsMouseInPointerEnabled"}
MACHINE_ARCH = {0x14C: "x86", 0x8664: "x64"}


def _align(v, a):
    return (v + a - 1) // a * a


def read_info(path):
    """-> dict(arch, os, subsystem, imports=[(dll,[names])], delay=[dll], signed, dotnet) or None if not a PE."""
    try:
        pe = pefile.PE(path, fast_load=False)
    except (pefile.PEFormatError, OSError):
        return None
    try:
        o = pe.OPTIONAL_HEADER
        imps = []
        for d in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []):
            imps.append((d.dll.decode("latin1"), [e.name.decode("latin1") for e in d.imports if e.name]))
        delay = [d.dll.decode("latin1") for d in getattr(pe, "DIRECTORY_ENTRY_DELAY_IMPORT", [])]
        dd = o.DATA_DIRECTORY
        return {"arch": MACHINE_ARCH.get(pe.FILE_HEADER.Machine, "other"), "os": (o.MajorOperatingSystemVersion, o.MinorOperatingSystemVersion),
                "subsystem": (o.MajorSubsystemVersion, o.MinorSubsystemVersion), "imports": imps, "delay": delay,
                "signed": dd[4].VirtualAddress != 0 and dd[4].Size != 0, "dotnet": len(dd) > 14 and dd[14].VirtualAddress != 0,
                "dll": bool(pe.FILE_HEADER.Characteristics & 0x2000),
                "sections": [x.Name.rstrip(b"\0").decode("latin1") for x in pe.sections]}
    finally:
        pe.close()


def patch_versions(path, dst=None):
    """Lower OS/subsystem version fields to 6.1. Valid only if the code really does not need newer features (verify by running)."""
    with open(path, "rb") as f:
        data = f.read()
    pe = pefile.PE(data=data, fast_load=True)
    changed = False
    o = pe.OPTIONAL_HEADER
    for maj, mn, want in (("MajorOperatingSystemVersion", "MinorOperatingSystemVersion", (6, 1)), ("MajorSubsystemVersion", "MinorSubsystemVersion", (6, 1))):
        if (getattr(o, maj), getattr(o, mn)) > want:
            setattr(o, maj, want[0]); setattr(o, mn, want[1]); changed = True
    if changed:
        out = pe.write()
        with open(dst or path, "wb") as f:
            f.write(out)
    pe.close()
    return changed


def redirect_imports(path, dst=None, names=None, shim=SHIM_DLL):
    """Make imports of post-Win7 APIs resolve from `shim` instead. Splits import descriptors into runs; the IAT slots stay where the
    code expects them. New import table lives in an appended section. Strips the digital signature (it would be invalid anyway).
    Returns the sorted list of redirected function names ([] and file untouched if nothing to do). Raises ValueError if unsafe."""
    names = set(names or SHIMMED)
    with open(path, "rb") as f:
        raw = f.read()
    pe = pefile.PE(data=raw, fast_load=False)
    o = pe.OPTIONAL_HEADER
    ps = 8 if pe.FILE_HEADER.Machine == 0x8664 else 4
    if pe.FILE_HEADER.Machine not in (0x14C, 0x8664):
        raise ValueError("unsupported machine type")
    fmt = "<Q" if ps == 8 else "<I"
    ordflag = 1 << (ps * 8 - 1)
    dd = o.DATA_DIRECTORY[1]
    if not dd.VirtualAddress:
        return []
    img = pe.get_memory_mapped_image()
    # read all descriptors
    descs, off = [], dd.VirtualAddress
    while True:
        oft, ts, fwd, nm, ft = struct.unpack_from("<IIIII", img, off)
        if not (oft or nm or ft):
            break
        descs.append((oft, ts, fwd, nm, ft)); off += 20
    moved_total, plan = set(), []
    for (oft, ts, fwd, nm, ft) in descs:
        src = oft or ft
        thunks, i = [], 0
        while True:
            v = struct.unpack_from(fmt, img, src + i * ps)[0]
            if v == 0:
                break
            thunks.append(v); i += 1
        flags = []
        for v in thunks:
            hit = False
            if not (v & ordflag):
                nm_ = img[v + 2: img.index(b"\0", v + 2)].decode("latin1")
                hit = nm_ in names
                if hit:
                    moved_total.add(nm_)
            flags.append(hit)
        plan.append((nm, ft, thunks, flags, (oft, ts, fwd)))
    if not moved_total:
        pe.close(); return []
    if o.DATA_DIRECTORY[13].VirtualAddress:
        pass  # delay imports are left alone (reported by analyze)
    # ---- build the new import table blob ----
    shim_b = shim.encode() + b"\0"
    entries = []   # (kind, nameRVA|None, ft_rva, thunks)
    for (nm, ft, thunks, flags, _o) in plan:
        if not any(flags):
            entries.append(("orig", nm, ft, thunks, _o)); continue
        s = 0
        while s < len(thunks):
            e = s
            while e < len(thunks) and flags[e] == flags[s]:
                e += 1
            entries.append(("shim" if flags[s] else "split", nm, ft + s * ps, thunks[s:e], (0, 0, 0)))
            s = e
    ndesc = len(entries) + 1
    blob_desc = ndesc * 20
    int_off, total = [], blob_desc
    for ent in entries:
        int_off.append(total); total += (len(ent[3]) + 1) * ps
    name_off = total; total += len(shim_b)
    # ---- section placement ----
    secs = pe.sections
    last = secs[-1]
    sa, fa = o.SectionAlignment, o.FileAlignment
    new_va = _align(last.VirtualAddress + max(last.Misc_VirtualSize, last.SizeOfRawData), sa)
    sec_table_end = pe.sections[0].get_file_offset() + 40 * len(secs)
    if sec_table_end + 40 > min(s.PointerToRawData for s in secs if s.PointerToRawData):
        raise ValueError("no room in PE headers for another section")
    # data to append after the last section's raw data; drop certificate / overlay beyond sections
    end_raw = max(s.PointerToRawData + s.SizeOfRawData for s in secs)
    body = bytearray(raw[:end_raw])
    new_raw = _align(len(body), fa)
    body += b"\0" * (new_raw - len(body))
    blob = bytearray(total)
    for k, ent in enumerate(entries):
        kind, nm, ft, thunks, (oft0, ts0, fwd0) = ent
        iva = new_va + int_off[k]
        name_rva = nm if kind != "shim" else new_va + name_off
        struct.pack_into("<IIIII", blob, k * 20, iva, 0, 0, name_rva, ft)
        for j, v in enumerate(thunks):
            struct.pack_into(fmt, blob, int_off[k] + j * ps, v)
    blob[name_off:name_off + len(shim_b)] = shim_b
    raw_size = _align(len(blob), fa)
    body += blob + b"\0" * (raw_size - len(blob))
    # ---- section header ----
    hdr = struct.pack("<8sIIIIIIHHI", b".nxat\0\0\0", len(blob), new_va, raw_size, new_raw, 0, 0, 0, 0, 0x40000040)
    body[sec_table_end:sec_table_end + 40] = hdr
    nt = pe.DOS_HEADER.e_lfanew
    struct.pack_into("<H", body, nt + 6, len(secs) + 1)                       # NumberOfSections
    opt = nt + 24
    struct.pack_into("<I", body, opt + 56, new_va + _align(len(blob), sa))    # SizeOfImage
    struct.pack_into("<I", body, opt + 64, 0)                                 # CheckSum (0 = not verified)
    ddo = opt + (112 if ps == 8 else 96)
    struct.pack_into("<II", body, ddo + 8, new_va, blob_desc)                 # import directory
    struct.pack_into("<II", body, ddo + 11 * 8, 0, 0)                         # bound imports (now stale)
    struct.pack_into("<II", body, ddo + 4 * 8, 0, 0)                          # security (signature) removed
    pe.close()
    with open(dst or path, "wb") as f:
        f.write(bytes(body))
    return sorted(moved_total)
