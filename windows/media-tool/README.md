# NX Media Tool - LEGACY edition (Windows 7 SP1+)
Python 3.8 + PySide2 5.15.2.1. CLI: `nx-media-tool-cli.exe NX.iso NX.iso.sha256` (exit 0 = match, 1 = mismatch). GUI: `nx-media-tool.exe`. USB writing is NOT implemented.
Executables are built by CI (artifacts `win-x64`, `win-x86`). On Windows 7 run `windows/win7-smoke-test.bat` and send the report. Details: docs/compatibility/windows.md
