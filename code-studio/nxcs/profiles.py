"""Studio Profiles / Environment Profiles: presets that change real settings (written to settings JSON)."""
import json, os
from . import workspace

STUDIO = {
 "python":   {"tab_width": 4, "formatter": "black", "tests": "unittest", "terminal_limit_mb": 1024, "extensions": ["python"]},
 "web":      {"tab_width": 2, "formatter": "prettier", "tests": "npm test", "live_preview": True, "extensions": ["html", "css", "js"]},
 "cpp":      {"tab_width": 4, "formatter": "clang-format", "tests": "make test", "extensions": ["c", "cpp"]},
 "multi":    {"tab_width": 4, "formatter": "per-language", "tests": "auto", "extensions": ["python", "html", "css", "js", "c", "cpp"]},
 "low-resource": {"tab_width": 4, "terminal_limit_mb": 256, "live_preview": False, "ai_context_files": 2, "extensions": []},
}
SECRET_HINTS = ("key", "token", "secret", "password")


def apply(name, settings_path):
    if name not in STUDIO:
        raise KeyError(name)
    cur = {}
    if os.path.exists(settings_path):
        cur = json.loads(workspace.read_text(settings_path))
    cur.update(STUDIO[name]); cur["profile"] = name
    os.makedirs(os.path.dirname(os.path.abspath(settings_path)), exist_ok=True)
    workspace.write_text_atomic(settings_path, json.dumps(cur, indent=2))
    return cur


def validate_shared_config(d):
    """Environment profiles live in project files: refuse anything that looks like a secret."""
    bad = [k for k in d if any(h in k.lower() for h in SECRET_HINTS)]
    if bad:
        raise ValueError("secrets must not be stored in shared project files: %s" % bad)
    return True
