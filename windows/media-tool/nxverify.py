"""NX ISO verifier core. Pure standard library; syntax compatible with Python 3.8 (Windows 7 SP1)."""
import hashlib
import os
import sys


def sha256_file(path, chunk=1024 * 1024):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def read_expected(sha_file, iso_name):
    """Parse 'sha256sum' format: '<hex>  <name>' (name may have a leading '*')."""
    with open(sha_file, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(None, 1)
            if len(parts) == 2 and parts[1].lstrip("*") == iso_name:
                return parts[0].lower()
    return None


def verify(iso_path, sha_file):
    expected = read_expected(sha_file, os.path.basename(iso_path))
    if expected is None:
        return False, "no checksum entry for this ISO"
    actual = sha256_file(iso_path)
    return actual == expected, actual


if __name__ == "__main__":
    ok, info = verify(sys.argv[1], sys.argv[2])
    print("OK" if ok else "MISMATCH", info)
    sys.exit(0 if ok else 1)
