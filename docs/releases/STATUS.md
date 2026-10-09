# Status (only facts that were actually run)

## Session 1 (2026-10-08, build VM: Ubuntu 24.04, 1 CPU, 4 GB RAM, no /dev/kvm)
**Actually done**
- Installed debootstrap, xorriso, squashfs-tools, grub, qemu, shellcheck (blocked nodesource apt source disabled).
- `build/build-iso.sh` built a real hybrid ISO: `out/nx-os-0.0.1-pre-amd64.iso` (149 MB) + `.sha256`. Listing shows casper/{vmlinuz,initrd,filesystem.squashfs}, /boot/grub, EFI image. Checksum verified with `nxverify.py`.
- Unit tests `tests/unit/test_nxverify.py`: 3 passed (Python 3.12; Python 3.8 not tested).
- QEMU boot (BIOS, TCG, 1.5 GB RAM): kernel + casper reached a serial **login prompt**. This is the only boot evidence. UEFI boot, graphical session and installation were NOT tested.

**Observed problems (first image)**
- Casper overrode branding: hostname/user were `ubuntu`, banner "Ubuntu 24.04 LTS", and `casper-md5check` FAILED (no md5sum.txt).
- Test marker `nx login:` did not match (marker changed to ` login: `).
- Fixes (`/etc/casper.conf`, `/etc/issue`, md5sum.txt) are written in `build-iso.sh` but NOT yet rebuilt or re-tested.

**Not implemented:** installer, desktop, Brok adapter, Software Center, Secure Boot, 32-bit, ARM64, dual boot; Windows GUI is untested scaffolding.
**Next:** rebuild, rerun boot test, then Calamares empty-disk install in a VM.

## Session 1, update
- Third build added kernel args `username=nx hostname=nx userfullname=NX` in `build/config/grub.cfg`.
- QEMU BIOS/TCG boot of that ISO: PASS. Serial output showed the banner "NX OS 0.0.1 (pre-alpha)" and the prompt `nx login:`; no md5check failure or "user does not exist" lines were matched by the grep (full log not archived).
- Still untested: UEFI, graphical session, installation, networking, persistence. Live login is nx/nx (live image only).

## Session 1, final
- UEFI boot (OVMF, TCG, `tests/vm/boot-test-uefi.sh`): PASS, reached login. Secure Boot not tested/supported.
- Added `ai/service/broker.py` (allowlist, approval, untrusted-source block, audit log) and `compatibility/validate.py`. `python3 -m unittest discover -s tests/unit`: 13 tests passed (Python 3.12).
- Added scaffolds (NOT functional): `installer/calamares/`, `.github/workflows/ci.yml` (never run on GitHub).
- Brok adapter, desktop, Software Center, installer integration, dual boot: not implemented.

## Session 1, installer (2026-10-08)
**Ran and passed**
- `installer/nx-install` on a fresh 3 GiB loop-device image (final script, one clean run): rc=0, log in `docs/releases/install-log-2026-10-08.txt`.
- Same disk booted with NO ISO attached: BIOS/TCG PASS (`nx login:`), UEFI/OVMF/TCG PASS (`nx login:`) via `tests/vm/boot-disk-test.sh`.
- Safety checks verified by hand: bad source, non-block-device and invalid user name are rejected; a disk with an existing partition table is refused without `--erase --yes-i-am-sure DISK`.
- Not directly tested: refusal of a mounted disk; wrong confirmation string.
**Limits**
- Only loop-device images in QEMU/TCG. No physical disk, no KVM, no Secure Boot, no dual boot, no graphical installer, no login test after boot (only the prompt was seen), no network/audio/graphics tests.
- Build VM kernel lacks vfat, so the ESP is written with mtools and `grub-mkstandalone`; unverified on a standard kernel.

## Session 1, Brok adapter (2026-10-09)
- `ai/service/brok_adapter.py` runs the real Brok CLI (`python -m brok.cli`, Brok 0.2.0 clone at /home/claude/Brok) as an isolated subprocess: refuses root, stdin=/dev/null so Brok's own approver denies all approvals, untrusted text cannot drive `code`/`fix`, statuses instead of exceptions, `enabled=False` switch.
- `tests/unit/test_brok_adapter.py`: 7 tests passed as a NON-root user (against real Brok `doctor` offline: all providers unreachable, parsed correctly; `ask` offline returned a status without crashing). As root, 5 skip by design.
- NOT tested: a configured local model (no Ollama here), cloud providers, voice, desktop integration, PolicyKit, installing Brok into the ISO, Brok dependencies on the target image.
- Brok mainline needs Qt 6; Windows 7 stays unsupported there (legacy branch plan unchanged).

