"""Turn an input (folder, zip, MSI, NSIS/Inno/SFX installer, .asar) into an app folder. Uses 7z / innoextract if installed."""
import json, os, shutil, struct, subprocess, zipfile


class UnpackError(Exception):
    pass


def read_asar(path, dest):
    """Pure-python asar extractor (format: u32 pickle header size ... JSON index ... file data)."""
    with open(path, "rb") as f:
        hdr = f.read(16)
        jlen = struct.unpack("<I", hdr[12:16])[0]
        index = json.loads(f.read(jlen).decode("utf-8"))
        base = 8 + struct.unpack("<I", hdr[4:8])[0]
        dest_abs = os.path.realpath(dest)

        def walk(node, rel):
            for name, ent in node.get("files", {}).items():
                p = os.path.join(rel, name)
                tgt = os.path.realpath(os.path.join(dest, p))
                if not tgt.startswith(dest_abs + os.sep):
                    raise UnpackError("asar path escapes destination: " + p)
                if "files" in ent:
                    os.makedirs(tgt, exist_ok=True); walk(ent, p)
                elif "link" in ent or ent.get("unpacked"):
                    continue
                else:
                    f.seek(base + int(ent["offset"]))
                    os.makedirs(os.path.dirname(tgt), exist_ok=True)
                    with open(tgt, "wb") as o:
                        o.write(f.read(int(ent["size"])))
        walk(index, "")


def _safe_zip(path, dest):
    dest_abs = os.path.realpath(dest)
    with zipfile.ZipFile(path) as z:
        for n in z.namelist():
            if not os.path.realpath(os.path.join(dest, n)).startswith(dest_abs):
                raise UnpackError("zip entry escapes destination: " + n)
        z.extractall(dest)


def _run(cmd):
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    return r.returncode, r.stdout


def unpack(src, dest):
    """-> method string. Raises UnpackError with an honest reason when it cannot extract."""
    os.makedirs(dest, exist_ok=True)
    if os.path.isdir(src):
        shutil.copytree(src, dest, dirs_exist_ok=True)
        return "folder"
    low = src.lower()
    if low.endswith(".asar"):
        read_asar(src, dest); return "asar"
    if zipfile.is_zipfile(src) and not low.endswith((".exe", ".msi")):
        _safe_zip(src, dest); return "zip"
    if shutil.which("innoextract") and low.endswith(".exe"):
        rc, out = _run(["innoextract", "-s", "-d", dest, src])
        if rc == 0:
            app = os.path.join(dest, "app")
            if os.path.isdir(app):      # innoextract puts payload into ./app
                for n in os.listdir(app):
                    shutil.move(os.path.join(app, n), os.path.join(dest, n))
                os.rmdir(app)
            return "inno"
    sz = shutil.which("7z") or shutil.which("7za") or shutil.which("7zr")
    if sz and low.endswith((".exe", ".dll")):
        rc, out = _run([sz, "l", "-slt", src])
        types = [l.split("=", 1)[1].strip() for l in out.splitlines() if l.startswith("Type =")]
        if types[:1] == ["PE"] or rc != 0 and not types:
            shutil.copy2(src, dest)      # a plain program, not an installer/SFX: translate it as is
            return "single-exe"
    if sz:
        rc, out = _run([sz, "x", "-y", "-o" + dest, src])
        if rc in (0, 1) and os.listdir(dest):
            return "7z"
        raise UnpackError("7z could not extract %s: %s" % (os.path.basename(src), out[-300:]))
    raise UnpackError("no extractor for %s (install 7-Zip or innoextract, or pass an app folder/zip)" % os.path.basename(src))
