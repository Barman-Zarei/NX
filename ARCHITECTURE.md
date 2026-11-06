# ARCHITECTURE (actual, as of this work)

| Component | Path | Origin |
|---|---|---|
| ISO builder (debootstrap Ubuntu 24.04 "noble" minbase + casper + GRUB BIOS/UEFI) | build/ | NX original scripts; Ubuntu packages upstream |
| Installer scripts, Calamares config | installer/, desktop/overlay/etc/calamares | NX original config; Calamares upstream |
| Software Center + compatibility DB | software-center/, compatibility/ | NX original |
| AI layer: Brok adapter + permission broker | ai/service/ | NX original; Brok is a separate repo (Barman-Zarei/Brok) |
| Windows media tool | windows/ | NX original (main: PySide6, Win10+; LEGACY: PySide2, Win7 SP1+) |
| **NX Studio Code (Feature 50)** | code-studio/ (git submodule, repo Barman-Zarei/NX-Studio-Code, branch LEGACY: Electron 22.3.27, Windows 7 SP1+) | separate project; replaces the former in-tree Python/Qt `nxcs` |
| **NX APP TRANSLATOR (LEGACY only)** | windows/nx-app-translator/ | NX original; Python 3.8 + pefile, C shim `nxshim7.dll` |
| **nxsys system services** | nx-core/nxsys/ | NX original, stdlib only |

Layers: headless libraries (nxcs, nxsys) -> thin CLI/GUI. The GUI is a consumer of the libraries; every module is testable without a display.
Brok isolation: Brok is invoked through ai/service/brok_adapter.py behind the broker (allowlist, approval, audit log). NX Studio Code's Claude client is independent of Brok; Brok is NOT yet integrated.
Editor technology: NX Studio Code = Code-OSS fork (MIT) with the NX extension. On LEGACY it is built on Electron 22 (Chromium 108) - the last Electron line that runs on Windows 7. Chromium 108 gets no security fixes any more.
Upstream: Ubuntu (various licenses, trademark "Ubuntu" not used as NX branding), Calamares (GPL-3.0+), PySide6/PySide2 (LGPL-3.0). NX is not an official Ubuntu, Microsoft or VS Code product.
