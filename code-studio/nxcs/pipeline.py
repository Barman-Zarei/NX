"""Pipeline Lab: inspect GitHub Actions workflows and run their `run:` steps locally.

Honest scope: only `run:` shell steps are executed. `uses:` actions, service containers,
matrix expansion, secrets and hosted-runner features are reported as UNSUPPORTED (not faked).
"""
import re
try:
    import yaml
except ImportError:  # PyYAML is optional; inspection then reports itself as unavailable
    yaml = None
from . import saferun


def inspect(path):
    if yaml is None:
        return {"error": "PyYAML not installed", "jobs": {}}
    with open(path, encoding="utf-8") as f:
        wf = yaml.safe_load(f)
    jobs, unsupported = {}, []
    for jn, job in (wf.get("jobs") or {}).items():
        steps = job.get("steps", [])
        jobs[jn] = {"runs_on": job.get("runs-on"), "needs": _list(job.get("needs")),
                    "run_steps": [s["run"] for s in steps if "run" in s],
                    "uses": [s["uses"] for s in steps if "uses" in s]}
        if "services" in job:
            unsupported.append("%s: service containers" % jn)
        if "matrix" in (job.get("strategy") or {}):
            unsupported.append("%s: matrix strategy" % jn)
        if any("secrets." in s.get("run", "") or "secrets." in str(s.get("env", "")) for s in steps):
            unsupported.append("%s: uses secrets (not provided locally)" % jn)
        for u in jobs[jn]["uses"]:
            unsupported.append("%s: action %s is not executed locally" % (jn, u))
        if re.search(r"\$\{\{", str(steps)):
            unsupported.append("%s: ${{ }} expressions are not evaluated" % jn)
    return {"error": None, "jobs": jobs, "unsupported": sorted(set(unsupported))}


def _list(v):
    return [] if v is None else ([v] if isinstance(v, str) else list(v))


def run_job(info, job, cwd, timeout=300, restricted=True, on_output=None):
    results = []
    for cmd in info["jobs"][job]["run_steps"]:
        if "${{" in cmd:
            results.append({"cmd": cmd, "skipped": "contains ${{ }} expression"})
            continue
        r = saferun.run(["bash", "-eo", "pipefail", "-c", cmd], cwd=cwd, timeout=timeout,
                        restricted=restricted, on_output=on_output)
        results.append({"cmd": cmd, "returncode": r["returncode"], "isolation": r["isolation"]})
        if r["returncode"]:
            break
    return results
