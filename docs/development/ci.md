# Continuous integration
`.github/workflows/ci.yml` (never run yet) has three jobs:
- **lint-unit:** shellcheck, unit tests (Python 3.12), compatibility DB validation, Brok adapter tests against a fresh clone of Brok, and the Windows-tool stack on Python 3.8.20 + PySide2 5.15.2.1 (headless).
- **iso-and-vm-tests:** builds the ISO, verifies checksums, runs BIOS/UEFI live boot tests and `tests/vm/test-installers.sh` (empty-disk install, refusal checks, alongside install with byte-identity checks on a fake Windows disk, Secure Boot boots). Uses /dev/kvm when the runner has it; otherwise TCG (slow, raise `NX_BOOT_TIMEOUT`). Logs and the ISO are uploaded as an artifact.
- **desktop-flavor (manual):** builds the untested XFCE flavor and uploads screenshots. A screenshot only counts as evidence after a human looks at it.
Rules: do not call something verified until the job output shows the PASS lines; read the logs, a green check alone is not a release.
