#!/bin/bash
# Prepares a virtual display (Xvfb), D-Bus session, PulseAudio null sink and a notification daemon (dunst),
# then runs nx-core/tests/test_real_tools.py. Needs: xvfb scrot ffmpeg pulseaudio-utils cron dunst libnotify-bin gsettings.
set -u
cd "$(dirname "$0")/.." || exit 1
PY="${PYTHON:-python3}"
export NX_REAL_TOOLS=1 DISPLAY=:99 GSETTINGS_BACKEND=memory
Xvfb :99 -screen 0 1024x768x24 >/dev/null 2>&1 & XP=$!
sleep 2
dbus-run-session -- bash -c '
  pulseaudio --start --exit-idle-time=-1 --daemonize=yes >/dev/null 2>&1; sleep 2
  pactl load-module module-null-sink sink_name=nxtest >/dev/null
  dunst >/dev/null 2>&1 & DP=$!; sleep 1
  PYTHONPATH=nx-core '"$PY"' -W ignore -m unittest nx-core/tests/test_real_tools.py -v 2>&1 | tail -20
  RC=${PIPESTATUS[0]}
  kill $DP 2>/dev/null; pulseaudio --kill 2>/dev/null; exit $RC'
RC=$?
kill $XP 2>/dev/null
exit $RC
