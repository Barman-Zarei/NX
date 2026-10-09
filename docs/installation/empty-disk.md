# Empty-disk install (experimental CLI)
    sudo NX_PASSWORD='choose-a-password' installer/nx-install --disk /dev/sdX --source <dir containing casper/> --user NAME
- Layout: GPT, 1 MiB bios_grub, 256 MiB ESP, ext4 root. Boots with BIOS and UEFI (no Secure Boot).
- A disk with any partition table or mounted filesystem is refused unless `--erase --yes-i-am-sure /dev/sdX` is given. Everything on it is then destroyed.
- Verified only on a loop-device disk image in QEMU (see docs/releases/STATUS.md). Do NOT run on a disk with data you care about.
- Recovery: boot the NX live ISO, mount the root partition, and re-run `grub-install` for the disk.
- Not supported yet: dual boot, resizing, encryption, graphical installer.
