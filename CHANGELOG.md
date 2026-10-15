# CHANGELOG
## Unreleased
- Added NX Code Studio (code-studio/): headless core + Qt GUI; this branch (LEGACY) = PySide2 5.15 (Python 3.8).
- Added nx-core/nxsys: Hardware Lab, Install Preflight, Storage Analyzer, Duplicate Finder, Archive Center, Network Diagnostics, Process Manager, Bug Report Builder, Power/Startup (read side).
- CI: new code-studio jobs (main: Python 3.12 + PySide6; LEGACY: Python 3.8 + PySide2). release.yml: tag format validation, concurrency, pre-release tests, ISO structure verification.
- build-iso.sh: non-interactive dpkg flags built in.
- Docs: FEATURE_PRESERVATION, FEATURES, ARCHITECTURE, COMPATIBILITY, BUILD, TESTING.
