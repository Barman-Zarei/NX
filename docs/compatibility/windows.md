# Windows host tool compatibility (branch LEGACY)
This branch targets **Windows 7 SP1 and later**: Python 3.8 + PySide2 5.15.2.1 (Qt 5.15). Windows 7 needs SP1, the Universal C Runtime update (KB2999226) and the VC++ 2015-2019 redistributable.
- Tested: unit tests and the GUI window logic on **Linux** with Python 3.8.20 + PySide2 5.15.2.1 (offscreen). NOT tested on any Windows version; no .exe has been built; USB writing is not implemented.
- Python 3.8 and Qt 5.15 no longer receive public security fixes: this branch is a documented legacy edition without full security support.
- Installing NX alongside Windows 7 is NOT supported by `nx-install-alongside` (it needs GPT + UEFI; Windows 7 is usually MBR + BIOS).
- The mainline branch (`main`) uses PySide6/Qt 6 and supports Windows 10+ only.
Branch policy: keep OS code (build/, installer/, ai/, tests/vm) identical to `main` by merging `main` into `LEGACY`; only `windows/` and its CI/docs differ.
