#!/bin/bash
# Installer tests (root, loop devices, QEMU, OVMF). usage: sudo tests/vm/test-installers.sh file.iso [empty|alongside|mbr|all]
# empty:     install onto an empty 3 GiB image; refusal on non-empty disk; boot BIOS, UEFI, UEFI+Secure Boot (MS keys).
# alongside: fake-Windows GPT disk (ESP + NTFS + free space); existing partitions must stay byte-identical; Secure Boot boot.
#            The firmware boot entry is SIMULATED by copying EFI/NX/* to EFI/BOOT in a test copy (no NVRAM in a VM).
set -uo pipefail
ISO="${1:?usage: test-installers.sh file.iso [empty|alongside|mbr|all]}"; WHICH="${2:-all}"; T="${NX_BOOT_TIMEOUT:-900}"
HERE="$(cd "$(dirname "$0")/../.." && pwd)"; W="$(mktemp -d /var/tmp/nxtest.XXXXXX)"; FAIL=0
ACCEL=tcg; [ -w /dev/kvm ] && ACCEL=kvm
export NX_PASSWORD=ci-test-password
pass() { echo "PASS: $*"; }
fail() { echo "FAIL: $*"; FAIL=1; }
[ "$(id -u)" -eq 0 ] || { echo "run as root"; exit 2; }
[ -f /usr/lib/shim/shimx64.efi.signed ] || { echo "install shim-signed and grub-efi-amd64-signed first"; exit 2; }
mkdir -p "$W/src"; xorriso -osirrox on -indev "$ISO" -extract /casper "$W/src/casper" >/dev/null 2>&1 || { echo "cannot extract ISO"; exit 2; }

# shellcheck disable=SC2054
boot_check() {  # image mode(bios|uefi|secboot)
  local img="$1" mode="$2" vars="$W/vars-$2.fd" i q log; local -a args=()
  log="$W/boot-$2-$(basename "$1").log"
  : > "$log"
  case "$mode" in
    uefi) cp /usr/share/OVMF/OVMF_VARS_4M.fd "$vars"
      args=(-drive "if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd" -drive "if=pflash,format=raw,file=$vars");;
    secboot) cp /usr/share/OVMF/OVMF_VARS_4M.ms.fd "$vars"
      args=(-machine q35,smm=on -global driver=cfi.pflash01,property=secure,value=on
            -drive "if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.secboot.fd" -drive "if=pflash,format=raw,file=$vars");;
  esac
  qemu-system-x86_64 -accel "$ACCEL" -m 1536 -drive "file=$img,format=raw,if=virtio" -display none -serial "file:$log" -no-reboot "${args[@]}" &
  q=$!
  for ((i = 0; i < T; i++)); do
    if grep -aq ' login: ' "$log"; then
      kill "$q" 2>/dev/null; wait "$q" 2>/dev/null
      if [ "$mode" = secboot ] && ! grep -aq 'Secure boot enabled' "$log"; then fail "$mode: login reached but kernel did not report Secure Boot enabled"; return; fi
      pass "$mode boot reached login ($(basename "$img"))"; return
    fi
    kill -0 "$q" 2>/dev/null || break
    sleep 1
  done
  kill "$q" 2>/dev/null; wait "$q" 2>/dev/null
  fail "$mode boot: no login prompt ($(basename "$img"))"; tail -c 600 "$log" | tr -cd '[:print:]\n'
}

test_empty() {
  local img="$W/empty.img" ld; truncate -s 3G "$img"; ld="$(losetup -fP --show "$img")"
  if "$HERE/installer/nx-install" --disk "$ld" --source "$W/src" --user cituser > "$W/empty-install.log" 2>&1; then pass "empty-disk install"; else fail "empty-disk install"; tail -5 "$W/empty-install.log"; fi
  if "$HERE/installer/nx-install" --disk "$ld" --source "$W/src" --user cituser > "$W/empty-refuse.log" 2>&1; then fail "installer did not refuse a non-empty disk"; else pass "refuses non-empty disk without --erase"; fi
  losetup -d "$ld"
  boot_check "$img" bios; boot_check "$img" uefi; boot_check "$img" secboot
}

