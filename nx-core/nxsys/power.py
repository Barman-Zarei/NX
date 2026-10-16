"""Feature 26 Power Manager (read side): reports what the hardware exposes; says 'unsupported' otherwise."""
import os
BASE = "/sys/class/power_supply"


def status():
    if not os.path.isdir(BASE) or not os.listdir(BASE):
        return {"supported": False, "reason": "no power_supply devices exposed (desktop/VM?)", "devices": []}
    devs = []
    for d in sorted(os.listdir(BASE)):
        def rd(n):
            try:
                with open(os.path.join(BASE, d, n)) as f: return f.read().strip()
            except OSError: return None
        devs.append({"name": d, "type": rd("type"), "capacity": rd("capacity"), "status": rd("status")})
    return {"supported": True, "devices": devs}
