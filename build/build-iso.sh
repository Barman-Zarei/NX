#!/bin/bash
# NX OS minimal live ISO builder. Run as root on Ubuntu 24.04. Produces a real hybrid ISO (BIOS+UEFI via grub-mkrescue).
set -euo pipefail
VERSION="${NX_VERSION:-0.0.1-pre}"
FLAVOR="${NX_FLAVOR:-base}"   # base (CLI, tested) | desktop (XFCE, UNTESTED: verify with tests/vm/desktop-screenshot.sh)
SUITE=noble
MIRROR="${NX_MIRROR:-http://archive.ubuntu.com/ubuntu}"
ROOT="${NX_WORK:-/var/tmp/nx-build}"
OUT="$(cd "$(dirname "$0")/.." && pwd)/out"
HERE="$(cd "$(dirname "$0")" && pwd)"
[ "$(id -u)" -eq 0 ] || { echo "run as root"; exit 1; }
mkdir -p "$ROOT" "$OUT"
CH="$ROOT/chroot"; ISO="$ROOT/iso"
if [ ! -f "$CH/.bootstrapped" ]; then
  rm -rf "$CH"
  debootstrap --variant=minbase --arch=amd64 "$SUITE" "$CH" "$MIRROR"
  touch "$CH/.bootstrapped"
fi
mount --bind /dev "$CH/dev"; mount -t proc proc "$CH/proc"; mount -t sysfs sys "$CH/sys"
trap 'umount -l "$CH/dev" "$CH/proc" "$CH/sys" 2>/dev/null || true' EXIT
cat > "$CH/etc/apt/sources.list" <<EOL
deb $MIRROR $SUITE main universe
deb $MIRROR $SUITE-updates main universe
deb http://security.ubuntu.com/ubuntu $SUITE-security main universe
EOL
echo nx > "$CH/etc/hostname"
printf 'NX OS 0.0.1 (pre-alpha) \\n \\l\n' > "$CH/etc/issue"
printf 'export USERNAME="nx"\nexport USERFULLNAME="NX Live user"\nexport HOST="nx"\nexport BUILD_SYSTEM="NX"\nexport FLAVOUR="NX"\n' > "$CH/etc/casper.conf"
cp "$HERE/config/os-release" "$CH/etc/os-release"
cp "$HERE/config/motd" "$CH/etc/motd"
chroot "$CH" /usr/bin/env NX_FLAVOR="$FLAVOR" /bin/bash -euxc '
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends linux-image-virtual casper initramfs-tools systemd-sysv \
  network-manager sudo less nano iproute2 ca-certificates locales \
  parted dosfstools mtools e2fsprogs squashfs-tools grub-pc-bin grub-efi-amd64-bin grub-efi-amd64-signed shim-signed efibootmgr gdisk
useradd -m -s /bin/bash -G sudo nx || true
echo "nx:nx" | chpasswd
mkdir -p /etc/systemd/system/getty@tty1.service.d
printf "[Service]\nExecStart=\nExecStart=-/sbin/agetty --autologin nx --noclear %%I \$TERM\n" > /etc/systemd/system/getty@tty1.service.d/autologin.conf
if [ "${NX_FLAVOR:-base}" = desktop ]; then
  apt-get install -y --no-install-recommends xorg xfce4 xfce4-terminal lightdm lightdm-gtk-greeter network-manager-gnome \
    dbus-x11 adwaita-icon-theme fonts-noto-core fonts-noto-ui-core xdg-utils
  mkdir -p /etc/lightdm/lightdm.conf.d
  printf "[Seat:*]\nautologin-user=nx\nautologin-session=xfce\n" > /etc/lightdm/lightdm.conf.d/50-nx-live.conf
fi
apt-get clean; rm -rf /var/lib/apt/lists/*
'
umount -l "$CH/dev" "$CH/proc" "$CH/sys" || true; trap - EXIT
rm -rf "$ISO"; mkdir -p "$ISO/casper" "$ISO/boot/grub"
KFILE=$(find "$CH/boot" -maxdepth 1 -name 'vmlinuz-*' | sort | head -n1)
KV="${KFILE##*/vmlinuz-}"
cp "$CH/boot/vmlinuz-$KV" "$ISO/casper/vmlinuz"; cp "$CH/boot/initrd.img-$KV" "$ISO/casper/initrd"
mksquashfs "$CH" "$ISO/casper/filesystem.squashfs" -comp xz -e boot -noappend -no-progress
( cd "$ISO" && find . -type f ! -name md5sum.txt ! -path "./boot/grub/*" -print0 | xargs -0 md5sum > md5sum.txt )
cp "$HERE/config/grub.cfg" "$ISO/boot/grub/grub.cfg"
if [ "$FLAVOR" = base ]; then IMG="$OUT/nx-os-$VERSION-amd64.iso"; else IMG="$OUT/nx-os-$VERSION-$FLAVOR-amd64.iso"; fi
grub-mkrescue -o "$IMG" "$ISO" -- -volid NX_OS
( cd "$OUT" && sha256sum "$(basename "$IMG")" > "$(basename "$IMG").sha256" )
echo "BUILT: $IMG"; ls -lh "$IMG"
