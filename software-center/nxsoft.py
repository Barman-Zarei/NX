"""NX Software Center core (CLI): search/info/install/remove over APT (and Flatpak if present) + compatibility DB.
No custom package manager. Installs/removals are privileged: they only RUN when approved=True and are executed
via an injectable runner (the desktop UI must obtain PolicyKit authorization first; this CLI uses sudo/pkexec if not root).
Package names are validated; no shell is ever used."""
import json
import os
import re
import subprocess
import sys

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9+.\-]{1,100}$")
HERE = os.path.dirname(os.path.abspath(__file__))
COMPAT = os.path.join(HERE, "..", "compatibility", "database", "apps.json")


def _run(argv):
    p = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300, env=dict(os.environ, LC_ALL="C"))
    return p.returncode, p.stdout.decode("utf-8", "replace")


def valid(name):
    return isinstance(name, str) and bool(NAME_RE.match(name))


def search(term, runner=_run):
    if not isinstance(term, str) or not term.strip() or term.startswith("-") or len(term) > 100:
        return []
    rc, out = runner(["apt-cache", "search", "--", term])
    res = []
    for line in out.splitlines():
        if " - " in line:
            n, d = line.split(" - ", 1)
            res.append({"name": n.strip(), "summary": d.strip()})
    return res


def info(name, runner=_run):
    if not valid(name):
        return None
    rc, out = runner(["apt-cache", "show", name])
    if rc != 0 or not out:
        return None
    fields = {}
    for line in out.split("\n\n")[0].splitlines():
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            fields[k.strip()] = v.strip()
    return {k: fields.get(k) for k in ("Package", "Version", "Architecture", "Section", "Depends", "Homepage", "Description") if k in fields}


def compat_report(name, apps=None):
    try:
        apps = apps if apps is not None else json.load(open(COMPAT))
    except (OSError, ValueError):
        apps = []
    for a in apps:
        if a.get("name", "").lower() == name.lower():
            return a
    return {"status": "unknown", "note": "no NX compatibility record for this application"}


def plan(action, name):
    """Returns the exact command that would run (preview). action: install|remove."""
    if action not in ("install", "remove") or not valid(name):
        return None
    return ["apt-get", action, "-y", "--no-install-recommends", name]


def apply(action, name, approved=False, runner=_run):
    cmd = plan(action, name)
    if cmd is None:
        return "denied", "invalid action or package name"
    if not approved:
        return "needs_approval", "preview: " + " ".join(cmd)
    if os.geteuid() != 0:
        cmd = ["pkexec"] + cmd
    rc, out = runner(cmd)
    return ("done" if rc == 0 else "failed"), out


def main(argv=None):
    a = argv if argv is not None else sys.argv[1:]
    if len(a) < 2:
        print("usage: nxsoft search|info|install|remove <name> [--yes]"); return 2
    cmd, arg = a[0], a[1]
    if cmd == "search":
        for r in search(arg)[:20]:
            print("%-30s %s" % (r["name"], r["summary"]))
    elif cmd == "info":
        i = info(arg); print(json.dumps({"apt": i, "compat": compat_report(arg)}, indent=2, ensure_ascii=False) if i else "not found")
    elif cmd in ("install", "remove"):
        st, out = apply(cmd, arg, approved="--yes" in a)
        print(st + ": " + out[-500:])
        return 0 if st in ("done", "needs_approval") else 1
    else:
        print("unknown command"); return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
