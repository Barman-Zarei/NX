"""Features 29,30,34,35,36,37,38,39,40,43,44,45,46,47,48,49 — wrappers over real system tools.
Hardware/desktop dependent features report 'available': False instead of pretending."""
import json, os, re, shutil, subprocess, time
from . import common
from .common import run, tool, require_confirm


def _cap(*names):
    return {n: bool(tool(n)) for n in names}


# ---- 29 Screenshot Studio / 46 Screen Recorder ----
def screenshot(path):
    for argv in (["grim", path], ["gnome-screenshot", "-f", path], ["scrot", path], ["import", "-window", "root", path]):
        if tool(argv[0]):
            r = run(argv, timeout=20)
            if r["rc"] == 0 and os.path.exists(path):
                return {"ok": True, "tool": argv[0], "path": path, "size": os.path.getsize(path)}
    return {"ok": False, "reason": "no screenshot tool usable (needs a display + one of grim/gnome-screenshot/scrot/imagemagick)"}


def record_command(path, seconds=5, audio=False):
    """Returns the ffmpeg command; does not start recording without an explicit start() call by the caller."""
    if not tool("ffmpeg"):
        return {"available": False, "reason": "ffmpeg not installed"}
    display = os.environ.get("DISPLAY")
    if not display:
        return {"available": False, "reason": "no X display"}
    cmd = ["ffmpeg", "-y", "-f", "x11grab", "-t", str(seconds), "-i", display, path]
    return {"available": True, "argv": cmd, "audio": audio, "note": "microphone is not captured unless audio=True is passed by the user"}


# ---- 30 Notification Center: history log + real delivery via notify-send ----
class Notifications:
    def __init__(self, path):
        self.path = path

    def send(self, title, body="", deliver=True):
        entry = {"ts": int(time.time()), "title": title, "body": body, "delivered": False}
        if deliver and tool("notify-send") and os.environ.get("DBUS_SESSION_BUS_ADDRESS"):
            entry["delivered"] = run(["notify-send", title, body])["rc"] == 0
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry

    def history(self, n=50):
        if not os.path.exists(self.path): return []
        return [json.loads(l) for l in open(self.path, encoding="utf-8")][-n:]


# ---- 34 Audio / 35 Display / 37 Night Light: parse real tool output where present ----
def audio_sinks():
    r = run(["pactl", "list", "short", "sinks"])
    return {"available": r["available"] and r["rc"] == 0,
            "sinks": [l.split("\t")[1] for l in r["out"].splitlines() if "\t" in l]}


def set_volume(sink, percent, confirm=True):
    if not 0 <= percent <= 150: raise ValueError("percent out of range")
    return run(["pactl", "set-sink-volume", sink, "%d%%" % percent])


def displays():
    r = run(["xrandr", "--query"])
    if not r["available"] or r["rc"] != 0:
        return {"available": False, "reason": r["err"][:100] or "no display"}
    return {"available": True, "outputs": [l.split()[0] for l in r["out"].splitlines() if " connected" in l]}


def night_light_cmd(kelvin):
    if not 1000 <= kelvin <= 6500: raise ValueError("kelvin must be 1000-6500")
    return {"gammastep": ["gammastep", "-O", str(kelvin)], "redshift": ["redshift", "-O", str(kelvin)],
            "available": _cap("gammastep", "redshift")}


# ---- 36 Device Pairing (Bluetooth via bluetoothctl) / 49 USB ----
def bluetooth_devices():
    r = run(["bluetoothctl", "devices"])
    return {"available": r["available"], "devices": [l for l in r["out"].splitlines() if l.startswith("Device")]}


def pair(mac, confirm=False):
    require_confirm(confirm, "pairing")
    if not re.fullmatch(r"([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}", mac): raise ValueError("bad MAC")
    return run(["bluetoothctl", "pair", mac], timeout=60)


def usb_devices():
    r = run(["lsusb"])
    if r["available"]:
        return {"available": True, "devices": r["out"].splitlines()}
    root = "/sys/bus/usb/devices"
    if os.path.isdir(root):
        out = []
        for d in sorted(os.listdir(root)):
            p = os.path.join(root, d, "product")
            if os.path.exists(p): out.append("%s %s" % (d, open(p).read().strip()))
        return {"available": True, "devices": out, "source": "sysfs"}
    return {"available": False, "devices": []}


def safe_to_eject(device):
    """Refuses system/boot disks."""
    mounts = open("/proc/mounts").read() if os.path.exists("/proc/mounts") else ""
    system = any(l.split()[0].startswith(device) and l.split()[1] in ("/", "/boot", "/boot/efi") for l in mounts.splitlines() if l.strip())
    return {"device": device, "allowed": not system, "reason": "hosts / or /boot" if system else ""}


