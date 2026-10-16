"""Feature 10 Storage Analyzer + Feature 42 Duplicate Finder. Analysis/preview only: NEVER deletes."""
import hashlib, os, collections


def large_files(root, top=10, min_bytes=0):
    items = []
    for dp, dn, fn in os.walk(root):
        for f in fn:
            p = os.path.join(dp, f)
            try:
                if not os.path.islink(p):
                    s = os.path.getsize(p)
                    if s >= min_bytes: items.append((s, p))
            except OSError:
                pass
    return sorted(items, reverse=True)[:top]


def _hash(p, n=None):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        h.update(f.read(n) if n else f.read())
    return h.hexdigest()


def find_duplicates(root):
    """Group by size, then partial hash, then full hash (reliable). Returns groups of identical files."""
    by_size = collections.defaultdict(list)
    for dp, dn, fn in os.walk(root):
        for f in fn:
            p = os.path.join(dp, f)
            if not os.path.islink(p):
                try: by_size[os.path.getsize(p)].append(p)
                except OSError: pass
    groups = []
    for size, ps in by_size.items():
        if len(ps) < 2 or size == 0: continue
        full = collections.defaultdict(list)
        for p in ps:
            try: full[_hash(p)].append(p)
            except OSError: pass
        groups += [sorted(v) for v in full.values() if len(v) > 1]
    return sorted(groups)
