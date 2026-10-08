# Architecture decisions (proposed)
1. **Base:** Ubuntu 24.04 LTS "noble" (standard support to 2029). Built with debootstrap + casper, so upstream packages stay unmodified.
2. **Arch:** amd64 primary, generic x86-64 baseline (no AVX assumptions in NX code). i386 is NOT a bootable Ubuntu 24.04 edition; a separate legacy edition on a Debian-compatible base is to be evaluated. ARM64: not started.
3. **Desktop:** NX shell layer on top of an existing compositor/toolkit (GNOME or KDE decision pending, Milestone 3). No custom display server.
4. **Installer:** Calamares (Milestone 2). Never auto-resize or erase without explicit confirmation.
5. **AI:** user-level service (not root) + Brok adapter; privileged actions only via PolicyKit with allowlisted tools, previews, audit log. The OS must work with AI disabled.
6. **Windows host tools:** isolated in `windows/`. Qt 5.15 + PySide2 + Python 3.8 is the only practical stack for Windows 7 SP1. Brok mainline (Qt 6) does not support Windows 7.
7. **Boot media:** grub-mkrescue hybrid ISO (BIOS + UEFI). Secure Boot: NOT supported yet (unsigned GRUB image).
