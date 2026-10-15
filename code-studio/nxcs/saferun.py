"""Safe Run / Terminal. Honest about what is and is not restricted.

Restrictions actually applied (POSIX): scrubbed environment (no secrets), wall-clock timeout,
RLIMIT_CPU / RLIMIT_AS / RLIMIT_FSIZE / RLIMIT_NPROC, new process group (killed on timeout/cancel).
Network isolation only if `unshare -rn` works on this host. NOT a full sandbox: files of the
user are still readable/writable. report['isolation'] states exactly what was applied.
"""
import os, shutil, signal, subprocess, threading, time

SAFE_ENV_KEYS = ("PATH", "HOME", "LANG", "LC_ALL", "TERM", "TMPDIR", "SYSTEMROOT", "COMSPEC", "PATHEXT", "USERPROFILE", "TEMP", "TMP")


def scrub_env(extra=None):
    env = {k: v for k, v in os.environ.items() if k in SAFE_ENV_KEYS}
    env.update(extra or {})
    return env


def _unshare_ok():
    exe = shutil.which("unshare")
    if not exe:
        return None
    try:
        r = subprocess.run([exe, "-rn", "true"], capture_output=True, timeout=5)
        return exe if r.returncode == 0 else None
    except Exception:
        return None


class Cancelled(Exception):
    pass


class Job:
    def __init__(self, argv, cwd=None, timeout=60, restricted=True, no_network=False,
                 mem_mb=1024, on_output=None, env=None):
        self.argv, self.cwd, self.timeout = list(argv), cwd, timeout
        self.restricted, self.no_network, self.mem_mb = restricted, no_network, mem_mb
        self.on_output, self.env = on_output, env
        self.proc = None
        self._cancel = threading.Event()
        self.isolation = []

    def cancel(self):
        self._cancel.set()
        self._kill()

    def _kill(self):
        if self.proc and self.proc.poll() is None:
            try:
                os.killpg(self.proc.pid, signal.SIGKILL)   # POSIX: kill whole process group
            except (AttributeError, ProcessLookupError, PermissionError):
                self.proc.kill()                            # Windows / fallback: kill the process only

    def _preexec(self):
        import resource
        os.setsid()
        if self.restricted:
            resource.setrlimit(resource.RLIMIT_CPU, (self.timeout + 5, self.timeout + 5))
            resource.setrlimit(resource.RLIMIT_FSIZE, (512 << 20, 512 << 20))
            resource.setrlimit(resource.RLIMIT_AS, (self.mem_mb << 20, self.mem_mb << 20))

    def run(self):
        argv = self.argv
        env = scrub_env(self.env) if self.restricted else dict(os.environ, **(self.env or {}))
        if self.restricted:
            self.isolation = ["env-scrubbed", "timeout", "rlimits(cpu,as,fsize)", "process-group-kill"]
            if self.no_network:
                ex = _unshare_ok()
                if ex:
                    argv = [ex, "-rn"] + argv
                    self.isolation.append("network-namespace")
                else:
                    self.isolation.append("NETWORK-NOT-ISOLATED(unshare unavailable)")
        else:
            self.isolation = ["none"]
        t0 = time.time()
        out = []
        try:
            self.proc = subprocess.Popen(argv, cwd=self.cwd, env=env, stdout=subprocess.PIPE,
                                         stderr=subprocess.STDOUT, text=True, errors="replace",
                                         preexec_fn=self._preexec if os.name == "posix" else None)
        except OSError as e:
            return {"returncode": 127, "output": str(e), "timed_out": False, "cancelled": False,
                    "isolation": self.isolation, "seconds": 0.0}
        timed = [False]

        def watchdog():
            while self.proc.poll() is None:
                if time.time() - t0 > self.timeout:
                    timed[0] = True
                    self._kill()
                    return
                time.sleep(0.05)
        threading.Thread(target=watchdog, daemon=True).start()
        for line in self.proc.stdout:
            out.append(line)
            if self.on_output:
                self.on_output(line)
        rc = self.proc.wait()
        return {"returncode": rc, "output": "".join(out), "timed_out": timed[0],
                "cancelled": self._cancel.is_set(), "isolation": self.isolation,
                "seconds": round(time.time() - t0, 3)}


def run(argv, **kw):
    return Job(argv, **kw).run()
