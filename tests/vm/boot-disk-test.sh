#!/bin/bash
# Boots an INSTALLED disk image (no ISO attached). usage: boot-disk-test.sh disk.img bios|uefi [timeout]
set -uo pipefail
IMG="${1:?disk image}"; MODE="${2:-bios}"; T="${3:-900}"; LOG="$(mktemp)"; ACCEL=tcg; [ -w /dev/kvm ] && ACCEL=kvm
EXTRA=()
if [ "$MODE" = uefi ]; then VARS="$(mktemp)"; cp /usr/share/OVMF/OVMF_VARS_4M.fd "$VARS"
  # shellcheck disable=SC2054
  EXTRA=(-drive if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd -drive if=pflash,format=raw,file="$VARS"); fi
timeout "$T" qemu-system-x86_64 -accel "$ACCEL" -m 1536 -drive file="$IMG",format=raw,if=virtio -display none -serial "file:$LOG" -no-reboot "${EXTRA[@]}" &
QP=$!
for _ in $(seq 1 "$T"); do
  if grep -aq ' login: ' "$LOG"; then kill $QP 2>/dev/null; echo "PASS ($MODE,$ACCEL)"; grep -a ' login: ' "$LOG" | tail -1; exit 0; fi
  kill -0 $QP 2>/dev/null || break; sleep 1
done
kill $QP 2>/dev/null; echo "FAIL ($MODE,$ACCEL)"; tail -c 1200 "$LOG"; exit 1
