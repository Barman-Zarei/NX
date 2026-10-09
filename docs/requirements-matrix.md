# Requirements matrix (evidence = what actually ran on 2026-10-08)
| ID | Requirement | Status | Source | Test | Limits |
|---|---|---|---|---|---|
| NX-BOOT-1 | Bootable live ISO (BIOS) | Tested (QEMU/TCG, reached login) | build/build-iso.sh | tests/vm/boot-test.sh | no real hardware, no KVM |
| NX-BOOT-2 | UEFI boot | Tested (OVMF/TCG, reached login) | tests/vm/boot-test-uefi.sh | OVMF/TCG | Secure Boot not supported |
| NX-INST-1 | Empty-disk install (CLI) | Tested on loop image, BIOS+UEFI boot to login | installer/nx-install | tests/vm/boot-disk-test.sh | no physical disk; GUI installer (Calamares) is scaffold only |
| NX-INST-2 | Alongside install (UEFI/GPT) | Tested on a fake-Windows disk image: existing partitions byte-identical, boots to login with simulated boot entry | installer/nx-install-alongside | manual procedure in STATUS.md | dummy bootmgfw, no real Windows, no Secure Boot/BIOS/BitLocker |
| NX-AI-1 | Safe tool broker | Implemented + unit tested (8 tests) | ai/service/broker.py | tests/unit/test_broker.py | no Brok, no PolicyKit yet |
| NX-AI-2 | Brok adapter (CLI subprocess) | Implemented; 7 tests pass as non-root; real Brok offline path verified | ai/service/brok_adapter.py | tests/unit/test_brok_adapter.py | no local model/cloud test, not in ISO |
| NX-APP-1 | Compatibility DB + validator | Implemented + unit tested | compatibility/ | tests/unit/test_compat.py | 1 placeholder entry |
| NX-WIN-1 | Windows 7+ media tool | Core + GUI logic tested on Linux with Python 3.8.20 / PySide2 5.15.2.1 (offscreen); never run on Windows | windows/media-tool | tests/unit/test_nxverify.py | no Win7/Py3.8 test |
| NX-DESK-1 | NX desktop | Planned | - | none | - |
| NX-SC-1 | Software Center | CLI core implemented, 6 unit tests | software-center/nxsoft.py | tests/unit/test_nxsoft.py | no GUI, no Flatpak/Wine, no real install |
| NX-SEC-1 | Secure Boot | Tested in QEMU/OVMF(MS keys): signed shim+grub+kernel boot, lockdown on | installer/*, build/build-iso.sh | manual (STATUS.md) | no real firmware, no own keys/MOK |
| NX-ARCH-1 | 32-bit | Dropped by maintainer | - | - | - |
| NX-ARCH-2 | ARM64 | Not started | - | none | - |
