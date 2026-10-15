"""Task Graph: dependency-ordered execution; independent tasks run concurrently; cancellable."""
import threading
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED


class CycleError(Exception):
    pass


class Graph:
    def __init__(self):
        self.tasks = {}   # name -> (fn, deps)

    def add(self, name, fn, deps=()):
        self.tasks[name] = (fn, tuple(deps))

    def validate(self):
        for n, (_, deps) in self.tasks.items():
            for d in deps:
                if d not in self.tasks:
                    raise KeyError("task %r depends on unknown task %r" % (n, d))
        state = {}

        def visit(n):
            if state.get(n) == 1:
                raise CycleError("cycle involving %r" % n)
            if state.get(n) == 2:
                return
            state[n] = 1
            for d in self.tasks[n][1]:
                visit(d)
            state[n] = 2
        for n in self.tasks:
            visit(n)

    def run(self, workers=4, cancel=None, on_event=None):
        """Returns {name: 'ok'|'failed'|'skipped'|'cancelled'}. A failed task skips its dependents."""
        self.validate()
        cancel = cancel or threading.Event()
        status, running = {}, {}
        emit = on_event or (lambda *a: None)
        with ThreadPoolExecutor(max_workers=workers) as ex:
            while len(status) < len(self.tasks):
                for n, (fn, deps) in self.tasks.items():
                    if n in status or n in running.values():
                        continue
                    if cancel.is_set():
                        status[n] = "cancelled"
                    elif any(status.get(d) in ("failed", "skipped", "cancelled") for d in deps):
                        status[n] = "skipped"
                        emit(n, "skipped")
                    elif all(status.get(d) == "ok" for d in deps):
                        emit(n, "start")
                        running[ex.submit(fn)] = n
                if len(status) >= len(self.tasks):
                    break
                if not running:
                    continue
                done, _ = wait(list(running), return_when=FIRST_COMPLETED)
                for f in done:
                    n = running.pop(f)
                    try:
                        r = f.result()
                        status[n] = "ok" if (r is None or r is True or (type(r) is int and r == 0)) else "failed"
                    except Exception:
                        status[n] = "failed"
                    emit(n, status[n])
        return status
