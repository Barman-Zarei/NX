# Windows 7 SP1+ support (branch LEGACY)
**Scope:** the Windows host tool (ISO verification; USB writing NOT implemented) and installing NX next to a Windows 7 era (MBR/BIOS) disk.
Stack: Python 3.8 + PySide2 5.15.2.1 (Qt 5.15), PyInstaller 5.13.2, x64 and x86 builds. Windows 7 needs SP1, the Universal C Runtime update (KB2999226) and the VC++ 2015-2019 redistributable.
## What CI checks (`.github/workflows/ci.yml`, never run yet)
1. Unit tests on Python 3.8 on Linux and on **real Windows** (windows-2022 runner, x64 and x86).
2. PyInstaller builds of the CLI and GUI executables, smoke-tested on the Windows runner (match, mismatch, headless GUI self test).
3. `windows/check_win7_compat.py`: static check that no built binary requires OS/subsystem > 6.1 or imports known post-Windows-7 APIs. **Proxy only.**
4. Wine configured as Windows 7 runs the executables. **Proxy only** (Wine implements newer APIs too).
5. BIOS/MBR alongside install on a simulated Windows 7 disk (partitions byte-identical, boots in QEMU).
## What CI cannot do
GitHub offers no Windows 7 runner. Real Windows 7 verification = a human runs `windows/win7-smoke-test.bat` (with the built folders from the CI artifact) on Windows 7 SP1 and sends `win7-report.txt`. Until that has been done, "supports Windows 7" means: designed and statically checked for it, **not verified on it**.
## Known limits
Python 3.8, Qt 5.15 and Windows 7 itself no longer get security fixes: this is a legacy edition. Newer VC++ runtimes picked up by the build may not run on Windows 7: the PE check and the Wine/real-machine tests exist to catch this.
`main` (PySide6/Qt 6) supports Windows 10+ only. Branch policy: `LEGACY` merges `main` for everything outside `windows/`, its CI and its docs.
