#!/bin/bash
# UEFI boot test using OVMF. Same pass marker as the BIOS test.
set -uo pipefail
ISO="${1:?usage: boot-test-uefi.sh file.iso [timeout]}"; T="${2:-900}"
CODE=/usr/share/OVMF/OVMF_CODE_4M.fd; VARS_SRC=/usr/share/OVMF/OVMF_VARS_4M.fd
LOG="$(mktemp)"; VARS="$(mktemp)"; cp "$VARS_SRC" "$VARS"; ACCEL=tcg; [ -w /dev/kvm ] && ACCEL=kvm
timeout "$T" qemu-system-x86_64 -accel "$ACCEL" -m 2048 -cdrom "$ISO" -boot d -display none -serial "file:$LOG" -no-reboot \
  -drive if=pflash,format=raw,readonly=on,file="$CODE" -drive if=pflash,format=raw,file="$VARS" &
QP=$!
for _ in $(seq 1 "$T"); do
  if grep -aqE ' login: |nx@nx' "$LOG"; then kill $QP 2>/dev/null; echo "PASS (UEFI,$ACCEL)"; exit 0; fi
  kill -0 $QP 2>/dev/null || break; sleep 1
done
kill $QP 2>/dev/null; echo "FAIL (UEFI,$ACCEL)"; tail -c 800 "$LOG"; exit 1
