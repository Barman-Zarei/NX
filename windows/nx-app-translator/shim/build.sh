#!/bin/sh
# Builds nxshim7.dll for x64 and x86 into shim/bin/{x64,x86}/. Needs mingw-w64 (apt: gcc-mingw-w64-x86-64 gcc-mingw-w64-i686).
set -eu
cd "$(dirname "$0")"
mkdir -p bin/x64 bin/x86
CF="-O2 -Wall -Wextra -Wno-cast-function-type -Wno-attributes -shared -static-libgcc -nostartfiles -Wl,--kill-at -Wl,--major-subsystem-version=6 -Wl,--minor-subsystem-version=1 -Wl,--major-os-version=6 -Wl,--minor-os-version=1"
"$(command -v x86_64-w64-mingw32-gcc)" $CF -Wl,--entry=DllMain -o bin/x64/nxshim7.dll nxshim7.c -lkernel32 -luser32 -lgdi32
"$(command -v i686-w64-mingw32-gcc)"   $CF -Wl,--entry=_DllMain@12 -o bin/x86/nxshim7.dll nxshim7.c -lkernel32 -luser32 -lgdi32
echo "built: bin/x64/nxshim7.dll bin/x86/nxshim7.dll"
