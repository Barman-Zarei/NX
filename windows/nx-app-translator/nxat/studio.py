"""Locate NX Studio Code's Python core (patch review = conflict-safe apply, Safe Run = timeouts/env scrub) and import it."""
import glob, importlib, os, sys

REL = os.path.join("extensions", "nx-studio", "python")


def find():
    here = os.path.dirname(os.path.abspath(__file__))
    cands = [os.environ.get("NX_STUDIO_PY", ""), os.path.join(here, "..", "..", "..", "code-studio", REL)]
    lp = os.environ.get("LOCALAPPDATA", "")
    if lp:
        cands += glob.glob(os.path.join(lp, "Programs", "NX Studio Code", "resources", "app", REL))
    cands += glob.glob(os.path.join("/opt/nx-studio-code", "resources", "app", REL))
    for c in cands:
        if c and os.path.isfile(os.path.join(c, "nxcs", "patch.py")):
            return os.path.abspath(c)
    return None


def load():
    """-> (patch, saferun, workspace) modules from NX Studio Code, or raises RuntimeError."""
    p = find()
    if not p:
        raise RuntimeError("NX Studio Code core not found (init the code-studio submodule or set NX_STUDIO_PY)")
    if p not in sys.path:
        sys.path.insert(0, p)
    m = [importlib.import_module("nxcs." + n) for n in ("patch", "saferun", "workspace")]
    return tuple(m)
