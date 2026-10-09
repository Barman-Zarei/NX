#!/bin/bash
# UNTESTED. Boots a desktop-flavor ISO with a virtual display and saves screenshots (PNG) at intervals so a human can inspect them.
# usage: desktop-screenshot.sh file.iso outdir [seconds-between=60] [count=5]. A screenshot is evidence only after someone looks at it.
set -uo pipefail
ISO="${1:?iso}"; OUT="${2:?outdir}"; STEP="${3:-60}"; N="${4:-5}"; mkdir -p "$OUT"
ACCEL=tcg; [ -w /dev/kvm ] && ACCEL=kvm; SOCK="$(mktemp -u /tmp/nxmon.XXXXXX)"
qemu-system-x86_64 -accel "$ACCEL" -m 2048 -cdrom "$ISO" -boot d -vga std -display none -monitor "unix:$SOCK,server,nowait" -no-reboot &
Q=$!; sleep 5
for ((i = 1; i <= N; i++)); do
  sleep "$STEP"; echo "screendump $OUT/shot-$i.ppm" | socat - "UNIX-CONNECT:$SOCK" > /dev/null 2>&1
  command -v convert > /dev/null && convert "$OUT/shot-$i.ppm" "$OUT/shot-$i.png" 2> /dev/null && rm -f "$OUT/shot-$i.ppm"
done
kill "$Q" 2> /dev/null; ls -l "$OUT"
