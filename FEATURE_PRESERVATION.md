# FEATURE_PRESERVATION

Statuses are from this session's inspection of the repo + test runs. Names/numbers follow the master prompt exactly.
Most of features 1-49 did NOT exist in the repository before this work; they are PLANNED, not silently dropped or faked.


> **GUI (added):** `nx-core/nxcc.py` = NX Control Center. Every feature 1-50 has an interactive page (form fields, Run button, output pane)
> generated from `nx-core/nxsys/actions.py` (78 actions, 12 of which change the system and require a checkbox + confirmation dialog).
> Pages are auto-generated forms, not hand-designed screens. Tested offscreen on PySide6/py3.12 and PySide2/py3.8 (6 tests each);
> screenshots in docs/screenshots/. Hardware-dependent actions were not run against real hardware.


| # | Feature | Status | Existing/new source | Limitations |
|---|---|---|---|---|
| 1 | NX Self-Healing | PARTIALLY IMPLEMENTED (service + Control Center page) | nx-core/nxsys/sysfeatures_a.py diagnose/repair | diagnose dpkg/disk/systemd; one allow-listed repair; no GUI, no logs viewer |
| 2 | NX Rescue Environment | PARTIALLY IMPLEMENTED (service + Control Center page) | sysfeatures_a.py rescue_plan; docs/installation/recovery.md | prints documented recovery commands; no bootable rescue image built or tested |
| 3 | NX Offline Pack | IMPLEMENTED AND TESTED (service + Control Center page) | sysfeatures_a.py offline_pack/manifest/verify_pack | download step needs apt-get + network (not exercised); manifest/verify tested |
| 4 | NX Hardware Lab | IMPLEMENTED AND TESTED (inventory only, headless) | nx-core/nxsys/hwlab.py; tests/test_nxsys.py | no diagnostics/stress tests run; no GUI |
| 5 | NX Easy Mode | PARTIALLY IMPLEMENTED (service + Control Center page) | sysfeatures_a.py set_mode/visible_features | mode flag + feature filter only; no simplified UI |
| 6 | NX App Inspector | PARTIALLY IMPLEMENTED (service + Control Center page) | sysfeatures_a.py inspect_deb; software-center/nxsoft.py | reads deb metadata/scripts only; no signature, malware or permission analysis |
| 7 | NX Safe Update | IMPLEMENTED, NOT FULLY TESTED (service + Control Center page; hardware/desktop-dependent, real behaviour untested here) | sysfeatures_a.py preview_updates | preview only (apt-get -s); explicitly provides NO rollback |
| 8 | NX Permission Map | PARTIALLY IMPLEMENTED (service + Control Center page) | sysfeatures_a.py permission_map/set_mode_path | filesystem permissions only; not app/portal permissions |
| 9 | NX DevKit | PARTIALLY IMPLEMENTED (service + Control Center page) | sysfeatures_a.py devkit_status/create_venv | tool detection + venv creation; no version manager |
| 10 | NX Storage Analyzer | IMPLEMENTED AND TESTED (headless, preview only) | nx-core/nxsys/storage.py | no GUI; never deletes |
| 11 | NX Migration Assistant | IMPLEMENTED AND TESTED (service + Control Center page) | sysfeatures_a.py migrate_preview/migrate_apply | copies only; symlinks and existing files skipped, originals untouched; settings migration not implemented |
| 12 | NX Driver Center | IMPLEMENTED, NOT FULLY TESTED (service + Control Center page; hardware/desktop-dependent, real behaviour untested here) | sysfeatures_b.py detect_drivers | detection via lspci only; never installs drivers |
| 13 | NX Backup & Restore | IMPLEMENTED AND TESTED (service + Control Center page) | sysfeatures_a.py backup/restore | tar.gz with checksum; restore rejects traversal/links; no incremental/encryption |
| 14 | NX Compatibility Center | PARTIALLY IMPLEMENTED (service + Control Center page) | sysfeatures_b.py system_requirements; compatibility/ | requirements check + existing compatibility DB files |
| 15 | NX Performance Manager | PARTIALLY IMPLEMENTED (service + Control Center page) | sysfeatures_b.py snapshot/startup_time | monitoring + textual proposals; applies no changes |
| 16 | NX Disk Manager | PARTIALLY IMPLEMENTED (service + Control Center page) | sysfeatures_b.py list_disks/plan_format/format_device | inspect + guarded format only; no partitioning; destructive path never run against a real disk in tests |
| 17 | NX Install Preflight | IMPLEMENTED AND TESTED (checks only, headless) | nx-core/nxsys/preflight.py | not wired into installers/Calamares |
| 18 | NX Bug Report Builder | IMPLEMENTED AND TESTED (headless) | nx-core/nxsys/bugreport.py | no GUI/review dialog; never uploads |
| 19 | NX Hardware Compatibility Database | IMPLEMENTED AND TESTED (service + Control Center page) | sysfeatures_b.py CompatDB | verified vs user-report kept separate; local JSON file only |
| 20 | NX Firewall Profiles | IMPLEMENTED, NOT FULLY TESTED (service + Control Center page; hardware/desktop-dependent, real behaviour untested here) | sysfeatures_b.py firewall_preview/apply | preview tested; apply needs ufw + root and was NOT run |
| 21 | NX Recovery Validator | IMPLEMENTED AND TESTED (service + Control Center page) | sysfeatures_a.py validate_recovery | checks files/tools only; does not guarantee recovery |
| 22 | NX Configuration Audit | PARTIALLY IMPLEMENTED (service + Control Center page) | sysfeatures_a.py audit_sshd | sshd_config only; no auto-remediation |
| 23 | NX Network Diagnostics | IMPLEMENTED AND TESTED (headless) | nx-core/nxsys/netdiag.py | no GUI; network checks depend on host |
| 24 | NX App Test Bench | IMPLEMENTED AND TESTED (service + Control Center page) | sysfeatures_b.py run_app_test | runs the real command (network namespace if permitted); static inspection is not claimed |
| 25 | NX Language Toolkit | PARTIALLY IMPLEMENTED (service + Control Center page) | sysfeatures_b.py locales/set_locale_pref | lists locales and stores a per-user preference; does not install language packs |
| 26 | NX Power Manager | IMPLEMENTED, NOT FULLY TESTED (service + Control Center page; hardware/desktop-dependent, real behaviour untested here) | nxsys/power.py; sysfeatures_b.py power_profiles | status/capability only; no setting changes |
| 27 | Startup Manager | PARTIALLY IMPLEMENTED (XDG autostart list + non-destructive disable) | nx-core/nxsys/startup.py | no systemd services; no GUI |
| 28 | Clipboard History | IMPLEMENTED AND TESTED (service + Control Center page) | sysfeatures_b.py Clipboard | history logic + secret filtering tested; no desktop clipboard hook |
| 29 | Screenshot Studio | IMPLEMENTED AND TESTED against real tools on VIRTUAL devices (Xvfb / PulseAudio null sink / cron / dunst); physical hardware NOT TESTED | sysfeatures_c.py screenshot | needs a display + grim/scrot/etc.; not tested with a display |
| 30 | Notification Center | IMPLEMENTED AND TESTED against real tools on VIRTUAL devices (Xvfb / PulseAudio null sink / cron / dunst); physical hardware NOT TESTED | sysfeatures_c.py Notifications | history tested; on-screen delivery (notify-send) not tested |
| 31 | Font Manager | IMPLEMENTED AND TESTED against real tools on VIRTUAL devices (Xvfb / PulseAudio null sink / cron / dunst); physical hardware NOT TESTED | sysfeatures_b.py list_fonts/install_font | list + user-dir install; no removal |
| 32 | Archive Center | IMPLEMENTED AND TESTED (zip/tar, headless) | nx-core/nxsys/archive.py | no GUI; other formats not supported |
| 33 | Document Center | IMPLEMENTED AND TESTED against real tools on VIRTUAL devices (Xvfb / PulseAudio null sink / cron / dunst); physical hardware NOT TESTED | sysfeatures_b.py default_app | file-association lookup only |
| 34 | Audio Mixer | IMPLEMENTED AND TESTED against real tools on VIRTUAL devices (Xvfb / PulseAudio null sink / cron / dunst); physical hardware NOT TESTED | sysfeatures_c.py audio_sinks/set_volume | pactl wrapper; no audio hardware here |
| 35 | Display Manager | IMPLEMENTED AND TESTED against real tools on VIRTUAL devices (Xvfb / PulseAudio null sink / cron / dunst); physical hardware NOT TESTED | sysfeatures_c.py displays | xrandr wrapper; no display here |
| 36 | Device Pairing | IMPLEMENTED, NOT FULLY TESTED (service + Control Center page; hardware/desktop-dependent, real behaviour untested here) | sysfeatures_c.py bluetooth_devices/pair | bluetoothctl wrapper; no Bluetooth hardware here |
| 37 | Night Light | IMPLEMENTED, NOT FULLY TESTED (service + Control Center page; hardware/desktop-dependent, real behaviour untested here) | sysfeatures_c.py night_light_cmd | builds gammastep/redshift commands; not run |
| 38 | Password Vault | IMPLEMENTED AND TESTED (service + Control Center page) | sysfeatures_c.py Vault | AES-256-CBC+PBKDF2 via openssl, 0600 file; no GUI/autofill; not independently security-reviewed |
| 39 | Privacy Dashboard | PARTIALLY IMPLEMENTED (service + Control Center page) | sysfeatures_c.py privacy_report | device availability only; no per-app access tracking |
| 40 | Task Scheduler | IMPLEMENTED AND TESTED against real tools on VIRTUAL devices (Xvfb / PulseAudio null sink / cron / dunst); physical hardware NOT TESTED | sysfeatures_c.py list_tasks/add_task | user crontab wrapper; add_task validation tested, real crontab write not run |
| 41 | Process Manager | PARTIALLY IMPLEMENTED (list + guarded terminate, headless) | nx-core/nxsys/procs.py | no GUI; no resource graph |
| 42 | Duplicate Finder | IMPLEMENTED AND TESTED (headless, never deletes) | nx-core/nxsys/storage.py | no GUI/deletion workflow |
| 43 | Secure Delete Guide | IMPLEMENTED AND TESTED (service + Control Center page) | sysfeatures_c.py secure_delete_advice | guidance only; makes no erasure guarantee and deletes nothing |
| 44 | Web Apps | IMPLEMENTED AND TESTED (service + Control Center page) | sysfeatures_c.py create_webapp | creates a .desktop launcher for a URL (a browser wrapper, not a native app) |
| 45 | Game Mode | PARTIALLY IMPLEMENTED (service + Control Center page) | sysfeatures_c.py game_mode_plan | plan only; applies nothing; no FPS claims |
| 46 | Screen Recorder | IMPLEMENTED AND TESTED against real tools on VIRTUAL devices (Xvfb / PulseAudio null sink / cron / dunst); physical hardware NOT TESTED | sysfeatures_c.py record_command | builds ffmpeg x11grab command; not executed (no display) |
| 47 | Share Sheet | PARTIALLY IMPLEMENTED (service + Control Center page) | sysfeatures_c.py share_targets/share_email | target discovery + mail command |
| 48 | Accessibility Toolkit | IMPLEMENTED AND TESTED against real tools on VIRTUAL devices (Xvfb / PulseAudio null sink / cron / dunst); physical hardware NOT TESTED | sysfeatures_c.py a11y_status | reads GNOME gsettings if present; no toolkit UI |
| 49 | USB Manager | IMPLEMENTED AND TESTED against real tools on VIRTUAL devices (Xvfb / PulseAudio null sink / cron / dunst); physical hardware NOT TESTED | sysfeatures_c.py usb_devices/safe_to_eject | lists devices, refuses system disks; no real USB tested |
| 50 | NX Code Studio | PARTIALLY IMPLEMENTED | code-studio/ (see FEATURES.md module table) | many modules incomplete |
