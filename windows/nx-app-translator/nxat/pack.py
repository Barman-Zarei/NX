"""Build the final installer: copy of the prebuilt stub exe + payload.zip + manifest + trailer (self-extracting, no compiler needed
on the user's machine). Trailer layout (all little-endian): payload | manifest(JSON) | u64 manifest_len | u64 payload_len | b'NXATPKG1'."""
import hashlib, json, os, struct, zipfile

MAGIC = b"NXATPKG1"


def make_payload(root, zip_path):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for d, _, fs in os.walk(root):
            for f in sorted(fs):
                p = os.path.join(d, f)
                z.write(p, os.path.relpath(p, root).replace(os.sep, "/"))
    return zip_path


def build_installer(stub_path, payload_zip, manifest, out_path):
    pay = open(payload_zip, "rb").read()
    manifest = dict(manifest, payload_sha256=hashlib.sha256(pay).hexdigest())
    mj = json.dumps(manifest, ensure_ascii=False, sort_keys=True).encode("utf-8")
    with open(out_path, "wb") as o:
        o.write(open(stub_path, "rb").read())
        o.write(pay); o.write(mj)
        o.write(struct.pack("<QQ", len(mj), len(pay))); o.write(MAGIC)
    return out_path


def read_package(path):
    """-> (manifest dict, payload_offset, payload_len). Verifies the payload hash."""
    with open(path, "rb") as f:
        f.seek(0, 2); size = f.tell()
        if size < 24:
            raise ValueError("not an NXAT package")
        f.seek(size - 24)
        mlen, plen = struct.unpack("<QQ", f.read(16))
        if f.read(8) != MAGIC or mlen + plen + 24 > size:
            raise ValueError("not an NXAT package")
        f.seek(size - 24 - mlen); man = json.loads(f.read(mlen).decode("utf-8"))
        off = size - 24 - mlen - plen
        h = hashlib.sha256(); f.seek(off); left = plen
        while left:
            b = f.read(min(left, 1 << 20)); h.update(b); left -= len(b)
        if h.hexdigest() != man.get("payload_sha256"):
            raise ValueError("payload checksum mismatch (corrupt download?)")
    return man, off, plen
