"""Log Explorer: level/regex filtering and sanitization of logs for sharing."""
import re
LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
REDACT = [(re.compile(r"(sk-[A-Za-z0-9_\-]{8,})"), "sk-***"),
          (re.compile(r"(?i)(password|token|secret|api[_-]?key)\s*[=:]\s*\S+"), r"\1=***"),
          (re.compile(r"/home/[^/\s]+"), "/home/<user>")]


def filter_lines(text, min_level="DEBUG", pattern=None):
    rx = re.compile(pattern) if pattern else None
    floor = LEVELS.index(min_level); out = []
    for n, line in enumerate(text.splitlines(), 1):
        lv = next((i for i, l in enumerate(LEVELS) if l in line), None)
        if lv is not None and lv < floor:
            continue
        if rx and not rx.search(line):
            continue
        out.append((n, line))
    return out


def sanitize(text):
    for rx, rep in REDACT:
        text = rx.sub(rep, text)
    return text
