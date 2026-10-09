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
