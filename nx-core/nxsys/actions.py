"""Declarative action registry behind the NX Control Center GUI.
Each feature (1-49) has >=1 Action(label, fn, params, danger). `danger=True` means: changes the system or user data;
the GUI requires an explicit confirmation and the executor passes confirm=True ONLY then.
Param = (name, kind, default, label); kinds: str, int, bool, path, secret, choice:a|b|c"""
import json, os, shlex, subprocess, sys
from . import (hwlab, storage, startup, procs, netdiag, preflight, bugreport, power, archive,
               sysfeatures_a as A, sysfeatures_b as B, sysfeatures_c as C)

H = os.path.expanduser("~")
CFG = os.path.join(H, ".config", "nx")
DATA = os.path.join(H, ".local", "share", "nx")


class Action:
    def __init__(self, label, fn, params=(), danger=False, help=""):
        self.label, self.fn, self.params, self.danger, self.help = label, fn, tuple(params), danger, help


def P(name, kind="str", default="", label=None):
    return (name, kind, default, label or name)


def convert(kind, raw):
    if kind == "int":
        return int(raw)
    if kind == "bool":
        return bool(raw)
    return raw


_clip = B.Clipboard()


def _clip_add(text):
    return {"added": _clip.add(text), "history": list(_clip.items), "note": "secret-looking text is refused"}


def _repair_first(confirm=False):
    for f in A.diagnose():
        if f.get("repair"):
            return A.repair(f, confirm=confirm)
    return {"ran": False, "reason": "nothing repairable found"}


def _offline_pack(packages, dest):
    r = A.offline_pack([p.strip() for p in packages.split(",") if p.strip()], dest)
    if r.get("ok"):
        json.dump(r["files"], open(os.path.join(dest, "manifest.json"), "w"))
    return r


def _verify_pack(dest):
    return A.verify_pack(dest, json.load(open(os.path.join(dest, "manifest.json"))))


def _compat_add(db, hardware, nx_version, result, source):
    B.CompatDB(db).add(hardware, nx_version, result, source=source); return {"saved": True}


def _compat_query(db, text, verified_only):
    return B.CompatDB(db).query(text, verified_only=verified_only)


def _vault_put(path, passphrase, site, user, password):
    v = C.Vault(path)
    try:
        data = v.load(passphrase) if os.path.exists(path) else {}
    except ValueError:
        return {"error": "wrong passphrase for existing vault; nothing written"}
    data[site] = {"user": user, "pw": password}
    v.save(data, passphrase); return {"saved": site, "sites": sorted(data)}


def _vault_get(path, passphrase, site, reveal):
    try:
        d = C.Vault(path).load(passphrase)
    except (ValueError, OSError) as e:
        return {"error": str(e)}
    if not site:
        return {"sites": sorted(d)}
    e = d.get(site)
    if e is None: return {"error": "no such site"}
    return {"site": site, "user": e["user"], "password": e["pw"] if reveal else "••••••••"}


def _notify(title, body):
    return C.Notifications(os.path.join(DATA, "notifications.log")).send(title, body)


def _notify_hist():
    return C.Notifications(os.path.join(DATA, "notifications.log")).history()


def _app_test(command, timeout):
    return B.run_app_test(shlex.split(command), timeout=timeout)


def _zip(zpath, files, base):
    archive.create_zip(zpath, [f.strip() for f in files.split(",") if f.strip()], base); return {"created": zpath}


def _extract(path, dest):
    return archive.extract(path, dest)


def _lang(path, lang, confirm=False):
    return B.set_locale_pref(path, lang, confirm=confirm)


def _easy(path, mode):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return A.set_mode(path, mode)


def _code_studio(root):
    here = os.path.dirname(os.path.abspath(__file__))
    cs = os.path.join(os.path.dirname(os.path.dirname(here)), "code-studio")
    env = dict(os.environ, PYTHONPATH=cs)
    pr = subprocess.Popen([sys.executable, "-m", "nxcs.gui", root], env=env, cwd=cs)
    return {"started_pid": pr.pid}


def _chmod(path, mode, confirm=False):
    A.set_mode_path(path, int(mode, 8), confirm=confirm); return {"chmod": path, "mode": mode}


def _mig_apply(src, dst, confirm=False):
    return A.migrate_apply(src, dst, confirm=confirm)


def _restore(archive_path, dest, sha256, confirm=False):
    return A.restore(archive_path, dest, expected_sha256=sha256 or None, confirm=confirm)


def _format(device, fstype, typed, confirm=False):
    r = B.format_device(device, fstype, typed, confirm=confirm); return {"rc": r["rc"], "err": r["err"][:300]}


def _fw_apply(profile, confirm=False):
    return B.firewall_apply(profile, confirm=confirm)


