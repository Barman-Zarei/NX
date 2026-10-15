"""Workspace: file read/write (atomic), search/replace, recent projects."""
import json, os, re, tempfile

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", "build", "dist"}


def read_text(path):
    with open(path, "rb") as f:
        data = f.read()
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1")


def write_text_atomic(path, text):
    """Write via temp file + rename so a crash never leaves a half-written file."""
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".nxcs-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        if os.path.exists(path):
            os.chmod(tmp, os.stat(path).st_mode & 0o7777)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def iter_files(root):
    for dp, dn, fn in os.walk(root):
        dn[:] = sorted(d for d in dn if d not in SKIP_DIRS)
        for f in sorted(fn):
            yield os.path.join(dp, f)


def search(root, pattern, regex=False, ignore_case=False):
    flags = re.I if ignore_case else 0
    rx = re.compile(pattern if regex else re.escape(pattern), flags)
    hits = []
    for p in iter_files(root):
        try:
            text = read_text(p)
        except OSError:
            continue
        if "\0" in text:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            if rx.search(line):
                hits.append((p, n, line))
    return hits


def replace_in_file(path, pattern, repl, regex=False, dry_run=True):
    """Returns (count, new_text). Writes only when dry_run is False."""
    text = read_text(path)
    rx = re.compile(pattern if regex else re.escape(pattern))
    new, n = rx.subn(repl if regex else repl.replace("\\", "\\\\"), text)
    if n and not dry_run:
        write_text_atomic(path, new)
    return n, new


class Recent:
    def __init__(self, store):
        self.store = store

    def load(self):
        try:
            with open(self.store, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return []

    def add(self, project, limit=10):
        items = [p for p in self.load() if p != project]
        items.insert(0, project)
        os.makedirs(os.path.dirname(os.path.abspath(self.store)), exist_ok=True)
        with open(self.store, "w", encoding="utf-8") as f:
            json.dump(items[:limit], f, ensure_ascii=False)
