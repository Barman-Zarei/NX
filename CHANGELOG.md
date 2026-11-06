# CHANGELOG
## Unreleased
- LEGACY: code-studio/ is now a git submodule of NX-Studio-Code (branch LEGACY, Electron 22); the in-tree Python/Qt nxcs was removed. Control Center action launches a built NX Studio Code. CI job `code-studio-legacy` tests the NX layer.
- LEGACY: added NX APP TRANSLATOR (windows/nx-app-translator/) + nxshim7.dll: analyze, patch PE/imports for Windows 7, Electron 22 swap, rebuild installer. Brok-supervised (fail-closed gates + audit log), decompile stage, Brok+NX Studio Code adaptation loop. CI job `app-translator`; stub + translator exe built in `windows-build-test`.
- Added nx-core/nxsys: Hardware Lab, Install Preflight, Storage Analyzer, Duplicate Finder, Archive Center, Network Diagnostics, Process Manager, Bug Report Builder, Power/Startup (read side).
- CI: new code-studio jobs (main: Python 3.12 + PySide6; LEGACY: Python 3.8 + PySide2). release.yml: tag format validation, concurrency, pre-release tests, ISO structure verification.
- build-iso.sh: non-interactive dpkg flags built in.
- Docs: FEATURE_PRESERVATION, FEATURES, ARCHITECTURE, COMPATIBILITY, BUILD, TESTING.

## Unreleased (this session)
- Code Studio core + GUI (PySide6 on main, PySide2 5.15 on LEGACY), 23 tests.
- nx-core: headless services for most of features 1-49 with 34 tests; statuses in FEATURE_PRESERVATION.md.
- build-iso.sh: non-interactive dpkg, MODULES=most. ISO builds; BIOS boot test currently FAILS (see TESTING.md).
