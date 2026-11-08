"""Frozen-Python (PyInstaller) programs built with Python 3.9+ cannot run on Windows 7 (CPython 3.9 dropped it) and bytecode is version-specific.
Pipeline (needs infrastructure, each piece optional and reported when missing):
  extract  (pyinstxtractor-ng, pip)  ->  decompile (pycdc, C++ tool; incomplete for new opcodes, e.g. `match` on 3.11; bytecode listing is kept
  for the Brok loop)  ->  Brok completes/adapts the source  ->  verify with Python 3.8  ->  re-freeze with PyInstaller on a WINDOWS Python 3.8
  (run under Wine on NX)  ->  differential run against the original (exit code + output) before anything is replaced.
Third-party packages are NOT reinstalled automatically (they need Python-3.8-compatible versions); a rebuild without them is caught by the differential run."""
import os, re, shutil, subprocess, sys, tempfile

MAGIC = b"MEI\x0c\x0b\x0a\x0b\x0e"
STD = set(getattr(sys, "stdlib_module_names", ())) | {"pyimod01_archive", "pyimod02_importers", "pyimod03_ctypes", "pyimod04_pywin32", "_pyi_rth_utils"}


def is_pyinstaller(exe):
    try:
        with open(exe, "rb") as f:
            f.seek(0, 2); size = f.tell(); f.seek(max(0, size - 8 * 1024 * 1024))
            return MAGIC in f.read()
    except OSError:
        return False


def find_pycdc():
    for c in (os.environ.get("NXAT_PYCDC", ""), shutil.which("pycdc") or "", "/opt/pycdc/pycdc", "/usr/local/bin/pycdc", "/tmp/pycdc/pycdc"):
        if c and os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return None


def find_winpy38():
    for c in (os.environ.get("NXAT_WINPY38", ""), os.path.join(os.path.expanduser("~"), ".local", "share", "nx", "winpy38", "python.exe"), "/opt/winpy38/python.exe"):
        if c and os.path.isfile(c):
            return c
    return None


def find_python(minor):
    p = shutil.which("python3.%d" % minor)
    if p:
        return p
    uv = shutil.which("uv")
    if uv:
        r = subprocess.run([uv, "python", "find", "3.%d" % minor], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, universal_newlines=True)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    return None


def have_extractor():
    try:
        import importlib.util
        return importlib.util.find_spec("pyinstxtractor_ng") is not None
    except Exception:
        return False


def extract(exe, workdir):
    r = subprocess.run([sys.executable, "-m", "pyinstxtractor_ng", os.path.abspath(exe)], cwd=workdir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       universal_newlines=True, timeout=600)
    d = os.path.join(workdir, os.path.basename(exe) + "_extracted")
    return d if os.path.isdir(d) else None


def minor_from_extracted(extdir):
    """Python minor version (e.g. 11 for 3.11) from the python3NN.dll that pyinstxtractor unpacked next to the archive contents."""
    for f in os.listdir(extdir):
        m = re.match(r"^python3(\d+)\.dll$", f.lower())
        if m:
            return int(m.group(1))
    return None


_MINOR_CACHE = {}


def frozen_minor(exe):
    """Python minor version of a onefile PyInstaller exe (extracts to a temp dir once per file). None if unknown / no extractor."""
    key = (os.path.abspath(exe), os.path.getsize(exe), int(os.path.getmtime(exe)))
    if key not in _MINOR_CACHE:
        v = None
        if is_pyinstaller(exe) and have_extractor():
            w = tempfile.mkdtemp(prefix="nxat_pyx_")
            try:
                ext = extract(exe, w)
                v = minor_from_extracted(ext) if ext else None
            except (subprocess.SubprocessError, OSError):
                v = None
            finally:
                shutil.rmtree(w, ignore_errors=True)
        _MINOR_CACHE[key] = v
    return _MINOR_CACHE[key]


def app_modules(extdir, exe_base):
    """-> (entry [(modname, pyc)], others [(modname, pyc)]). Entry = the program's own script; others = non-stdlib modules inside the PYZ."""
    entry = [(os.path.splitext(f)[0], os.path.join(extdir, f)) for f in sorted(os.listdir(extdir))
             if f.endswith(".pyc") and not f.startswith(("pyi_", "pyiboot", "pyimod"))]
    others, pyz = [], os.path.join(extdir, "PYZ.pyz_extracted")
    for d, _, fs in os.walk(pyz):
        for f in sorted(fs):
            if f.endswith(".pyc"):
                rel = os.path.relpath(os.path.join(d, f), pyz)[:-4].replace(os.sep, ".")
                if rel.split(".")[0] not in STD and not rel.startswith("pyimod"):
                    others.append((rel, os.path.join(d, f)))
    return entry, others[:60]


