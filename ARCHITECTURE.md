# ARCHITECTURE (actual, as of this work)

| Component | Path | Origin |
|---|---|---|
| ISO builder (debootstrap Ubuntu 24.04 "noble" minbase + casper + GRUB BIOS/UEFI) | build/ | NX original scripts; Ubuntu packages upstream |
| Installer scripts, Calamares config | installer/, desktop/overlay/etc/calamares | NX original config; Calamares upstream |
| Software Center + compatibility DB | software-center/, compatibility/ | NX original |
| AI layer: Brok adapter + permission broker | ai/service/ | NX original; Brok is a separate repo (Barman-Zarei/Brok) |
| Windows media tool | windows/ | NX original (main: PySide6, Win10+; LEGACY: PySide2, Win7 SP1+) |
| **NX Code Studio (Feature 50)** | code-studio/nxcs/ | NX original, stdlib core + Qt GUI |
| **nxsys system services** | nx-core/nxsys/ | NX original, stdlib only |

Layers: headless libraries (nxcs, nxsys) -> thin CLI/GUI. The GUI is a consumer of the libraries; every module is testable without a display.
Brok isolation: Brok is invoked through ai/service/brok_adapter.py behind the broker (allowlist, approval, audit log). Code Studio's Claude client is independent of Brok; Brok is NOT yet integrated into Code Studio.
Editor technology: Qt widgets (QPlainTextEdit). Monaco/Theia/Code-OSS were not adopted: they need Node/Electron, which does not run on the Windows 7 LEGACY target, and offline/licensing/trademark evaluation was not done. Consequence: no VS Code extension compatibility.
Upstream: Ubuntu (various licenses, trademark "Ubuntu" not used as NX branding), Calamares (GPL-3.0+), PySide6/PySide2 (LGPL-3.0). NX is not an official Ubuntu, Microsoft or VS Code product.
