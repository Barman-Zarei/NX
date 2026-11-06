# COMPATIBILITY

| Target | Status | Evidence |
|---|---|---|
| NX Studio layer (36 Python-core tests + extension smoke test), Linux, Python 3.12 | TESTED, PASS | CI job `code-studio` not yet run on GitHub |
| NX ISO amd64 on QEMU BIOS/UEFI (TCG) | see TESTING.md | |
| NX ISO inside VirtualBox/VMware on Windows 7 host, 4 GB RAM | NOT TESTED | 64-bit host + CPU virtualization needed; use dedicated virtual disk, never raw physical disks |
| 32-bit (i386) ISO | NOT SUPPORTED | dropped by the maintainer's decision |
| Old CPUs/GPUs/BIOS-MBR hardware | NOT TESTED | LEGACY has BIOS/MBR alongside-installer, untested on hardware |
| Non-ASCII paths | PASS in tests (Persian temp dirs) on Linux | |

Windows 7 VM safety: use a separate virtual disk file; do not attach the host's physical disk; do not choose installer options that erase/repartition the host disk.