def _disable(name, user_dir, confirm=False):
    if not confirm: raise PermissionError("needs confirm=True")
    return startup.disable(name, user_dir)


def _terminate(pid, confirm=False):
    return procs.terminate(pid, confirm=confirm)


def _fontinst(src, fonts_dir, confirm=False):
    return B.install_font(src, fonts_dir, confirm=confirm)


def _pair(mac, confirm=False):
    r = C.pair(mac, confirm=confirm); return {"rc": r["rc"], "out": r["out"][-300:]}


def _addtask(schedule, command, confirm=False):
    r = C.add_task(schedule, command, confirm=confirm); return {"rc": r["rc"], "err": r["err"][:200]}


def _setvol(sink, percent):
    r = C.set_volume(sink, percent); return {"rc": r["rc"], "err": r["err"][:200]}


R = {
 1: [Action("Diagnose", A.diagnose, [P("root", "path", "/", "Filesystem root")]),
     Action("Repair first fixable problem (dpkg --configure -a)", _repair_first, [], True, "Runs one allow-listed repair as root-capable user")],
 2: [Action("Validate recovery readiness", A.validate_recovery, [P("grub_cfg", "path", "/boot/grub/grub.cfg"), P("iso_dir", "path", "/boot")]),
     Action("Show rescue plan (prints commands only)", A.rescue_plan, [P("root_dev", "str", "/dev/sdXN")])],
 3: [Action("Download packages for offline use", _offline_pack, [P("packages", "str", "htop"), P("dest", "path", os.path.join(DATA, "offline-pack"))]),
     Action("Verify pack against manifest.json", _verify_pack, [P("dest", "path", os.path.join(DATA, "offline-pack"))])],
 4: [Action("Hardware report", hwlab.report), Action("Block devices", hwlab.block_devices)],
 5: [Action("Set Easy / Advanced mode", _easy, [P("path", "path", os.path.join(CFG, "settings.json")), P("mode", "choice:easy|advanced", "easy")])],
 6: [Action("Inspect a .deb", A.inspect_deb, [P("path", "path", "")])],
 7: [Action("Preview updates (no rollback available)", A.preview_updates)],
 8: [Action("Permission map", A.permission_map, [P("root", "path", "/etc"), P("limit", "int", 50)]),
     Action("chmod", _chmod, [P("path", "path", ""), P("mode", "str", "600", "Octal mode")], True)],
 9: [Action("Developer tools status", A.devkit_status), Action("Create virtualenv", A.create_venv, [P("path", "path", os.path.join(H, "venv"))])],
 10: [Action("Largest files", storage.large_files, [P("root", "path", H), P("top", "int", 10)])],
 11: [Action("Preview migration", A.migrate_preview, [P("src", "path", ""), P("dst", "path", "")]),
      Action("Copy files (originals untouched)", _mig_apply, [P("src", "path", ""), P("dst", "path", "")], True)],
 12: [Action("Detect drivers (never installs)", B.detect_drivers)],
 13: [Action("Create backup (tar.gz)", A.backup, [P("src", "path", ""), P("archive", "path", os.path.join(H, "nx-backup.tar.gz"))]),
      Action("Restore backup", _restore, [P("archive_path", "path", ""), P("dest", "path", ""), P("sha256", "str", "", "Expected SHA-256 (optional)")], True)],
 14: [Action("Check requirements", B.system_requirements, [P("min_ram_mb", "int", 1024), P("min_disk_gb", "int", 8), P("path", "path", "/")])],
 15: [Action("Performance snapshot", B.snapshot), Action("Boot time", B.startup_time)],
 16: [Action("List disks", B.list_disks), Action("Plan format (no changes)", B.plan_format, [P("device", "str", "/dev/sdX"), P("fstype", "str", "ext4")]),
      Action("FORMAT device", _format, [P("device", "str", ""), P("fstype", "str", "ext4"), P("typed", "str", "", "Type the device path again")], True, "Erases everything on the device")],
 17: [Action("Install preflight", preflight.run, [P("target_dir", "path", "/"), P("check_network", "bool", False)])],
 18: [Action("Build sanitized bug report", bugreport.build)],
 19: [Action("Add record", _compat_add, [P("db", "path", os.path.join(DATA, "compat.json")), P("hardware"), P("nx_version", "str", "0.0.1"), P("result", "str", "works"), P("source", "choice:user-report|tested", "user-report")]),
      Action("Search records", _compat_query, [P("db", "path", os.path.join(DATA, "compat.json")), P("text"), P("verified_only", "bool", False)])],
 20: [Action("Preview profile", B.firewall_preview, [P("profile", "choice:home|public|restricted", "public")]),
      Action("Apply profile (ufw)", _fw_apply, [P("profile", "choice:home|public|restricted", "public")], True)],
 21: [Action("Validate recovery readiness", A.validate_recovery, [P("grub_cfg", "path", "/boot/grub/grub.cfg"), P("iso_dir", "path", "/boot")])],
 22: [Action("Audit sshd_config", A.audit_sshd, [P("path", "path", "/etc/ssh/sshd_config")])],
 23: [Action("Run all checks", netdiag.run_all), Action("DNS lookup", netdiag.dns, [P("host", "str", "archive.ubuntu.com")]),
      Action("TCP connect", netdiag.tcp, [P("host", "str", "archive.ubuntu.com"), P("port", "int", 443)])],
 24: [Action("Run command in test bench", _app_test, [P("command", "str", "echo hello"), P("timeout", "int", 30)])],
 25: [Action("Installed locales", B.locales), Action("Save language preference", _lang, [P("path", "path", os.path.join(CFG, "lang.json")), P("lang", "str", "fa_IR.UTF-8")], True)],
 26: [Action("Power capabilities", B.power_profiles)],
 27: [Action("List startup entries", startup.entries), Action("Disable startup entry", _disable, [P("name"), P("user_dir", "path", os.path.join(CFG, "autostart-disabled"))], True)],
 28: [Action("Add text to clipboard history", _clip_add, [P("text")]), Action("Show history", lambda: list(_clip.items))],
 29: [Action("Take screenshot", C.screenshot, [P("path", "path", os.path.join(H, "nx-screenshot.png"))])],
 30: [Action("Send notification", _notify, [P("title"), P("body")]), Action("History", _notify_hist)],
 31: [Action("List fonts", B.list_fonts), Action("Install font (.ttf/.otf)", _fontinst, [P("src", "path", ""), P("fonts_dir", "path", os.path.join(H, ".local", "share", "fonts"))], True)],
 32: [Action("Create ZIP", _zip, [P("zpath", "path", os.path.join(H, "archive.zip")), P("files", "str", "", "Files (comma separated)"), P("base", "path", H)]),
      Action("Extract (safe)", _extract, [P("path", "path", ""), P("dest", "path", "")])],
 33: [Action("Default app for MIME type", B.default_app, [P("mime", "str", "text/plain")])],
 34: [Action("List outputs", C.audio_sinks), Action("Set volume", _setvol, [P("sink"), P("percent", "int", 50)])],
 35: [Action("List displays", C.displays)],
 36: [Action("Paired devices", C.bluetooth_devices), Action("Pair device", _pair, [P("mac", "str", "AA:BB:CC:DD:EE:FF")], True)],
 37: [Action("Show night-light command", C.night_light_cmd, [P("kelvin", "int", 3400)])],
 38: [Action("Save entry (encrypted)", _vault_put, [P("path", "path", os.path.join(DATA, "vault.bin")), P("passphrase", "secret"), P("site"), P("user"), P("password", "secret")]),
      Action("Open vault", _vault_get, [P("path", "path", os.path.join(DATA, "vault.bin")), P("passphrase", "secret"), P("site", "str", "", "Site (empty = list)"), P("reveal", "bool", False)])],
 39: [Action("Privacy report", C.privacy_report)],
 40: [Action("List scheduled tasks", C.list_tasks), Action("Add cron task", _addtask, [P("schedule", "str", "0 3 * * *"), P("command")], True)],
 41: [Action("List processes", procs.list_processes), Action("Terminate process", _terminate, [P("pid", "int", 0)], True)],
 42: [Action("Find duplicates (preview only, deletes nothing)", storage.find_duplicates, [P("root", "path", H)])],
 43: [Action("Secure-delete advice", C.secure_delete_advice, [P("path", "path", H)])],
 44: [Action("Create web app launcher", C.create_webapp, [P("name"), P("url", "str", "https://"), P("apps_dir", "path", os.path.join(H, ".local", "share", "applications"))])],
 45: [Action("Game Mode plan (applies nothing)", C.game_mode_plan)],
 46: [Action("Build recording command", C.record_command, [P("path", "path", os.path.join(H, "nx-rec.mp4")), P("seconds", "int", 5)])],
 47: [Action("Share targets", C.share_targets), Action("Build e-mail command", C.share_email, [P("path", "path", ""), P("to")])],
 48: [Action("Accessibility settings", C.a11y_status)],
 49: [Action("List USB devices", C.usb_devices), Action("Is device safe to eject?", C.safe_to_eject, [P("device", "str", "/dev/sdb")])],
 50: [Action("Open NX Code Studio", _code_studio, [P("root", "path", H)])],
}


def execute(action, values, confirmed=False):
    kw = {}
    for name, kind, default, _ in action.params:
        raw = values.get(name, default)
        kw[name] = convert(kind, raw)
    if action.danger:
        if not confirmed:
            raise PermissionError("this action changes the system and needs explicit confirmation")
        kw["confirm"] = True
    return action.fn(**kw)
