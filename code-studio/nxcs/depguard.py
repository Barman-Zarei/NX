"""Dependency Guardian: outdated packages via `pip list --outdated` (needs network/index). No advisory DB is bundled;
vulnerability data is reported as UNAVAILABLE rather than guessed."""
import json, sys
from . import saferun


def outdated(python=None):
    r = saferun.run([python or sys.executable, "-m", "pip", "list", "--outdated", "--format=json"],
                    timeout=120, restricted=False)
    if r["returncode"]:
        return {"ok": False, "error": r["output"][-300:], "packages": [], "advisories": "unavailable"}
    start = r["output"].find("[")
    try:
        pk = json.loads(r["output"][start:])
    except ValueError:
        return {"ok": False, "error": "unparseable pip output", "packages": [], "advisories": "unavailable"}
    return {"ok": True, "packages": [(p["name"], p["version"], p["latest_version"]) for p in pk], "advisories": "unavailable"}


def preview_upgrade(name, current, latest):
    major = lambda v: v.split(".")[0]
    risk = "major version change: may break compatibility" if major(current) != major(latest) else "minor/patch change"
    return {"package": name, "from": current, "to": latest, "risk": risk, "disk_impact": "unknown (not estimated)"}
