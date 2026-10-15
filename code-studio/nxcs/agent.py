"""Project Agent: bounded workflow. inspect -> plan/draft (Claude) -> diff -> APPROVAL -> apply -> run tests -> report.
No step writes to disk before `approve(diff)` returns True. Cancellation supported. Files changed on disk
during the AI call are protected by patch.apply_to_file."""
import os, threading
from . import patch, workspace, testintel


class Agent:
    def __init__(self, client, root, approve):
        self.client, self.root, self.approve = client, root, approve
        self.cancel_event = threading.Event()

    def cancel(self):
        self.cancel_event.set(); self.client.cancel()

    def run(self, task, rel_path, run_tests=True):
        path = os.path.join(self.root, rel_path)
        base = workspace.read_text(path)
        reply = self.client.ask("Task: %s\nReturn ONLY the complete new content of %s." % (task, rel_path),
                                context_files={rel_path: base})
        if self.cancel_event.is_set():
            return {"status": "cancelled"}
        new = reply["text"]
        d = patch.diff(base, new, rel_path)
        if not d:
            return {"status": "no_changes", "source": reply["source"]}
        if not self.approve(d):
            return {"status": "rejected", "diff": d, "source": reply["source"]}
        res = patch.apply_to_file(path, base, new)
        if not res["applied"]:
            return {"status": "conflict", "reason": res["reason"], "source": reply["source"]}
        out = {"status": "applied", "diff": d, "source": reply["source"]}
        if run_tests:
            out["tests"] = testintel.run_unittest(self.root)
        return out
