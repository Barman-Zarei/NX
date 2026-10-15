"""Feature 17 NX Install Preflight: checks only, never modifies disks. Each check returns pass/warn/fail + evidence."""
import os, shutil, socket
from . import hwlab

MIN_RAM_MIB, MIN_DISK_GIB = 1024, 8


def run(target_dir="/", min_ram_mib=MIN_RAM_MIB, min_disk_gib=MIN_DISK_GIB, check_network=True):
    r = []
    mem = hwlab.report()["mem_total_mib"]
    r.append(("ram", "pass" if mem and mem >= min_ram_mib else "fail", "%s MiB (need %d)" % (mem, min_ram_mib)))
    free = shutil.disk_usage(target_dir).free / 2**30
    r.append(("disk_space", "pass" if free >= min_disk_gib else "fail", "%.1f GiB free at %s (need %d)" % (free, target_dir, min_disk_gib)))
    r.append(("firmware", "pass", "UEFI" if os.path.isdir("/sys/firmware/efi") else "BIOS/legacy"))
    if check_network:
        try:
            socket.create_connection(("archive.ubuntu.com", 80), timeout=3).close(); r.append(("network", "pass", "archive.ubuntu.com:80 reachable"))
        except OSError as e:
            r.append(("network", "warn", "not reachable: %s (offline install possible)" % e))
    r.append(("data_loss_notice", "warn", "installer may erase the selected target; this preflight changed nothing"))
    return {"checks": r, "ok": not any(s == "fail" for _, s, _ in r)}