def _dis(python, pyc):
    code = "import dis,marshal,sys\nf=open(sys.argv[1],'rb'); f.read(16); dis.dis(marshal.load(f))"
    r = subprocess.run([python, "-c", code, pyc], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=120)
    return r.stdout


def decompile(extdir, exe_base, minor, outdir):
    """-> dict(src, modules=[(mod, relpath, complete?)], entry_py). Writes <mod>.py (and <mod>.dis.txt for incomplete ones)."""
    pycdc = find_pycdc()
    if not pycdc:
        return None
    entry, others = app_modules(extdir, exe_base)
    py = find_python(minor)
    os.makedirs(outdir, exist_ok=True)
    mods, entry_py = [], None
    for kind, items in (("entry", entry), ("lib", others)):
        for mod, pyc in items:
            r = subprocess.run([pycdc, pyc], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=300)
            text = r.stdout
            complete = "Decompyle incomplete" not in text and "Unsupported opcode" not in r.stderr and r.returncode == 0
            rel = mod.replace(".", os.sep) + ".py"
            p = os.path.join(outdir, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "w", encoding="utf-8").write(text)
            if not complete and py:
                open(p[:-3] + ".dis.txt", "w", encoding="utf-8").write(_dis(py, pyc))
            mods.append((mod, rel, complete))
            if kind == "entry" and entry_py is None and mod.lower() == exe_base.lower():
                entry_py = rel
    if entry_py is None and entry:
        entry_py = entry[-1][0] + ".py"
    return {"src": outdir, "modules": mods, "entry_py": entry_py}


def py38_argv():
    p = find_python(8)
    if p:
        return [p]
    w, wp = shutil.which("wine"), find_winpy38()
    return [w, wp] if w and wp else None


def rebuild(dec, saferun, runner):
    """Re-freeze with PyInstaller on Windows Python 3.8 (under Wine on Linux). Replaces dec['exe'] only after a differential run."""
    wine, wp = shutil.which("wine"), find_winpy38()
    if not (wine and wp):
        return False, "re-freeze NOT done: needs Wine + a Windows Python 3.8 with PyInstaller (set NXAT_WINPY38)"
    work = tempfile.mkdtemp(prefix="nxat_py_")
    try:
        for d, _, fs in os.walk(dec["src"]):
            for f in fs:
                if f.endswith(".py"):
                    rel = os.path.relpath(os.path.join(d, f), dec["src"])
                    os.makedirs(os.path.dirname(os.path.join(work, rel)), exist_ok=True); shutil.copy2(os.path.join(d, f), os.path.join(work, rel))
        base = os.path.splitext(os.path.basename(dec["exe"]))[0]
        argv = [wine, wp, "-m", "PyInstaller", "--noconfirm", "--onefile", "--name", base, "--distpath", os.path.join(work, "dist"),
                "--workpath", os.path.join(work, "b"), "--specpath", work, "--paths", work] + (["--noconsole"] if dec.get("gui") else []) + [os.path.join(work, dec["entry_py"])]
        p = subprocess.Popen(argv, cwd=work, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=dict(os.environ, WINEDEBUG="-all"))
        try:
            out = p.communicate(timeout=1500)[0]            # stdin stays open until the build ends (PyInstaller under Wine needs a valid handle)
        except subprocess.TimeoutExpired:
            p.kill(); return False, "re-freeze timed out"
        new = os.path.join(work, "dist", base + ".exe")
        if not os.path.isfile(new):
            return False, "re-freeze failed: " + out.decode("utf8", "replace")[-300:]
        want, got = runner(dec["exe"]), runner(new)
        if want is None or got is None:
            return False, "re-frozen exe NOT used: cannot verify its behaviour here (needs Wine)"
        if want != got:
            return False, "re-frozen exe REJECTED: behaviour differs from the original (original %r vs rebuilt %r)" % (want, got)
        shutil.copy2(new, dec["exe"])
        return True, "re-frozen with Python 3.8 (differential run identical: exit code and output)"
    finally:
        shutil.rmtree(work, ignore_errors=True)
