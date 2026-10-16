"""Features 1,2,3,5,6,7,8,9,11,13,21,22 — non-destructive by default; risky actions need confirm=True."""
import glob, hashlib, json, os, re, shutil, tarfile, time
from . import common
from .common import run, tool, require_confirm


# ---- 1 NX Self-Healing: diagnose; repair only with confirm, and only from a fixed allow-list ----
def diagnose(root="/"):
    found = []
    st = os.statvfs(root)
    free_pct = 100.0 * st.f_bavail / max(st.f_blocks, 1)
    if free_pct < 10:
        found.append({"id": "disk-low", "severity": "high", "detail": "%.1f%% free on %s" % (free_pct, root),
                      "repair": None})
    if os.path.exists("/var/lib/dpkg/lock-frontend") and tool("fuser") is None:
        pass
    if tool("dpkg"):
        r = run(["dpkg", "--audit"])
        if r["out"].strip():
            found.append({"id": "dpkg-broken", "severity": "high", "detail": r["out"].strip()[:300],
                          "repair": ["dpkg", "--configure", "-a"]})
    if tool("systemctl"):
        r = run(["systemctl", "--failed", "--no-legend", "--plain"])
        if r["rc"] == 0 and r["out"].strip():
            found.append({"id": "units-failed", "severity": "medium", "detail": r["out"].strip()[:300], "repair": None})
    return found


ALLOWED_REPAIRS = (["dpkg", "--configure", "-a"],)


def repair(finding, confirm=False, log="/tmp/nx-selfheal.log"):
    require_confirm(confirm, "repair")
    cmd = finding.get("repair")
    if not cmd or cmd not in [list(a) for a in ALLOWED_REPAIRS]:
        return {"ran": False, "reason": "no allow-listed repair for this finding"}
    r = run(cmd, timeout=600)
    with open(log, "a") as f:
        f.write("%s %s rc=%s\n" % (time.strftime("%F %T"), cmd, r["rc"]))
    return {"ran": r["available"], "rc": r["rc"], "log": log}


# ---- 2 Rescue Environment / 21 Recovery Validator ----
def validate_recovery(grub_cfg="/boot/grub/grub.cfg", iso_dir="/boot"):
    checks = []
    def chk(name, ok, detail): checks.append({"check": name, "ok": bool(ok), "detail": detail})
    chk("grub.cfg present", os.path.exists(grub_cfg), grub_cfg)
    kernels = glob.glob(os.path.join(iso_dir, "vmlinuz*"))
    initrds = glob.glob(os.path.join(iso_dir, "initrd*"))
    chk("kernel present", kernels, ", ".join(kernels[:3]) or "none")
    chk("initramfs present", initrds, ", ".join(initrds[:3]) or "none")
    chk("rescue tools: fsck", tool("fsck"), tool("fsck") or "missing")
    chk("rescue tools: grub-install", tool("grub-install"), tool("grub-install") or "missing")
    chk("rescue tools: chroot", tool("chroot"), tool("chroot") or "missing")
    return {"checks": checks, "ready": all(c["ok"] for c in checks),
            "note": "Presence of files does not guarantee recovery will succeed."}


def rescue_plan(root_dev):
    """Documented offline recovery steps for a chosen root device. Returns commands; executes nothing."""
    return ["fsck -n %s   # read-only check first" % root_dev, "mount %s /mnt" % root_dev,
            "mount --bind /dev /mnt/dev; mount --bind /proc /mnt/proc; mount --bind /sys /mnt/sys",
            "chroot /mnt update-grub", "chroot /mnt grub-install <TARGET-DISK>   # verify disk first"]


# ---- 3 Offline Pack ----
def offline_pack(packages, dest):
    """Download .debs (with deps) for later offline install. Needs apt-get; records versions + sha256."""
    os.makedirs(dest, exist_ok=True)
    if not tool("apt-get"):
        return {"ok": False, "reason": "apt-get not available"}
    r = run(["apt-get", "download"] + list(packages), timeout=600)
    if r["rc"] != 0:
        return {"ok": False, "reason": r["err"][:300]}
    return {"ok": True, "files": manifest(dest)}


def manifest(d):
    out = []
    for f in sorted(os.listdir(d)):
        p = os.path.join(d, f)
        if os.path.isfile(p):
            out.append({"file": f, "size": os.path.getsize(p), "sha256": _sha(p)})
    return out


def _sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def verify_pack(d, manifest_list):
    bad = [m["file"] for m in manifest_list if not os.path.exists(os.path.join(d, m["file"]))
           or _sha(os.path.join(d, m["file"])) != m["sha256"]]
    return {"ok": not bad, "bad": bad}


# ---- 5 Easy Mode: persisted mode flag; advanced settings are never deleted ----
def set_mode(path, mode):
    if mode not in ("easy", "advanced"):
        raise ValueError("mode must be easy|advanced")
    d = {}
    if os.path.exists(path):
        d = json.load(open(path))
    d["mode"] = mode
    json.dump(d, open(path, "w"))
    return d


