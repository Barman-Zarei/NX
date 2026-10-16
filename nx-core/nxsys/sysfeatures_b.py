"""Features 12,14,15,16,19,20,24,25,26,28,31,33 — headless services. Destructive actions need confirm=True."""
import json, os, re, shutil, subprocess, sys, time
from . import common
from .common import run, tool, require_confirm


# ---- 12 Driver Center: detect, never auto-install ----
def detect_drivers():
    pci = run(["lspci", "-nnk"])
    if not pci["available"]:
        return {"available": False, "reason": "lspci not installed", "devices": []}
    devs, cur = [], None
    for line in pci["out"].splitlines():
        if line and not line.startswith("\t"):
            cur = {"device": line, "driver": None}; devs.append(cur)
        elif "Kernel driver in use:" in line and cur:
            cur["driver"] = line.split(":", 1)[1].strip()
    return {"available": True, "devices": devs,
            "without_driver": [d["device"] for d in devs if not d["driver"]],
            "note": "Detection only. Nothing is installed automatically."}


# ---- 14 Compatibility Center / 19 Hardware Compatibility DB ----
class CompatDB:
    """JSON-backed records. 'verified' only when status source is 'tested'; user reports stay 'unverified'."""
    def __init__(self, path):
        self.path = path
        self.rows = json.load(open(path)) if os.path.exists(path) else []

    def add(self, hardware, nx_version, result, source="user-report", notes=""):
        if source not in ("tested", "user-report"):
            raise ValueError("source must be tested|user-report")
        self.rows.append({"hardware": hardware, "nx": nx_version, "result": result, "source": source,
                          "verified": source == "tested", "notes": notes, "ts": int(time.time())})
        json.dump(self.rows, open(self.path, "w"), ensure_ascii=False)

    def query(self, text, verified_only=False):
        return [r for r in self.rows if text.lower() in r["hardware"].lower() and (r["verified"] or not verified_only)]


def system_requirements(min_ram_mb=1024, min_disk_gb=8, path="/"):
    ram = None
    if os.path.exists("/proc/meminfo"):
        ram = int(re.search(r"MemTotal:\s+(\d+)", open("/proc/meminfo").read()).group(1)) // 1024
    st = os.statvfs(path); disk = st.f_bavail * st.f_frsize / 1e9
    return {"ram_mb": ram, "ram_ok": ram is not None and ram >= min_ram_mb,
            "disk_free_gb": round(disk, 1), "disk_ok": disk >= min_disk_gb}


# ---- 15 Performance Manager (monitor; proposals only) ----
def snapshot():
    load = os.getloadavg() if hasattr(os, "getloadavg") else None
    mem = {}
    if os.path.exists("/proc/meminfo"):
        for l in open("/proc/meminfo"):
            k, v = l.split(":"); mem[k] = int(v.split()[0])
    out = {"load": load, "mem_total_kb": mem.get("MemTotal"), "mem_avail_kb": mem.get("MemAvailable"),
           "cpus": os.cpu_count()}
    out["proposals"] = []
    if load and load[0] > (os.cpu_count() or 1) * 1.5:
        out["proposals"].append("High load average: inspect top processes (no automatic changes made).")
    if mem.get("MemAvailable") and mem["MemAvailable"] < 0.1 * mem.get("MemTotal", 1):
        out["proposals"].append("Low available memory.")
    return out


def startup_time():
    r = run(["systemd-analyze", "time"])
    return r if r["available"] else {"available": False}


# ---- 16 Disk Manager: inspect + guarded plan; execution refuses anything but the chosen target ----
def list_disks():
    r = run(["lsblk", "-J", "-b", "-o", "NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE,RO"])
    if not r["available"]:
        return {"available": False, "disks": []}
    try:
        return {"available": True, "disks": json.loads(r["out"])["blockdevices"]}
    except ValueError:
        return {"available": True, "disks": [], "error": "unparseable lsblk output"}


def plan_format(device, fstype="ext4"):
    disks = {"/dev/" + d["name"]: d for d in list_disks().get("disks", [])}
    d = disks.get(device)
    warnings = []
    if d is None: warnings.append("device not found")
    else:
        mounts = [c.get("mountpoint") for c in d.get("children", []) if c.get("mountpoint")] + ([d["mountpoint"]] if d.get("mountpoint") else [])
        if mounts: warnings.append("mounted: %s" % mounts)
        if d.get("children"): warnings.append("has %d partitions; ALL DATA WOULD BE LOST" % len(d["children"]))
    return {"target": device, "action": "mkfs.%s" % fstype, "warnings": warnings, "blocked": bool(warnings)}


