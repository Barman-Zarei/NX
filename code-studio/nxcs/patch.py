"""Patch review: unified diff preview and selective, conflict-safe application."""
import difflib, hashlib
from . import workspace


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def diff(old, new, name="file"):
    return "".join(difflib.unified_diff(old.splitlines(True), new.splitlines(True), "a/" + name, "b/" + name))


def hunks(old, new):
    """Return opcodes that change text, as (index, tag, old_lines, new_lines)."""
    a, b = old.splitlines(True), new.splitlines(True)
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    return [(i, t, a[i1:i2], b[j1:j2], (i1, i2, j1, j2))
            for i, (t, i1, i2, j1, j2) in enumerate(sm.get_opcodes()) if t != "equal"]


def apply_selected(old, new, accept):
    """Apply only hunks whose index is in `accept`; others keep the old text."""
    a, b = old.splitlines(True), new.splitlines(True)
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    out, k = [], 0
    for t, i1, i2, j1, j2 in sm.get_opcodes():
        if t == "equal":
            out += a[i1:i2]
        else:
            out += b[j1:j2] if k in accept else a[i1:i2]
            k += 1
    return "".join(out)


def apply_to_file(path, base_text, new_text, accept=None):
    """Refuse if the file changed since base_text was read (preserves user edits made meanwhile)."""
    cur = workspace.read_text(path)
    if digest(cur) != digest(base_text):
        return {"applied": False, "reason": "file changed on disk since the proposal was made"}
    final = new_text if accept is None else apply_selected(base_text, new_text, set(accept))
    workspace.write_text_atomic(path, final)
    return {"applied": True, "reason": ""}
