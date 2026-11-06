"""Installer stub (frozen by PyInstaller 5.13 / Python 3.8 into nx-app-installer.exe, runs on Windows 7 SP1).
Per-user install (no admin): %LOCALAPPDATA%\\Programs\\<Name>, Start-menu shortcut, HKCU uninstall entry. Run with --uninstall to remove.
Options: --silent, --dir PATH."""
import os, shutil, subprocess, sys, tempfile, zipfile


def _pack():
    try:
        from nxat import pack
    except ImportError:
        import pack  # frozen next to this file
    return pack


def _safe_extract(zf, dest):
    d = os.path.realpath(dest)
    for n in zf.namelist():
        if not os.path.realpath(os.path.join(dest, n)).startswith(d):
            raise RuntimeError("unsafe path in package: " + n)
    zf.extractall(dest)


def _shortcut(lnk, target, workdir):
    vbs = 'Set s=CreateObject("WScript.Shell")\nSet l=s.CreateShortcut("%s")\nl.TargetPath="%s"\nl.WorkingDirectory="%s"\nl.Save\n' % (lnk, target, workdir)
    p = os.path.join(tempfile.gettempdir(), "nxat_lnk.vbs")
    open(p, "w", encoding="utf-16").write(vbs)
    try:
        subprocess.call(["cscript", "//nologo", p])
    finally:
        os.remove(p)


def default_dir(man):
    base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(base, "Programs", man["name"])


def install(pkgfile, target=None, log=print):
    pk = _pack()
    man, off, plen = pk.read_package(pkgfile)
    target = target or default_dir(man)
    log("Installing %s to %s" % (man["name"], target))
    os.makedirs(target, exist_ok=True)
    tmp = os.path.join(tempfile.gettempdir(), "nxat_payload.zip")
    with open(pkgfile, "rb") as f, open(tmp, "wb") as o:
        f.seek(off); left = plen
        while left:
            b = f.read(min(left, 1 << 20)); o.write(b); left -= len(b)
    with zipfile.ZipFile(tmp) as z:
        _safe_extract(z, target)
    os.remove(tmp)
    if getattr(sys, "frozen", False):
        shutil.copy2(sys.executable, os.path.join(target, "uninstall.exe"))
    if os.name == "nt":
        import winreg
        exe = os.path.join(target, man["entry"])
        sm = os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs")
        _shortcut(os.path.join(sm, man["name"] + ".lnk"), exe, target)
        k = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall\NXAT_" + man["name"])
        for n, v in (("DisplayName", man["name"] + " (NX Win7)"), ("InstallLocation", target), ("Publisher", man.get("publisher", "")),
                     ("UninstallString", '"%s" --uninstall "%s"' % (os.path.join(target, "uninstall.exe"), target)), ("DisplayVersion", man.get("version", ""))):
            winreg.SetValueEx(k, n, 0, winreg.REG_SZ, v)
    log("Done.")
    return target


def uninstall(target, name=None, log=print):
    if os.name == "nt" and name:
        import winreg
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall\NXAT_" + name)
        except OSError:
            pass
    shutil.rmtree(target, ignore_errors=True)
    log("Removed " + target)


def main(argv=None):
    a = list(sys.argv[1:] if argv is None else argv)
    if "--uninstall" in a:
        t = a[a.index("--uninstall") + 1]
        return uninstall(t, os.path.basename(t.rstrip("\\/")))
    tgt = a[a.index("--dir") + 1] if "--dir" in a else None
    pkg = sys.executable if getattr(sys, "frozen", False) else (a[0] if a and not a[0].startswith("--") else None)
    if not pkg:
        print("usage: installer_stub.py PACKAGE [--dir PATH] [--silent]"); return 2
    install(pkg, tgt)
    if "--silent" not in a and os.name == "nt":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, "Installation finished.", "NX App Installer", 0x40)
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main() or 0)
