# COMPATIBILITY

| Target | Status | Evidence |
|---|---|---|
| Code Studio core + GUI, Python 3.12 + PySide6 6.12 (Linux, offscreen) | TESTED, PASS | 23 + GUI tests |
| Code Studio core + GUI, Python 3.8.20 + PySide2 5.15.2.1 (Linux, offscreen) | TESTED, PASS | same suite |
| Code Studio on real Windows 7 | NOT TESTED | no Windows host; saferun is POSIX-tuned (rlimits Linux only), bash/sleep-based tests are POSIX |
| Code Studio on Windows (any) | NOT TESTED | |
| LEGACY GUI imports only PySide2 (never PySide6/Qt6) | PASS (static grep check) | CI step `code-studio-legacy` |
| NX ISO amd64 on QEMU BIOS/UEFI (TCG) | see TESTING.md | |
| NX ISO inside VirtualBox/VMware on Windows 7 host, 4 GB RAM | NOT TESTED | 64-bit host + CPU virtualization needed; use dedicated virtual disk, never raw physical disks |
| 32-bit (i386) ISO | NOT SUPPORTED | dropped by the maintainer's decision |
| Old CPUs/GPUs/BIOS-MBR hardware | NOT TESTED | LEGACY has BIOS/MBR alongside-installer, untested on hardware |
| Non-ASCII paths | PASS in tests (Persian temp dirs) on Linux | |

Windows 7 VM safety: use a separate virtual disk file; do not attach the host's physical disk; do not choose installer options that erase/repartition the host disk.