test_alongside() {
  local img="$W/dual.img" ld ok; truncate -s 8G "$img"; ld="$(losetup -fP --show "$img")"; sleep 1
  parted -s "$ld" mklabel gpt; parted -s "$ld" mkpart ESP fat32 1MiB 101MiB; parted -s "$ld" set 1 esp on
  parted -s "$ld" mkpart windows ntfs 101MiB 3GiB; parted -s "$ld" set 2 msftdata on; sleep 1
  mkfs.vfat -F32 -n SYSTEM "${ld}p1" > /dev/null; mkntfs -F -Q -L Windows "${ld}p2" > /dev/null 2>&1
  head -c 1048576 /dev/urandom > "$W/bootmgfw.efi"
  mmd -i "${ld}p1" ::EFI ::EFI/Microsoft ::EFI/Microsoft/Boot; mcopy -i "${ld}p1" "$W/bootmgfw.efi" ::EFI/Microsoft/Boot/bootmgfw.efi
  head -c 3145728 /dev/urandom | dd of="${ld}p2" bs=1M seek=100 conv=notrunc 2> /dev/null
  sha256sum "${ld}p2" | cut -c1-64 > "$W/ntfs.before"; parted -sm "$ld" print | grep -E '^[12]:' > "$W/pt.before"
  if "$HERE/installer/nx-install-alongside" --disk "$ld" --source "$W/src" --user cituser --size-mib 3500 > "$W/along-plan.log" 2>&1; then fail "alongside ran without --yes-i-am-sure"; else pass "alongside refuses without explicit confirmation"; fi
  if "$HERE/installer/nx-install-alongside" --disk "$ld" --source "$W/src" --user cituser --size-mib 3500 --yes-i-am-sure "$ld" > "$W/along-install.log" 2>&1; then pass "alongside install"; else fail "alongside install"; tail -5 "$W/along-install.log"; fi
  sync
  ok=YES; sha256sum "${ld}p2" | cut -c1-64 | diff -q - "$W/ntfs.before" > /dev/null || ok=NO; [ $ok = YES ] && pass "NTFS partition byte-identical" || fail "NTFS partition changed"
  ok=YES; parted -sm "$ld" print | grep -E '^[12]:' | diff -q - "$W/pt.before" > /dev/null || ok=NO; [ $ok = YES ] && pass "existing partition table rows unchanged" || fail "partition rows changed"
  ok=YES; mcopy -i "${ld}p1" ::EFI/Microsoft/Boot/bootmgfw.efi - | cmp -s - "$W/bootmgfw.efi" || ok=NO; [ $ok = YES ] && pass "Windows boot file unchanged" || fail "Windows boot file changed"
  mdir -i "${ld}p1" ::EFI/BOOT > /dev/null 2>&1 && fail "EFI/BOOT was created/touched" || pass "EFI/BOOT untouched"
  mdir -i "${ld}p1" ::EFI/NX 2> /dev/null | grep -qi grubx64 && pass "EFI/NX installed" || fail "EFI/NX missing"
  losetup -d "$ld"
  local i="$img@@1048576" f   # simulate a firmware boot entry: put NX's loader chain at the fallback path in this test image only
  mmd -i "$i" ::EFI/BOOT
  for f in shimx64.efi:BOOTX64.EFI grubx64.efi:grubx64.efi grub.cfg:grub.cfg; do mcopy -i "$i" "::EFI/NX/${f%%:*}" "$W/x.tmp" && mcopy -D o -i "$i" "$W/x.tmp" "::EFI/BOOT/${f##*:}"; done
  boot_check "$img" secboot
}

