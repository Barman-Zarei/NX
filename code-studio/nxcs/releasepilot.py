"""Release Pilot: version bump, changelog from git log, checklist. NEVER tags/pushes/publishes by itself."""
import re, subprocess
from . import workspace


def bump(version, part):
    a, b, c = (int(x) for x in re.match(r"(\d+)\.(\d+)\.(\d+)", version).groups())
    return {"major": "%d.0.0" % (a + 1), "minor": "%d.%d.0" % (a, b + 1), "patch": "%d.%d.%d" % (a, b, c + 1)}[part]


def changelog(repo, since=None):
    rng = (since + "..HEAD") if since else "HEAD"
    r = subprocess.run(["git", "-C", repo, "log", rng, "--pretty=- %s (%h)"], capture_output=True, text=True)
    return r.stdout


def checklist(repo, tests_ok, version):
    dirty = subprocess.run(["git", "-C", repo, "status", "--porcelain"], capture_output=True, text=True).stdout.strip()
    return [("tests pass", bool(tests_ok)), ("working tree clean", not dirty),
            ("version %s is valid semver" % version, bool(re.fullmatch(r"\d+\.\d+\.\d+(-[\w.]+)?", version))),
            ("publishing requires explicit user confirmation (not done here)", True)]
