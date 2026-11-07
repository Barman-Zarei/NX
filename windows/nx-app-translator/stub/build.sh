#!/bin/sh
# Native installer stub -> stub/bin/{x86,x64}/nx-app-installer.exe (mingw-w64). The x86 build runs on 32- and 64-bit Windows 7+.
set -eu
cd "$(dirname "$0")"
mkdir -p bin/x86 bin/x64
SRC="nxstub.c vendor/miniz.c vendor/miniz_tdef.c vendor/miniz_tinfl.c vendor/miniz_zip.c"
CF="-O2 -Wall -municode -mwindows -static -s -DMINIZ_NO_ARCHIVE_WRITING_APIS -DMINIZ_NO_STDIO -Wl,--major-subsystem-version=6 -Wl,--minor-subsystem-version=1 -Wl,--major-os-version=6 -Wl,--minor-os-version=1"
"$(command -v i686-w64-mingw32-gcc)" $CF -o bin/x86/nx-app-installer.exe $SRC -lole32 -luuid -lshell32 -ladvapi32
"$(command -v x86_64-w64-mingw32-gcc)" $CF -o bin/x64/nx-app-installer.exe $SRC -lole32 -luuid -lshell32 -ladvapi32
echo "built: bin/x86/nx-app-installer.exe bin/x64/nx-app-installer.exe"
