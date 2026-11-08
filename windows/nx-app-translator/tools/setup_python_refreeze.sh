#!/bin/sh
# One-time setup of the INFRASTRUCTURE the frozen-Python path needs (Linux/NX). Everything comes from PyPI / GitHub.
#   - pyinstxtractor-ng (pip), pycdc (built from source), Wine, and a WINDOWS CPython 3.8 with PyInstaller 5.13.2 (the last line that supports Windows 7)
# Result: ~/.local/share/nx/winpy38/python.exe (picked up automatically) and pycdc in ~/.local/bin.
set -eu
pip install --user pyinstxtractor-ng
sudo apt-get install -y wine xvfb cmake g++ git
B=/tmp/nxat_pycdc; rm -rf "$B"; git clone --depth 1 https://github.com/zrax/pycdc.git "$B"; (cd "$B" && cmake -DCMAKE_BUILD_TYPE=Release . >/dev/null && make -j1) && mkdir -p ~/.local/bin && cp "$B/pycdc" ~/.local/bin/
D=~/.local/share/nx/winpy38; mkdir -p "$D"
curl -L -o /tmp/py38.tgz https://github.com/astral-sh/python-build-standalone/releases/download/20240814/cpython-3.8.19+20240814-x86_64-pc-windows-msvc-shared-install_only.tar.gz
tar -xzf /tmp/py38.tgz -C "$D" --strip-components=1
# pip under Wine needs a live stdin pipe and piped (not file) output:
sleep 1200 | timeout 1100 xvfb-run -a wine "$D/python.exe" -m pip install "pyinstaller==5.13.2" 2>&1 | cat
echo "done: $D/python.exe"
