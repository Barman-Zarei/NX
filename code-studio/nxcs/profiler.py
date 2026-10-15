"""Performance Profiler: real cProfile (CPU/function level) + tracemalloc (memory) of a Python script."""
import cProfile, io, pstats, runpy, time, tracemalloc


def profile_script(path, top=10):
    pr = cProfile.Profile(); tracemalloc.start(); t = time.time()
    try:
        pr.runcall(runpy.run_path, path, run_name="__main__")
        err = None
    except BaseException as e:
        err = "%s: %s" % (type(e).__name__, e)
    cur, peak = tracemalloc.get_traced_memory(); tracemalloc.stop()
    st = pstats.Stats(pr, stream=io.StringIO()).sort_stats("cumulative")
    rows = []
    for (fn, ln, name), (cc, nc, tt, ct, _c) in list(st.stats.items()):
        rows.append({"function": "%s:%d(%s)" % (fn, ln, name), "calls": nc, "total_s": round(tt, 6), "cum_s": round(ct, 6)})
    rows.sort(key=lambda r: -r["cum_s"])
    return {"seconds": round(time.time() - t, 4), "peak_kib": peak // 1024, "error": err, "top": rows[:top]}
