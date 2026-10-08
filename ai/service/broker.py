"""NX AI tool-execution broker (real, tested core; no Brok or model code here).

Rules enforced:
- Only allowlisted tools run; arguments are validated; no shell strings, no shell=True.
- Risk 'safe' runs immediately; 'privileged' / 'destructive' / 'external' need explicit user approval.
- Every decision is written to an audit log (JSON lines).
- Prompt-injection guard: requests tagged as coming from untrusted content (files, web) can never be auto-approved.
- The broker never escalates privileges itself. Privileged tools must go through PolicyKit (pkexec) in a later milestone.
"""
import json
import subprocess
import time

SAFE, PRIVILEGED, DESTRUCTIVE, EXTERNAL = "safe", "privileged", "destructive", "external"
NEEDS_APPROVAL = {PRIVILEGED, DESTRUCTIVE, EXTERNAL}


class Tool(object):
    def __init__(self, name, argv, risk, arg_pattern=None):
        self.name, self.argv, self.risk = name, list(argv), risk
        self.arg_pattern = arg_pattern  # callable(str)->bool for the single optional arg


DEFAULT_TOOLS = {
    "disk_usage": Tool("disk_usage", ["df", "-h"], SAFE),
    "mem_info": Tool("mem_info", ["free", "-h"], SAFE),
    "kernel": Tool("kernel", ["uname", "-sr"], SAFE),
}


class Broker(object):
    def __init__(self, tools=None, audit_path=None, runner=None):
        self.tools = dict(tools if tools is not None else DEFAULT_TOOLS)
        self.audit_path = audit_path
        self.runner = runner or self._run

    def _audit(self, **ev):
        ev["ts"] = time.time()
        if self.audit_path:
            with open(self.audit_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(ev, sort_keys=True) + "\n")

    @staticmethod
    def _run(argv):
        p = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        return p.returncode, p.stdout.decode("utf-8", "replace")

    def request(self, name, arg=None, approved=False, untrusted_source=False):
        """Returns (status, detail). status: done | needs_approval | denied | failed."""
        tool = self.tools.get(name) if isinstance(name, str) else None
        if tool is None:
            self._audit(tool=str(name), status="denied", reason="not allowlisted")
            return "denied", "tool not allowlisted"
        argv = list(tool.argv)
        if arg is not None:
            if tool.arg_pattern is None or not tool.arg_pattern(arg):
                self._audit(tool=name, status="denied", reason="bad argument")
                return "denied", "argument rejected"
            argv.append(arg)
        if tool.risk in NEEDS_APPROVAL:
            if untrusted_source:
                self._audit(tool=name, status="denied", reason="untrusted source cannot trigger risky tool")
                return "denied", "untrusted content cannot trigger this tool"
            if not approved:
                self._audit(tool=name, status="needs_approval", argv=argv)
                return "needs_approval", "preview: " + " ".join(argv)
        try:
            rc, out = self.runner(argv)
        except Exception as e:  # noqa: BLE001
            self._audit(tool=name, status="failed", error=str(e))
            return "failed", str(e)
        self._audit(tool=name, status="done" if rc == 0 else "failed", rc=rc)
        return ("done" if rc == 0 else "failed"), out
