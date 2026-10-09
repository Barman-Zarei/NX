# Windows host tool compatibility (branch main)
Mainline Windows tool: PySide6 (Qt 6): **Windows 10 or later**. Windows 7/8 are NOT supported on `main`: use the `LEGACY` branch (Python 3.8 + PySide2, Windows 7 SP1+).
Tested: GUI window logic on Linux (offscreen, Python 3.12 + PySide6). Never run on Windows. No .exe, no USB writing.
Branch policy: `LEGACY` merges `main` for everything except `windows/`, its CI and its docs.
