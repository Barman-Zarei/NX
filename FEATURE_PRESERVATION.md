# FEATURE_PRESERVATION

Statuses are from this session's inspection of the repo + test runs. Names/numbers follow the master prompt exactly.
Most of features 1-49 did NOT exist in the repository before this work; they are PLANNED, not silently dropped or faked.

| # | Feature | Status | Existing/new source | Limitations |
|---|---|---|---|---|
| 1 | NX Self-Healing | PLANNED | - | none found |
| 2 | NX Rescue Environment | PLANNED | docs/installation/recovery.md (docs only) | no rescue image/workflow in code |
| 3 | NX Offline Pack | PLANNED | - | none found |
| 4 | NX Hardware Lab | IMPLEMENTED AND TESTED (inventory only, headless) | nx-core/nxsys/hwlab.py; tests/test_nxsys.py | no diagnostics/stress tests run; no GUI |
| 5 | NX Easy Mode | PLANNED | - | none |
| 6 | NX App Inspector | PARTIALLY IMPLEMENTED | software-center/nxsoft.py (compat-DB lookup) | no permission/security/dependency inspection |
| 7 | NX Safe Update | PLANNED | - | none |
| 8 | NX Permission Map | PLANNED | ai/service/broker.py is an AI-tool permission broker, not this feature | - |
| 9 | NX DevKit | PLANNED | code-studio/nxcs/forge.py gives project templates only | no env/Git/venv manager |
| 10 | NX Storage Analyzer | IMPLEMENTED AND TESTED (headless, preview only) | nx-core/nxsys/storage.py | no GUI; never deletes |
| 11 | NX Migration Assistant | PLANNED | - | none |
| 12 | NX Driver Center | PLANNED | - | none |
| 13 | NX Backup & Restore | PLANNED | - | none (installer scripts are not a backup feature) |
| 14 | NX Compatibility Center | PARTIALLY IMPLEMENTED | compatibility/database/apps.json, compatibility/validate.py | apps DB + schema validation only; no UI |
| 15 | NX Performance Manager | PLANNED | - | none |
| 16 | NX Disk Manager | PARTIALLY IMPLEMENTED | installer/nx-install, nx-install-alongside (disk logic inside installers) | not a manager; no inspection UI |
| 17 | NX Install Preflight | IMPLEMENTED AND TESTED (checks only, headless) | nx-core/nxsys/preflight.py | not wired into installers/Calamares |
| 18 | NX Bug Report Builder | IMPLEMENTED AND TESTED (headless) | nx-core/nxsys/bugreport.py | no GUI/review dialog; never uploads |
| 19 | NX Hardware Compatibility Database | PLANNED | compatibility/ holds an APPS db, not hardware | hardware DB absent |
| 20 | NX Firewall Profiles | PLANNED | - | none |
| 21 | NX Recovery Validator | PLANNED | - | none |
| 22 | NX Configuration Audit | PLANNED | nxcs/review.py audits code, not system config | none |
| 23 | NX Network Diagnostics | IMPLEMENTED AND TESTED (headless) | nx-core/nxsys/netdiag.py | no GUI; network checks depend on host |
| 24 | NX App Test Bench | PLANNED | nxcs/testintel.py runs project tests only | no app isolation bench |
| 25 | NX Language Toolkit | PLANNED | - | none |
| 26 | NX Power Manager | PARTIALLY IMPLEMENTED (read-only status) | nx-core/nxsys/power.py | no controls/profiles; reports unsupported on VMs/desktops |
| 27 | Startup Manager | PARTIALLY IMPLEMENTED (XDG autostart list + non-destructive disable) | nx-core/nxsys/startup.py | no systemd services; no GUI |
| 28 | Clipboard History | PLANNED | - | none |
| 29 | Screenshot Studio | PLANNED | - | none |
| 30 | Notification Center | PLANNED | - | none |
| 31 | Font Manager | PLANNED | - | none |
| 32 | Archive Center | IMPLEMENTED AND TESTED (zip/tar, headless) | nx-core/nxsys/archive.py | no GUI; other formats not supported |
| 33 | Document Center | PLANNED | - | none |
| 34 | Audio Mixer | PLANNED | - | none |
| 35 | Display Manager | PLANNED | - | none |
| 36 | Device Pairing | PLANNED | - | none |
| 37 | Night Light | PLANNED | - | none |
| 38 | Password Vault | PLANNED | - | no crypto primitive chosen yet |
| 39 | Privacy Dashboard | PLANNED | - | none |
| 40 | Task Scheduler | PLANNED | - | none |
| 41 | Process Manager | PARTIALLY IMPLEMENTED (list + guarded terminate, headless) | nx-core/nxsys/procs.py | no GUI; no resource graph |
| 42 | Duplicate Finder | IMPLEMENTED AND TESTED (headless, never deletes) | nx-core/nxsys/storage.py | no GUI/deletion workflow |
| 43 | Secure Delete Guide | PLANNED | - | none |
| 44 | Web Apps | PLANNED | - | none |
| 45 | Game Mode | PLANNED | - | none |
| 46 | Screen Recorder | PLANNED | - | none |
| 47 | Share Sheet | PLANNED | - | none |
| 48 | Accessibility Toolkit | PLANNED | - | none |
| 49 | USB Manager | PLANNED | nx-core hwlab.block_devices lists removable flag only | no USB manager |
| 50 | NX Code Studio | PARTIALLY IMPLEMENTED | code-studio/ (see FEATURES.md module table) | many modules incomplete |
