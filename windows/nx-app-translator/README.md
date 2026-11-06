# NX APP TRANSLATOR (branch LEGACY)

Takes a Windows program (installer, zip or app folder) and produces a **new installer** that targets **Windows 7 SP1**, using NX's own
tools (PyInstaller-frozen stub, `check_win7_compat.py`, PE tooling). Python 3.8 + `pefile`; the installer stub runs on Windows 7.

    nxat analyze  SETUP.exe                      # what blocks Windows 7, what can be fixed automatically
    nxat translate SETUP.exe -o SETUP-win7.exe --confirm [--name N] [--entry app/main.exe] [--stub nx-app-installer.exe]

Pipeline: **unpack** (folder, zip, `.asar`, MSI/NSIS/SFX via 7-Zip, Inno via innoextract) -> **analyze** -> **adapt** -> **re-analyze (static Win7 check)**
-> **pack** (stub exe + payload + manifest + SHA-256 trailer). The user runs the produced installer: per-user install to
`%LOCALAPPDATA%\Programs\<Name>`, Start-menu shortcut, HKCU uninstall entry (`uninstall.exe`).

## What adapt really does (and nothing more)
| Problem found | Automatic action |
|---|---|
| PE header says OS/subsystem > 6.1 | lowered to 6.1 (only valid if the code does not truly need newer features) |
| Static import of an API that is missing on Win7 (24 APIs, `nxshim7.dll`) | import table rewritten so those functions come from `nxshim7.dll` (placed next to the exe). On newer Windows the shim forwards to the real API; on Win7 it uses a fallback |
| Electron > 22 | runtime replaced by Electron 22.3.27 (last Win7 version), `resources/` kept. Your JS must not need newer Electron APIs; native `.node` modules are reported, **not** rebuilt |
| Frozen Python 3.9+, .NET 7+, APIs with no shim | **reported as blockers** - needs the original source and a rebuild; `translate` stops unless `--force` |

Fallback quality (honest list): precise time -> normal system time; WaitOnAddress -> polling; thread description -> no-op; per-monitor DPI -> system DPI;
CompareObjectHandles -> handle equality; VirtualAlloc2/MapViewOfFile3 -> only the plain (no extended parameters) case, otherwise they fail with
`ERROR_CALL_NOT_IMPLEMENTED`.

## Limits - read this
* This is **not** a general decompiler/recompiler. It does not turn machine code into source and cannot make arbitrary software run on Windows 7;
  it fixes the *loader-level* incompatibilities above. Apps that call newer APIs dynamically (GetProcAddress) or need new OS features will still fail at run time.
* Modified binaries **lose their digital signature**; anti-cheat/DRM/self-checking programs may refuse to run.
* Use only on software you are entitled to modify; the `--confirm` flag is a reminder of that. Do not redistribute translated third-party software.
* **Verification status:** unit tests pass on Python 3.8 and 3.12; translated sample x86 and x64 programs were **executed under Wine** (proxy: Wine also implements the newer APIs). **Never run on real Windows 7.**
* Delay-load imports are not rewritten. Installer stub needs Python-3.8-frozen prerequisites on Win7: SP1 + KB2999226 (UCRT).

## Build
`sh shim/build.sh` (mingw-w64) -> `shim/bin/{x64,x86}/nxshim7.dll`; CI builds `nx-app-translator.exe` and `nx-app-installer.exe` (the stub) with PyInstaller 5.13.2.
Tests: `python -m unittest discover -s tests` (compiler/shim tests skip if mingw is missing; `NXAT_WINE=1` also runs the programs under Wine).
