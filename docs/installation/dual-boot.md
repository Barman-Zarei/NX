# Alongside install (experimental, UEFI/GPT only)
    sudo NX_PASSWORD='...' installer/nx-install-alongside --disk /dev/sdX --source <dir with casper/> --user NAME [--size-mib N] --yes-i-am-sure /dev/sdX
Run without `--yes-i-am-sure` to only print the plan. It requires: existing GPT disk, an existing ESP, >= 4096 MiB contiguous free space. It creates ONE new partition, adds `EFI/NX/grubx64.efi` to the existing ESP and a GRUB menu with a "Windows" chainload entry if `EFI/Microsoft/Boot/bootmgfw.efi` exists. It never formats/resizes/deletes existing partitions and never touches `EFI/BOOT` or `EFI/Microsoft`.
You must have free space already: shrink the Windows partition from Windows Disk Management first (back up data; suspend BitLocker; disable Fast Startup). NX does not resize NTFS.
If the firmware has no NX boot entry, `efibootmgr` is attempted only when booted in UEFI mode; otherwise add `\EFI\NX\grubx64.efi` manually. Secure Boot: not supported (unsigned). MBR/legacy BIOS dual boot: not supported.
Recovery: in firmware boot menu choose Windows Boot Manager; to remove NX delete the NX partition and `EFI/NX`.
