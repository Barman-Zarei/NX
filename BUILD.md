# BUILD

ISO (Ubuntu 24.04 host, root): `sudo apt-get install debootstrap xorriso squashfs-tools grub-pc-bin grub-efi-amd64-bin mtools dosfstools qemu-system-x86 ovmf`
then `sudo DEBIAN_FRONTEND=noninteractive build/build-iso.sh` -> `out/nx-os-<ver>-amd64.iso` + `.sha256`. Desktop flavor: `NX_FLAVOR=desktop` (UNTESTED here).
Verify: `(cd out && sha256sum -c *.sha256)`, `file out/*.iso`, `xorriso -indev out/*.iso -report_el_torito plain`, `tests/vm/boot-test.sh` and `boot-test-uefi.sh`.
NX Studio Code (submodule): `git submodule update --init code-studio`, then follow `code-studio/docs/BUILDING.md` / its `build` workflow (Electron 22, Windows 7 SP1+). NX layer tests without building the editor: `cd code-studio/extensions/nx-studio/python && python -m unittest discover -s tests` and `node code-studio/extensions/nx-studio/test/smoke.js`.
NX APP TRANSLATOR: `sh windows/nx-app-translator/shim/build.sh` (mingw-w64), tests `python -m unittest discover -s windows/nx-app-translator/tests`; see windows/nx-app-translator/README.md.
Release: push a tag `vX.Y.Z[-suffix]`; `.github/workflows/release.yml` runs tests, builds, verifies and signs (needs secrets NX_GPG_PRIVATE_KEY / NX_GPG_PASSPHRASE; refuses to publish unsigned). Never run on GitHub yet.
The ISO is NOT committed (out/ is gitignored); publish it as a release asset.

**LEGACY note:** the Windows media tool GUI imports PySide2 only. Use Python 3.8 + `PySide2==5.15.2.1` (last PySide2; Windows 7 SP1+). Never install PySide6 here.
