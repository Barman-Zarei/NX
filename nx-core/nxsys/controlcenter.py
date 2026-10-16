"""NX Control Center registry: every numbered feature -> (name, read-only check or None).
Only SAFE, read-only checks are exposed here. Anything that changes the system stays behind the
service functions' confirm=True gates and is not triggered from this panel."""
import os
from . import (hwlab, storage, startup, procs, netdiag, preflight, bugreport, power,
               sysfeatures_a as A, sysfeatures_b as B, sysfeatures_c as C)

NAMES = {1: "NX Self-Healing", 2: "NX Rescue Environment", 3: "NX Offline Pack", 4: "NX Hardware Lab", 5: "NX Easy Mode",
 6: "NX App Inspector", 7: "NX Safe Update", 8: "NX Permission Map", 9: "NX DevKit", 10: "NX Storage Analyzer",
 11: "NX Migration Assistant", 12: "NX Driver Center", 13: "NX Backup & Restore", 14: "NX Compatibility Center",
 15: "NX Performance Manager", 16: "NX Disk Manager", 17: "NX Install Preflight", 18: "NX Bug Report Builder",
 19: "NX Hardware Compatibility Database", 20: "NX Firewall Profiles", 21: "NX Recovery Validator",
 22: "NX Configuration Audit", 23: "NX Network Diagnostics", 24: "NX App Test Bench", 25: "NX Language Toolkit",
 26: "NX Power Manager", 27: "Startup Manager", 28: "Clipboard History", 29: "Screenshot Studio", 30: "Notification Center",
 31: "Font Manager", 32: "Archive Center", 33: "Document Center", 34: "Audio Mixer", 35: "Display Manager",
 36: "Device Pairing", 37: "Night Light", 38: "Password Vault", 39: "Privacy Dashboard", 40: "Task Scheduler",
 41: "Process Manager", 42: "Duplicate Finder", 43: "Secure Delete Guide", 44: "Web Apps", 45: "Game Mode",
 46: "Screen Recorder", 47: "Share Sheet", 48: "Accessibility Toolkit", 49: "USB Manager", 50: "NX Code Studio"}

CHECKS = {
 1: A.diagnose, 2: A.validate_recovery, 4: hwlab.report, 7: A.preview_updates, 8: lambda: A.permission_map("/etc", 20),
 9: A.devkit_status, 10: lambda: storage.large_files(os.path.expanduser("~"), 5), 12: B.detect_drivers,
 14: B.system_requirements, 15: B.snapshot, 16: B.list_disks, 17: preflight.run, 18: bugreport.build,
 20: lambda: B.firewall_preview("public"), 22: A.audit_sshd, 23: netdiag.run_all, 25: B.locales, 26: B.power_profiles,
 27: startup.entries, 31: B.list_fonts, 34: C.audio_sinks, 35: C.displays, 36: C.bluetooth_devices, 39: C.privacy_report,
 40: C.list_tasks, 41: procs.list_processes, 43: lambda: C.secure_delete_advice("."), 45: C.game_mode_plan,
 47: C.share_targets, 48: C.a11y_status, 49: C.usb_devices,
}


def features():
    return [(n, NAMES[n], n in CHECKS) for n in sorted(NAMES)]


def run_check(n):
    f = CHECKS.get(n)
    if f is None:
        return {"note": "no read-only check; this feature needs arguments or confirmation and is used through its service API (see FEATURE_PRESERVATION.md)"}
    try:
        return f()
    except Exception as e:     # a failing check must not crash the panel
        return {"error": "%s: %s" % (type(e).__name__, e)}
