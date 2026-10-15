"""NX Debugger (Python only): real in-process debugger built on bdb. Breakpoints, step/next/return,
continue, call stack, variables, watches, exception stop. NOT a DAP adapter (DAP/other languages: planned)."""
import bdb, threading, os


class Debugger(bdb.Bdb):
    def __init__(self):
        super().__init__()
        self._resume, self._stopped = threading.Event(), threading.Event()
        self._cmd = "continue"; self.state = "idle"; self.frame_ref = None
        self.watches = []; self.exception = None; self.finished = False; self.error = None
        self.thread = None; self._first = True; self.stop_on_entry = False

    def start(self, script, breakpoints=()):
        script = os.path.abspath(script)
        for line in breakpoints:
            self.set_break(script, line)
        self.stop_on_entry = not breakpoints
        self.state = "running"
        self.thread = threading.Thread(target=self._run, args=(script,), daemon=True); self.thread.start()
        return self.wait_stop()

    def _run(self, script):
        src = open(script, encoding="utf-8").read()
        g = {"__name__": "__main__", "__file__": script}
        try:
            self.run(compile(src, script, "exec"), g)
        except bdb.BdbQuit:
            pass
        except BaseException as e:   # script error that escaped the debugger
            self.error = "%s: %s" % (type(e).__name__, e)
        self.finished, self.state = True, "finished"; self._stopped.set()

    def user_line(self, frame):
        if self._first:
            self._first = False
            if not self.stop_on_entry:
                self.set_continue(); return
        self._stop(frame)

    def user_return(self, frame, rv):
        pass

    def user_exception(self, frame, exc_info):
        self.exception = "%s: %s" % (exc_info[0].__name__, exc_info[1]); self._stop(frame)

    def _stop(self, frame):
        self.frame_ref, self.state = frame, "paused"
        self._resume.clear(); self._stopped.set(); self._resume.wait()
        if self._cmd == "quit":
            raise bdb.BdbQuit
        {"step": self.set_step, "next": lambda: self.set_next(frame), "out": lambda: self.set_return(frame),
         "continue": self.set_continue}[self._cmd]()
        self.state = "running"

    def wait_stop(self, timeout=10):
        self._stopped.wait(timeout); self._stopped.clear(); return self.state

    def command(self, cmd):
        self._cmd = cmd; self._resume.set()
        return self.wait_stop() if cmd != "quit" else "quit"

    # --- inspection (valid while paused) ---
    def location(self):
        f = self.frame_ref
        return (f.f_code.co_filename, f.f_lineno) if f else None

    def stack(self):
        out, f = [], self.frame_ref
        while f:
            out.append((f.f_code.co_name, f.f_code.co_filename, f.f_lineno)); f = f.f_back
        return out

    def variables(self):
        return {k: repr(v) for k, v in (self.frame_ref.f_locals if self.frame_ref else {}).items()
                if not k.startswith("__")}

    def evaluate(self, expr):
        try:
            return repr(eval(expr, self.frame_ref.f_globals, self.frame_ref.f_locals))
        except Exception as e:
            return "<error: %s>" % e
