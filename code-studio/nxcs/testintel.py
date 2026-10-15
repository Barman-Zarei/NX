"""Test Intelligence: discover and run real tests (unittest / pytest if installed), parse results."""
import os, re, sys
from . import saferun


def discover(root):
    found = []
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in (".git", "__pycache__", "node_modules", ".venv")]
        for f in fn:
            if re.match(r"(test_.*|.*_test)\.py$", f):
                found.append(os.path.relpath(os.path.join(dp, f), root))
    return sorted(found)


def run_unittest(root, start=".", pattern="test_*.py", timeout=300):
    res = saferun.run([sys.executable, "-m", "unittest", "discover", "-s", start, "-p", pattern, "-v"],
                      cwd=root, timeout=timeout, restricted=False)
    out = res["output"]
    m = re.search(r"Ran (\d+) tests?", out)
    ran = int(m.group(1)) if m else 0
    failed = re.findall(r"^(?:FAIL|ERROR): (\S+ \([^)]*\))", out, re.M)
    skipped = re.search(r"skipped=(\d+)", out)
    return {"ran": ran, "failed": failed, "skipped": int(skipped.group(1)) if skipped else 0,
            "ok": res["returncode"] == 0 and ran > 0, "returncode": res["returncode"], "output": out}


def failure_locations(output):
    return [(f, int(n)) for f, n in re.findall(r'File "([^"]+)", line (\d+)', output)]