test_mbr() {
  local img="$W/mbr.img" ld ok; truncate -s 8G "$img"; ld="$(losetup -fP --show "$img")"; sleep 1
  parted -s "$ld" mklabel msdos; parted -s "$ld" mkpart primary ntfs 1MiB 101MiB; parted -s "$ld" set 1 boot on
  parted -s "$ld" mkpart primary ntfs 101MiB 3GiB; sleep 1
  mkntfs -F -Q -L SystemReserved "${ld}p1" > /dev/null 2>&1; mkntfs -F -Q -L Windows "${ld}p2" > /dev/null 2>&1
  head -c 440 /dev/urandom > "$W/fake-boot-code.bin"; dd if="$W/fake-boot-code.bin" of="$ld" bs=440 count=1 conv=notrunc 2> /dev/null   # simulated Windows MBR boot code
  head -c 3145728 /dev/urandom | dd of="${ld}p2" bs=1M seek=100 conv=notrunc 2> /dev/null
  sha256sum "${ld}p1" | cut -c1-64 > "$W/m1.before"; sha256sum "${ld}p2" | cut -c1-64 > "$W/m2.before"
  dd if="$ld" bs=1 skip=440 count=38 2> /dev/null | sha256sum | cut -c1-64 > "$W/mtab.before"   # disk signature + partition entries 1-2
  if "$HERE/installer/nx-install-alongside-mbr" --disk "$ld" --source "$W/src" --user cituser --size-mib 3500 > "$W/mbr-plan.log" 2>&1; then fail "mbr installer ran without --yes-i-am-sure"; else pass "mbr installer refuses without explicit confirmation"; fi
  if "$HERE/installer/nx-install-alongside-mbr" --disk "$ld" --source "$W/src" --user cituser --size-mib 3500 --yes-i-am-sure "$ld" > "$W/mbr-install.log" 2>&1; then pass "mbr alongside install"; else fail "mbr alongside install"; tail -5 "$W/mbr-install.log"; fi
  sync
  ok=YES; sha256sum "${ld}p1" | cut -c1-64 | diff -q - "$W/m1.before" > /dev/null || ok=NO; [ $ok = YES ] && pass "MBR: partition 1 byte-identical" || fail "MBR: partition 1 changed"
  ok=YES; sha256sum "${ld}p2" | cut -c1-64 | diff -q - "$W/m2.before" > /dev/null || ok=NO; [ $ok = YES ] && pass "MBR: Windows partition byte-identical" || fail "MBR: Windows partition changed"
  ok=YES; dd if="$ld" bs=1 skip=440 count=38 2> /dev/null | sha256sum | cut -c1-64 | diff -q - "$W/mtab.before" > /dev/null || ok=NO
  [ $ok = YES ] && pass "MBR: disk signature and existing partition entries unchanged" || fail "MBR: partition table entries changed"
  debugfs -R "dump /boot/nx-mbr-backup.bin $W/backup.bin" "${ld}p3" > /dev/null 2>&1
  ok=YES; head -c 440 "$W/backup.bin" | cmp -s - "$W/fake-boot-code.bin" || ok=NO; [ $ok = YES ] && pass "original MBR boot code backed up" || fail "MBR boot code backup missing/different"
  ok=YES; [ "$(dd if="$ld" bs=1 skip=0 count=440 2> /dev/null | cmp -s - "$W/fake-boot-code.bin" && echo same)" != same ] || ok=NO; [ $ok = YES ] && pass "GRUB boot code now in MBR" || fail "MBR boot code not replaced"
  debugfs -R "cat /boot/grub/grub.cfg" "${ld}p3" 2> /dev/null | grep -q 'chainloader +1' && pass "grub.cfg has Windows chainload entry" || fail "no Windows chainload entry"
  losetup -d "$ld"
  boot_check "$img" bios
}

case "$WHICH" in empty) test_empty;; alongside) test_alongside;; mbr) test_mbr;; all) test_empty; test_alongside; test_mbr;; *) echo "bad selector"; exit 2;; esac
[ -n "${NX_LOG_DIR:-}" ] && { mkdir -p "$NX_LOG_DIR"; cp "$W"/*.log "$NX_LOG_DIR"/ 2> /dev/null; }
[ "$FAIL" -eq 0 ] && echo "ALL INSTALLER TESTS PASSED" || echo "SOME INSTALLER TESTS FAILED"
exit "$FAIL"
