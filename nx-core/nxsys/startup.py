"""Feature 27 Startup Manager (read side): lists XDG autostart entries. Disabling is non-destructive (Hidden=true override)."""
import os


def entries(dirs=None):
    dirs = dirs or [os.path.expanduser("~/.config/autostart"), "/etc/xdg/autostart"]
    out = []
    for d in dirs:
        if os.path.isdir(d):
            for f in sorted(os.listdir(d)):
                if f.endswith(".desktop"):
                    t = open(os.path.join(d, f), encoding="utf-8", errors="replace").read()
                    out.append({"file": f, "dir": d, "name": next((l.split("=", 1)[1] for l in t.splitlines() if l.startswith("Name=")), f),
                                "hidden": "Hidden=true" in t})
    return out


def disable(name, user_dir):
    os.makedirs(user_dir, exist_ok=True)
    with open(os.path.join(user_dir, name), "w") as f:
        f.write("[Desktop Entry]\nType=Application\nHidden=true\n")
