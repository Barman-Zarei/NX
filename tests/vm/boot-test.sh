#!/bin/bash
# Boots an NX ISO in QEMU (BIOS) and waits for a login/shell marker on the serial console.
set -uo pipefail
ISO="${1:?usage: boot-test.sh file.iso [timeout_seconds]}"; T="${2:-600}"
LOG="$(mktemp)"; ACCEL=tcg; [ -w /dev/kvm ] && ACCEL=kvm
timeout "$T" qemu-system-x86_64 -accel "$ACCEL" -m 1536 -cdrom "$ISO" -boot d -display none -serial "file:$LOG" -no-reboot &
QP=$!
for _ in $(seq 1 "$T"); do
  if grep -qE ' login: |nx@nx' "$LOG"; then kill $QP 2>/dev/null; echo "PASS ($ACCEL): reached login/shell"; exit 0; fi
  kill -0 $QP 2>/dev/null || break; sleep 1
done
kill $QP 2>/dev/null; echo "FAIL ($ACCEL): marker not seen; last serial output:"; tail -15 "$LOG"; exit 1
