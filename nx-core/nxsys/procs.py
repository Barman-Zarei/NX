"""Feature 41 Process Manager (read side) + protected-process warning; kill requires confirm."""
import os, signal


def list_processes():
    out = []
    for pid in filter(str.isdigit, os.listdir("/proc")):
        try:
            with open("/proc/%s/comm" % pid) as f: name = f.read().strip()
            with open("/proc/%s/statm" % pid) as f: rss = int(f.read().split()[1]) * os.sysconf("SC_PAGE_SIZE") // 1024
            out.append({"pid": int(pid), "name": name, "rss_kib": rss})
        except (OSError, ValueError, IndexError):
            continue
    return sorted(out, key=lambda p: -p["rss_kib"])


PROTECTED = {"systemd", "init", "dbus-daemon", "sshd", "NetworkManager", "Xorg", "gnome-shell"}


def terminate(pid, confirm=False):
    name = next((p["name"] for p in list_processes() if p["pid"] == pid), None)
    if pid in (1, os.getpid()) or name in PROTECTED:
        raise PermissionError("refusing to terminate protected process %s (%s)" % (pid, name))
    if not confirm:
        raise PermissionError("terminate needs confirm=True")
    os.kill(pid, signal.SIGTERM)
