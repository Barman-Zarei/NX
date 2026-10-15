"""Git Command Center: wraps the real git binary. Destructive operations need confirm=True."""
import subprocess


class GitError(Exception):
    pass


class Repo:
    def __init__(self, path):
        self.path = path

    def _git(self, *args, check=True):
        r = subprocess.run(["git", "-C", self.path] + list(args), capture_output=True, text=True)
        if check and r.returncode:
            raise GitError(r.stderr.strip() or "git %s failed" % args[0])
        return r.stdout

    def status(self):
        out = self._git("status", "--porcelain=v1", "-b")
        lines = out.splitlines()
        branch = lines[0][3:] if lines else ""
        return {"branch": branch, "files": [(l[:2], l[3:]) for l in lines[1:]]}

    def diff(self, staged=False, path=None):
        args = ["diff"] + (["--cached"] if staged else []) + (["--", path] if path else [])
        return self._git(*args)

    def stage(self, *paths):
        self._git("add", "--", *paths)

    def unstage(self, *paths):
        self._git("reset", "-q", "HEAD", "--", *paths)

    def commit(self, message):
        if not message.strip():
            raise GitError("empty commit message")
        self._git("commit", "-m", message)
        return self._git("rev-parse", "HEAD").strip()

    def log(self, n=10):
        return self._git("log", "-%d" % n, "--pretty=%h %s").splitlines()

    def branches(self):
        return [b.strip("* ").strip() for b in self._git("branch").splitlines()]

    def create_branch(self, name):
        self._git("switch", "-c", name)

    def switch(self, name):
        self._git("switch", name)

    def conflicts(self):
        return self._git("diff", "--name-only", "--diff-filter=U").split()

    def merge(self, name):
        r = subprocess.run(["git", "-C", self.path, "merge", "--no-edit", name], capture_output=True, text=True)
        return {"ok": r.returncode == 0, "conflicts": self.conflicts(), "output": r.stdout + r.stderr}

    # --- destructive: explicit confirmation required ---
    def discard(self, path, confirm=False):
        if not confirm:
            raise GitError("discard needs confirm=True (changes would be lost)")
        self._git("checkout", "--", path)

    def delete_branch(self, name, confirm=False):
        if not confirm:
            raise GitError("delete_branch needs confirm=True")
        self._git("branch", "-d", name)   # -d refuses unmerged branches

    def push(self, remote="origin", branch=None, force=False, confirm=False):
        if force and not confirm:
            raise GitError("force push needs confirm=True")
        args = ["push"] + (["--force-with-lease"] if force else []) + [remote] + ([branch] if branch else [])
        self._git(*args)
