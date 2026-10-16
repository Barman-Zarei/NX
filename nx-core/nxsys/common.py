"""Shared helpers: run external tools honestly (distinguish 'tool missing' from 'tool failed')."""
import os, shutil, subprocess


def tool(name):
    return shutil.which(name)


def run(argv, timeout=30, input_text=None, env=None):
    exe = tool(argv[0])
    if not exe:
        return {"available": False, "rc": None, "out": "", "err": "%s not installed" % argv[0]}
    try:
        r = subprocess.run([exe] + list(argv[1:]), capture_output=True, text=True, timeout=timeout,
                           input=input_text, env=env)
        return {"available": True, "rc": r.returncode, "out": r.stdout, "err": r.stderr}
    except subprocess.TimeoutExpired:
        return {"available": True, "rc": None, "out": "", "err": "timeout after %ss" % timeout}


def is_root():
    return hasattr(os, "geteuid") and os.geteuid() == 0


def require_confirm(confirm, what):
    if not confirm:
        raise PermissionError("%s needs explicit confirm=True" % what)
