# TESTING

All results below come from commands actually run in this session's container
(Ubuntu 24.04, 1 CPU, 4 GB RAM, no KVM, so QEMU uses slow TCG emulation). Nothing here was run on Windows or real hardware.

| Test | Command | Environment | Result |
|---|---|---|---|
| Code Studio unit + offscreen GUI | `QT_QPA_PLATFORM=offscreen PYTHONPATH=nx-core:code-studio python3 -m unittest discover -s code-studio/tests -t code-studio/tests` | Python 3.12 + PySide6 6.12 | PASS (23 tests) |
| Code Studio, LEGACY | same command in the LEGACY worktree | Python 3.8.20 + PySide2 5.15.2.1 | PASS (23 tests) |
| nx-core (nxsys) | `python3 -m unittest discover -s nx-core/tests -t nx-core/tests` | Python 3.12 and 3.8 | PASS (7 tests each) |
| nx-core feature services (34 tests, features 1-49 headless) | `python3 -m unittest discover -s nx-core/tests -t nx-core/tests` | Python 3.12 and 3.8 | PASS (34 each) |
| Pre-existing unit tests | `python3 -m unittest discover -s tests/unit` | Python 3.12 | PASS (32 tests, 9 skipped) |
| Workflow YAML syntax | PyYAML `safe_load` on `.github/workflows/*.yml` | local | PASS (syntax only; NOT run on GitHub) |
| ISO build | `NX_WORK=/var/tmp/nx-build bash build/build-iso.sh` | debootstrap, local | PASS (first build; later superseded by the from-scratch rebuild below) |
| ISO structure | `xorriso -indev ... -report_el_torito plain`, `sha256sum -c` | local | PASS: ISO 9660, El Torito BIOS + UEFI entries, checksum OK |
| ISO boot, BIOS (QEMU TCG) | `tests/vm/boot-test.sh <iso> 1100` | QEMU TCG, 1.5 GB | **PASS**: reached serial login/shell marker. Earlier runs FAILED; root cause: `BUILD_SYSTEM="NX"` in /etc/casper.conf made casper run `modprobe "" -b overlay`. Fixed with `BUILD_SYSTEM="Ubuntu"` in build/build-iso.sh. |
| ISO boot, UEFI (OVMF) | `tests/vm/boot-test-uefi.sh <iso> 1100` | QEMU TCG + OVMF, 2 GB | **PASS**: reached login marker (same ISO as BIOS PASS) |
| NX Control Center GUI (all 50 features listed, 33 read-only checks) | `QT_QPA_PLATFORM=offscreen PYTHONPATH=nx-core python3 -m unittest nx-core/tests/test_controlcenter.py` | py3.12/PySide6 and py3.8/PySide2 | PASS (3 tests each) |
| Brok adapter vs REAL Brok (cloned from GitHub), non-root user | `su tester -c 'NX_BROK_DIR=/tmp/Brok python3 -m unittest tests.unit.test_brok_adapter -v'` | Python 3.12, offline (no model/API) | PASS (8 tests, 0 skipped; real-Brok `doctor` and offline `ask` return status, no crash) |
| Full tests/unit as non-root with Brok present | same user, `unittest discover -s tests/unit` | Python 3.12 | PASS (32 tests, 4 skipped) |
| Static check: all Python | `python3 -m pyflakes <dirs>` | local | PASS for errors (no undefined names); only unused-import warnings |
| Shell lint as in CI | `shellcheck -S warning build/build-iso.sh installer/* tests/vm/*.sh` | local | PASS |
| CI workflows inspected with Pipeline Lab | `nxcs.pipeline.inspect` | local | DONE: ci.yml has 4 jobs, release.yml 1; actions (checkout, upload-artifact, action-gh-release), sudo/apt/KVM steps cannot run locally -> NOT executed |
| Installer on ISO (empty-disk mode): install, refusal on non-empty disk, boot installed image BIOS/UEFI/UEFI+SecureBoot | `sudo tests/vm/test-installers.sh <iso> empty` | QEMU TCG, loop images | **PASS** (ALL INSTALLER TESTS PASSED) |
| Installer alongside a fake-Windows GPT disk (NTFS partition byte-identical, partition rows unchanged, EFI/BOOT untouched, SecureBoot boot) | `sudo tests/vm/test-installers.sh <iso> alongside` | QEMU TCG, fake disk (NOT a real Windows install) | **PASS** |
| ISO rebuilt FROM SCRATCH with the patched build script, then boot BIOS + UEFI | `NX_WORK=/var/tmp/nx-build2 bash build/build-iso.sh`; boot-test*.sh | local | **PASS** / **PASS** (reproducible) |
| Windows 7 host VM | - | - | NOT TESTED (no Windows 7 available) |
| Live Claude API request | - | - | NOT TESTED (no API key); only a labelled mock was used |
| GitHub Actions execution | - | - | NOT TESTED (no push access) |

Known limits: the 9 skipped tests are skipped by the pre-existing suite itself (missing optional environment);
Code Studio's GUI tests run offscreen, not on a real display.

Boot tests prove only that the kernel/casper reach a login prompt in an emulator. Graphical session, installation and real hardware are NOT TESTED.

Still NOT TESTED: graphical desktop flavor, real hardware, Windows 7 host VM, live Claude API, GitHub-hosted CI. LEGACY unit tests (36) PASS on Python 3.8 + PySide2.