## Session 1, alongside install (2026-10-09)
**Ran** (manual procedure, scripts in `installer/`): 8 GiB GPT image with ESP (FAT32 + dummy `EFI/Microsoft/Boot/bootmgfw.efi`), 2.9 GiB NTFS "windows" partition (mkntfs, random marker data), 5 GiB free.
- Without `--yes-i-am-sure`: prints plan and refuses. On non-GPT/empty disk: refuses. After a bug fix (ESP flag and free-space parsing, found by the first runs refusing wrongly), install rc=0.
- After install: NTFS partition SHA-256 identical, partition table rows 1-2 identical, `bootmgfw.efi` hash identical, `EFI/BOOT` not created, new ext4 partition 3 and `EFI/NX/grubx64.efi` present, generated grub.cfg has "NX OS" and "Windows" entries.
- UEFI/OVMF/TCG boot of that disk reached `nx login:`, **but only after I copied `grubx64.efi` to `EFI/BOOT/BOOTX64.EFI` in a test copy** to simulate a firmware boot entry (no NVRAM entry could be created in the VM).
**Not verified:** real Windows (chainload entry only checked as text; bootmgfw.efi is a dummy), efibootmgr path, BitLocker, Secure Boot, MBR/BIOS, real disks, repeat installs.
- `.github/workflows/ci.yml` rewritten (lint, unit tests, ISO build, BIOS+UEFI boot tests); never run on GitHub.

## Session 1, Secure Boot, Python 3.8 GUI, Software Center (2026-10-09)
**Secure Boot (QEMU/OVMF with Microsoft keys pre-enrolled, `OVMF_CODE_4M.secboot.fd`, TCG)**
- Chain: Ubuntu-signed shim -> Ubuntu-signed GRUB -> Ubuntu-signed kernel. Boot log showed "UEFI Secure Boot is enabled", "secureboot: Secure boot enabled", kernel lockdown; reached `nx login:`.
- `build-iso.sh` now adds shim-signed/grub-efi-amd64-signed/parted/mtools etc. to the image; ISO rebuilt (168 MB). Empty-disk install from that ISO (installer picks signed shim+grub when present, else warns and falls back to unsigned GRUB) booted under Secure Boot: PASS.
- Alongside install with the signed chain on a fake-Windows disk: NTFS hash and partition rows unchanged, EFI/BOOT not created, EFI/NX files present; Secure Boot boot PASS **after copying EFI/NX/* into EFI/BOOT in a test copy** (simulating a firmware boot entry).
- Not verified: real firmware, real Windows, efibootmgr entry creation, custom-signed kernels/modules (MOK), disk encryption, Secure Boot on legacy BIOS (n/a). Signed binaries are Canonical's/Microsoft's: NX has no signing keys of its own.
**Windows 7 media tool**
- Python 3.8.20 (via uv, python-build-standalone) + PySide2 5.15.2.1 installed on Linux; all unit tests run on 3.8 and the GUI window logic passed headless (`QT_QPA_PLATFORM=offscreen`). Never run on Windows 7 or Windows at all; no .exe built; USB writing not implemented.
**Software Center core** (`software-center/nxsoft.py`): search/info over apt-cache (real call checked), install/remove preview + approval gate, name validation, compatibility record lookup. 6 unit tests pass. No GUI, no Flatpak/AppImage/Wine integration, no actual install performed.
**Dropped by the maintainer's decision:** 32-bit (i386) edition.
**Still not built:** NX desktop (login, shell, settings, file manager), graphical installer (Calamares), Brok inside the ISO / local-model test, voice, PolicyKit integration, ARM64, physical-hardware tests, update channels, signed NX releases.

## Session 1, CI preparation (2026-10-09)
- `tests/vm/test-installers.sh` turns the manual installer procedures into a script. Run here (alongside part only, TCG): all PASS lines (confirmation refusal, install, NTFS byte-identical, partition rows, Windows boot file, EFI/BOOT untouched, EFI/NX present, Secure Boot boot). The `empty` part of the script was NOT run as a script (its steps were verified manually earlier).
- `.github/workflows/ci.yml` rewritten (lint, unit on 3.12 and 3.8/PySide2, Brok adapter tests, ISO build, BIOS/UEFI boot, installer tests, manual desktop job). Never run on GitHub.
- Desktop flavor (`NX_FLAVOR=desktop`, XFCE + lightdm) and `tests/vm/desktop-screenshot.sh` are written but UNTESTED. lightdm autologin file is not yet removed by the installers after install (known gap).
- `docs/security/signing.md` explains signatures; `docs/development/ci.md` explains CI.

## Session 1, final push before CI (2026-10-09)
**Verified here:** GTK3 Software Center GUI window logic (4 tests, real GTK under xvfb); `nx-ai` CLI + 1 new test, run as non-root against real Brok; installers now remove the lightdm live-autologin file (grep-checked, not boot-tested).
**Written, to be verified by CI/hardware (nothing below has run):**
- Desktop flavor `NX_FLAVOR=desktop`: XFCE + lightdm, Calamares + `/etc/calamares` config (settings, unpackfs, partition, bootloader, users, shellprocess, NX branding), os-prober, Brok cloned to `/opt/brok` (license + NOTICE kept), `nx-ai`, Software Center GUI, NX wallpaper/dark theme setup script, polkit/pkexec. CI job `desktop-flavor` checks image contents, boots with a virtual display and fails if the last screenshot is blank. It does NOT run a Calamares installation: that needs a manual run (Calamares path is not Secure Boot capable; the CLI installers are).
- `release.yml`: build, boot and installer tests, package manifest, SHA256SUMS, detached GPG signature from repository secrets, pre-release vs stable by tag. Requires the maintainer to create the GPG key and secrets.
- Not started: ARM64, local-model (Ollama) test, voice, PolicyKit action files for NX tools, Windows .exe packaging, update channel/APT repo.