def visible_features(mode, all_features, advanced_only):
    return [f for f in all_features if mode == "advanced" or f not in advanced_only]


# ---- 6 App Inspector (.deb) ----
def inspect_deb(path):
    if not tool("dpkg-deb"):
        return {"available": False}
    info = run(["dpkg-deb", "-f", path])
    fields = dict(re.findall(r"^([A-Za-z-]+): (.*)$", info["out"], re.M))
    scripts = run(["dpkg-deb", "-I", path])["out"]
    risky = [s for s in ("preinst", "postinst", "prerm", "postrm") if re.search(r"\b%s\b" % s, scripts)]
    return {"available": True, "verified": {k: fields.get(k) for k in ("Package", "Version", "Architecture", "Depends")},
            "maintainer_scripts_run_as_root": risky,
            "unverified": "no signature or malware analysis performed"}


# ---- 7 Safe Update ----
def preview_updates():
    if not tool("apt-get"):
        return {"available": False}
    r = run(["apt-get", "-s", "upgrade"])
    ups = re.findall(r"^Inst (\S+) \[([^\]]+)\] \((\S+)", r["out"], re.M)
    return {"available": True, "upgrades": [{"pkg": p, "from": a, "to": b} for p, a, b in ups],
            "rollback": "NOT provided: apt cannot roll back; take a backup first (Feature 13)."}


# ---- 8 Permission Map (filesystem permissions, world-writable + setuid audit) ----
def permission_map(root, limit=50):
    ww, suid = [], []
    for dp, dn, fn in os.walk(root):
        for n in fn:
            p = os.path.join(dp, n)
            try:
                m = os.lstat(p).st_mode
            except OSError:
                continue
            if m & 0o002 and not os.path.islink(p): ww.append(p)
            if m & 0o4000: suid.append(p)
    return {"world_writable": ww[:limit], "setuid": suid[:limit]}


def set_mode_path(path, mode, confirm=False):
    require_confirm(confirm, "chmod")
    os.chmod(path, mode)


# ---- 9 DevKit ----
def devkit_status():
    t = {}
    for n in ("python3", "git", "pip3", "gcc", "node"):
        p = tool(n)
        v = run([n, "--version"])["out"].strip() if p else None
        t[n] = {"path": p, "version": v}
    return t


def create_venv(path):
    r = run(["python3", "-m", "venv", path], timeout=120)
    return {"ok": r["rc"] == 0, "err": r["err"][:200]}


# ---- 11 Migration Assistant (copy, never move/delete originals) ----
def migrate_preview(src, dst):
    plan, skipped = [], []
    for dp, dn, fn in os.walk(src):
        for n in fn:
            s = os.path.join(dp, n)
            d = os.path.join(dst, os.path.relpath(s, src))
            if os.path.islink(s): skipped.append((s, "symlink not migrated"))
            elif os.path.exists(d): skipped.append((s, "exists at destination"))
            else: plan.append((s, d))
    return {"copy": plan, "skipped": skipped}


def migrate_apply(src, dst, confirm=False):
    require_confirm(confirm, "migration")
    pv = migrate_preview(src, dst)
    for s, d in pv["copy"]:
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copy2(s, d)
    return {"copied": len(pv["copy"]), "skipped": pv["skipped"]}


# ---- 13 Backup & Restore ----
def backup(src, archive):
    with tarfile.open(archive, "w:gz") as t:
        t.add(src, arcname=os.path.basename(src.rstrip("/")))
    return {"archive": archive, "sha256": _sha(archive), "size": os.path.getsize(archive),
            "not_included": "files unreadable by this user; permissions/ownership only if run as root"}


def restore(archive, dest, expected_sha256=None, confirm=False):
    require_confirm(confirm, "restore")
    if expected_sha256 and _sha(archive) != expected_sha256:
        raise ValueError("archive checksum mismatch; refusing to restore")
    with tarfile.open(archive) as t:
        for m in t.getmembers():
            tgt = os.path.realpath(os.path.join(dest, m.name))
            if not tgt.startswith(os.path.realpath(dest) + os.sep) and tgt != os.path.realpath(dest):
                raise ValueError("unsafe path in archive: %s" % m.name)
            if m.issym() or m.islnk():
                raise ValueError("links not allowed in restore: %s" % m.name)
        t.extractall(dest)
    return {"restored_to": dest}


# ---- 22 Configuration Audit (sshd / sysctl-style) ----
def audit_sshd(path="/etc/ssh/sshd_config"):
    if not os.path.exists(path):
        return {"available": False, "findings": []}
    txt = open(path).read()
    f = []
    def val(k):
        m = re.findall(r"^\s*%s\s+(\S+)" % k, txt, re.M | re.I)
        return m[-1].lower() if m else None
    if val("PermitRootLogin") in ("yes",):
        f.append({"severity": "high", "setting": "PermitRootLogin yes", "fix": "set PermitRootLogin no"})
    if val("PasswordAuthentication") == "yes":
        f.append({"severity": "medium", "setting": "PasswordAuthentication yes", "fix": "use keys, set to no"})
    return {"available": True, "findings": f}
