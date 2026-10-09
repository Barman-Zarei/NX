# NX OS

An Ubuntu-based, independent Linux distribution with a system-wide AI layer built around [Brok](https://github.com/Barman-Zarei/Brok).

> **Status: pre-alpha, Milestone 1 in progress.** Nothing here is a release. See `docs/releases/STATUS.md`
> for exactly what has been built and tested. NX is **not** an official Ubuntu product and is not endorsed by Canonical.

Copyright (c) 2026 Barman. See `LICENSES.md`.

## Layout
- `build/` – reproducible ISO build (`build/build-iso.sh`), config
- `windows/media-tool/` – Windows 7+ companion (Qt 5.15 / PySide2 on Python 3.8): ISO checksum verification (GUI is scaffolding)
- `ai/brok-adapter/` – planned Brok integration (not started)
- `tests/` – unit tests and VM boot tests
- `docs/` – architecture, installation, compatibility, security, releases

## Install (experimental, VM-tested only)
See `docs/installation/empty-disk.md`.

## Build (needs root on Ubuntu 24.04)
    sudo apt install debootstrap xorriso squashfs-tools grub-pc-bin grub-efi-amd64-bin mtools qemu-system-x86
    sudo build/build-iso.sh          # produces out/nx-os-<version>-amd64.iso + .sha256
    tests/vm/boot-test.sh out/*.iso  # QEMU boot test (TCG if no /dev/kvm)
