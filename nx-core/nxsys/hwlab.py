"""Feature 4 NX Hardware Lab: reports what the kernel exposes. Reports 'not available' instead of inventing results."""
import os, platform, shutil


def _read(p):
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return None


def report():
    cpu = _read("/proc/cpuinfo") or ""
    mem = _read("/proc/meminfo") or ""
    model = next((l.split(":", 1)[1].strip() for l in cpu.splitlines() if l.startswith("model name")), None)
    mt = next((int(l.split()[1]) for l in mem.splitlines() if l.startswith("MemTotal")), None)
    return {"arch": platform.machine(), "kernel": platform.release(), "cpu_model": model,
            "cpu_threads": os.cpu_count(), "mem_total_mib": mt // 1024 if mt else None,
            "uefi": os.path.isdir("/sys/firmware/efi"), "diagnostics_run": [],
            "note": "inventory only; no component test was executed"}


def block_devices():
    base = "/sys/block"
    out = []
    if os.path.isdir(base):
        for d in sorted(os.listdir(base)):
            if d.startswith(("loop", "ram", "zram")):
                continue
            sz = _read("%s/%s/size" % (base, d))
            out.append({"name": d, "size_gib": round(int(sz) * 512 / 2**30, 1) if sz else None,
                        "removable": (_read("%s/%s/removable" % (base, d)) or "").strip() == "1"})
    return out