# ---- 38 Password Vault: AES-256-CBC + PBKDF2 via openssl; passphrase via env, never argv/plaintext file ----
class Vault:
    def __init__(self, path):
        self.path = path

    def _openssl(self, mode, data, pw):
        if not tool("openssl"):
            raise RuntimeError("openssl not installed")
        env = dict(os.environ, NXV_PW=pw)
        p = subprocess.run(["openssl", "enc", mode, "-aes-256-cbc", "-pbkdf2", "-iter", "200000", "-salt",
                            "-pass", "env:NXV_PW", "-a"], input=data, capture_output=True, env=env)
        if p.returncode: raise ValueError("wrong passphrase or corrupted vault")
        return p.stdout

    def save(self, entries, passphrase):
        blob = self._openssl("-e", json.dumps(entries).encode(), passphrase)
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "wb") as f: f.write(blob)

    def load(self, passphrase):
        return json.loads(self._openssl("-d", open(self.path, "rb").read(), passphrase).decode())


# ---- 39 Privacy Dashboard: what is actually inspectable ----
def privacy_report():
    cam = [p for p in os.listdir("/dev") if p.startswith("video")] if os.path.isdir("/dev") else []
    mic = os.path.exists("/proc/asound/cards")
    return {"camera_devices": cam, "audio_capture_possible": mic,
            "location_service": bool(tool("geoclue")) or os.path.exists("/usr/libexec/geoclue"),
            "note": "Per-application access is not tracked by this tool; lists device availability only."}


# ---- 40 Task Scheduler: user crontab via real crontab binary ----
def list_tasks():
    r = run(["crontab", "-l"])
    return {"available": r["available"], "tasks": [l for l in r["out"].splitlines() if l and not l.startswith("#")]}


def add_task(schedule, command, confirm=False):
    require_confirm(confirm, "scheduling a task")
    if not re.fullmatch(r"[\d*/,\- ]{9,}", schedule): raise ValueError("invalid cron schedule")
    cur = run(["crontab", "-l"])["out"] if tool("crontab") else ""
    new = cur.rstrip("\n") + ("\n" if cur.strip() else "") + "%s %s\n" % (schedule, command)
    return run(["crontab", "-"], input_text=new)


# ---- 43 Secure Delete Guide: honest guidance by storage type ----
def secure_delete_advice(path):
    r = run(["findmnt", "-n", "-o", "FSTYPE", "-T", path])
    fs = r["out"].strip() or "unknown"
    cow = fs in ("btrfs", "zfs", "xfs") or fs.startswith("overlay")
    rotational = None
    return {"filesystem": fs, "guarantee": False,
            "advice": ["Overwriting (shred) is unreliable on SSDs, snapshots and copy-on-write filesystems."]
                      + (["%s is copy-on-write/overlay: overwrite will not reach old blocks." % fs] if cow else [])
                      + ["For real erasure use full-disk encryption + destroy the key, or the drive's ATA secure-erase/crypto-erase."]}


# ---- 44 Web Apps: .desktop launcher that opens a URL in the browser (a wrapper, not a native app) ----
def create_webapp(name, url, apps_dir):
    if not re.match(r"^https?://", url): raise ValueError("only http(s) URLs")
    if re.search(r"[\n\r]", name): raise ValueError("bad name")
    os.makedirs(apps_dir, exist_ok=True)
    path = os.path.join(apps_dir, "nx-webapp-%s.desktop" % re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-").lower())
    open(path, "w", encoding="utf-8").write("[Desktop Entry]\nType=Application\nName=%s (web)\nExec=xdg-open %s\nTerminal=false\nCategories=Network;\n" % (name, url))
    return path


# ---- 45 Game Mode: only reversible, non-security changes; reports what it can set ----
def game_mode_plan():
    gov = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
    return {"actions": (["set CPU governor to 'performance' (reversible)"] if os.path.exists(gov) else []) + ["pause notifications"],
            "never_touches": ["firewall", "updates", "security services"], "fps_claims": "none"}


# ---- 47 Share Sheet: lists real targets ----
def share_targets():
    return {"email": bool(tool("xdg-email")), "bluetooth": bool(tool("bluetooth-sendto") or tool("bluetoothctl")),
            "files": True, "scp": bool(tool("scp"))}


def share_email(path, to):
    if not os.path.isfile(path): raise FileNotFoundError(path)
    return ["xdg-email", "--attach", path, to]


# ---- 48 Accessibility Toolkit: real gsettings keys where GNOME exists; otherwise reports unavailable ----
A11Y_KEYS = {"high_contrast": ("org.gnome.desktop.a11y.interface", "high-contrast"),
             "large_text": ("org.gnome.desktop.interface", "text-scaling-factor"),
             "screen_reader": ("org.gnome.desktop.a11y.applications", "screen-reader-enabled")}


def a11y_status():
    if not tool("gsettings"): return {"available": False}
    out = {}
    for k, (s, key) in A11Y_KEYS.items():
        r = run(["gsettings", "get", s, key]); out[k] = r["out"].strip() if r["rc"] == 0 else None
    return {"available": True, "settings": out}
