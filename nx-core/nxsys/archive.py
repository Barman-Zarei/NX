"""Feature 32 Archive Center: zip/tar with path-traversal, symlink and size protection."""
import os, tarfile, zipfile


class UnsafeArchive(Exception):
    pass


def _check(dest, name):
    target = os.path.realpath(os.path.join(dest, name))
    if not (target == os.path.realpath(dest) or target.startswith(os.path.realpath(dest) + os.sep)):
        raise UnsafeArchive("path escapes destination: %s" % name)


def create_zip(zpath, files, base):
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(f, os.path.relpath(f, base))


def extract(path, dest, max_total_mb=1024):
    os.makedirs(dest, exist_ok=True)
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            if sum(i.file_size for i in z.infolist()) > max_total_mb << 20:
                raise UnsafeArchive("archive too large when extracted")
            for i in z.infolist(): _check(dest, i.filename)
            z.extractall(dest); return [i.filename for i in z.infolist()]
    if tarfile.is_tarfile(path):
        with tarfile.open(path) as t:
            ms = t.getmembers()
            if sum(m.size for m in ms) > max_total_mb << 20: raise UnsafeArchive("archive too large when extracted")
            for m in ms:
                _check(dest, m.name)
                if m.issym() or m.islnk() or m.isdev(): raise UnsafeArchive("links/devices not allowed: %s" % m.name)
            t.extractall(dest); return [m.name for m in ms]
    raise UnsafeArchive("not a supported or valid archive")
