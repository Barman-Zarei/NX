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
