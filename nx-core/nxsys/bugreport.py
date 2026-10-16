"""Feature 18 Bug Report Builder: collects version/hardware info, sanitizes, returns text for USER REVIEW (never uploads)."""
import platform, re, sys
from . import hwlab

RED = [(re.compile(r"(sk-[A-Za-z0-9_\-]{8,})"), "sk-***"), (re.compile(r"(?i)(password|token|secret|api[_-]?key)\s*[=:]\s*\S+"), r"\1=***"),
       (re.compile(r"/home/[^/\s]+"), "/home/<user>"), (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "<ip>")]


def sanitize(t):
    for rx, rep in RED: t = rx.sub(rep, t)
    return t


def build(extra_log=""):
    hw = hwlab.report()
    txt = "NX bug report\npython: %s\nplatform: %s\nhardware: %s\n--- log ---\n%s\n" % (sys.version.split()[0], platform.platform(), hw, extra_log)
    return sanitize(txt)