def format_device(device, fstype, typed_confirmation, confirm=False):
    require_confirm(confirm, "format")
    if typed_confirmation != device:
        raise PermissionError("type the exact device path to confirm")
    p = plan_format(device, fstype)
    if p["blocked"]:
        raise PermissionError("refusing: %s" % "; ".join(p["warnings"]))
    return run(["mkfs." + fstype, device], timeout=600)


# ---- 20 Firewall Profiles: generate + preview rules; apply only with confirm ----
PROFILES = {"home": {"incoming": "deny", "allow": ["22/tcp", "5353/udp"]},
            "public": {"incoming": "deny", "allow": []},
            "restricted": {"incoming": "deny", "allow": [], "outgoing": "deny", "out_allow": ["53", "80/tcp", "443/tcp"]}}


def firewall_preview(profile):
    p = PROFILES[profile]
    cmds = ["ufw default %s incoming" % p["incoming"], "ufw default %s outgoing" % p.get("outgoing", "allow")]
    cmds += ["ufw allow %s" % a for a in p["allow"]] + ["ufw allow out %s" % a for a in p.get("out_allow", [])]
    return {"profile": profile, "commands": cmds,
            "effect": "Incoming connections are blocked except: %s" % (", ".join(p["allow"]) or "none")}


def firewall_apply(profile, confirm=False):
    require_confirm(confirm, "firewall change")
    if not tool("ufw"):
        return {"applied": False, "reason": "ufw not installed"}
    res = [run(c.split()) for c in firewall_preview(profile)["commands"]]
    return {"applied": all(r["rc"] == 0 for r in res), "results": [r["rc"] for r in res]}


# ---- 24 App Test Bench: run a real command in isolation when possible ----
def run_app_test(argv, timeout=60, no_network=True):
    argv = list(argv)
    iso = []
    if no_network and tool("unshare") and common.run(["unshare", "-rn", "true"])["rc"] == 0:
        argv = ["unshare", "-rn"] + argv; iso.append("network-namespace")
    r = run(argv, timeout=timeout)
    return {"executed": r["available"], "rc": r["rc"], "out": r["out"][-2000:], "isolation": iso or ["none"],
            "kind": "actual execution"}


# ---- 25 Language Toolkit ----
def locales():
    r = run(["locale", "-a"])
    return {"available": r["available"], "installed": r["out"].split() if r["available"] else [],
            "current": {k: os.environ.get(k) for k in ("LANG", "LC_ALL", "LANGUAGE")}}


def locale_valid(name):
    return name in locales()["installed"]


def set_locale_pref(path, lang, confirm=False):
    """Writes only a per-user preference file (not system config); preserves other keys."""
    require_confirm(confirm, "locale preference")
    d = json.load(open(path)) if os.path.exists(path) else {}
    d["LANG"] = lang
    json.dump(d, open(path, "w"), ensure_ascii=False)
    return d


# ---- 26 Power Manager: detect capability, only claim what exists ----
def power_profiles():
    r = run(["powerprofilesctl", "list"])
    gov = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
    return {"powerprofilesctl": r["available"], "governor": open(gov).read().strip() if os.path.exists(gov) else None,
            "battery": os.path.isdir("/sys/class/power_supply") and any(n.startswith("BAT") for n in os.listdir("/sys/class/power_supply")),
            "note": "Controls are offered only where the kernel/hardware exposes them."}


# ---- 28 Clipboard History: bounded, skips likely secrets, in-memory unless persisted ----
class Clipboard:
    SECRET = re.compile(r"(^sk-[A-Za-z0-9_-]{16,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY)")

    def __init__(self, limit=50):
        self.limit, self.items = limit, []

    def add(self, text, sensitive=False):
        if sensitive or self.SECRET.search(text) or not text.strip():
            return False
        self.items = [t for t in self.items if t != text]
        self.items.insert(0, text); del self.items[self.limit:]
        return True

    def clear(self):
        self.items = []


# ---- 31 Font Manager ----
def list_fonts():
    r = run(["fc-list", ":", "family"])
    return {"available": r["available"], "families": sorted(set(l.split(",")[0] for l in r["out"].splitlines())) if r["available"] else []}


def install_font(src, fonts_dir, confirm=False):
    require_confirm(confirm, "font install")
    if not src.lower().endswith((".ttf", ".otf")):
        raise ValueError("only .ttf/.otf accepted")
    os.makedirs(fonts_dir, exist_ok=True); shutil.copy2(src, fonts_dir)
    run(["fc-cache", "-f", fonts_dir]); return {"installed": os.path.basename(src)}


# ---- 33 Document Center: file-association inspection ----
def default_app(mime):
    r = run(["xdg-mime", "query", "default", mime])
    return {"available": r["available"], "app": r["out"].strip() or None}
