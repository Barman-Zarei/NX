# COMPATIBILITY

| Target | Status | Evidence |
|---|---|---|
| NX Studio Code (LEGACY, Electron 22) on real Windows 7 | NOT TESTED | upstream project states it was never booted on Win7; see code-studio/docs/LEGACY.md |
| NX Studio layer (36 Python-core tests + extension smoke test), Linux | TESTED, PASS (3.12 locally; CI job `code-studio-legacy` uses 3.8, not yet run on GitHub) | |
| NX APP TRANSLATOR: unit tests, Python 3.8 and 3.12 | TESTED, PASS (see TESTING.md) | |
| NX APP TRANSLATOR: translated x86 + x64 programs, native installer stub, Electron 30->22 swap executed under Wine | TESTED, PASS | proxy only: Wine implements the new APIs too |
| NX APP TRANSLATOR / nxshim7.dll on real Windows 7 (x86 and x64) | NOT TESTED | no Windows 7 available |
| NX ISO amd64 on QEMU BIOS/UEFI (TCG) | see TESTING.md | |
| NX ISO inside VirtualBox/VMware on Windows 7 host, 4 GB RAM | NOT TESTED | 64-bit host + CPU virtualization needed; use dedicated virtual disk, never raw physical disks |
| 32-bit (i386) ISO | NOT SUPPORTED | dropped by the maintainer's decision |
| Old CPUs/GPUs/BIOS-MBR hardware | NOT TESTED | LEGACY has BIOS/MBR alongside-installer, untested on hardware |
| Non-ASCII paths | PASS in tests (Persian temp dirs) on Linux | |

Windows 7 VM safety: use a separate virtual disk file; do not attach the host's physical disk; do not choose installer options that erase/repartition the host disk.
