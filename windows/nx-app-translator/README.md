# NX APP TRANSLATOR (branch LEGACY)

Takes a Windows program (installer, zip or app folder) and produces a **new installer** that targets **Windows 7 SP1**, using NX's own
tools (PyInstaller-frozen stub, `check_win7_compat.py`, PE tooling). Python 3.8 + `pefile`; the installer stub runs on Windows 7.

    nxat analyze  SETUP.exe                      # what blocks Windows 7, what can be fixed automatically
    nxat translate SETUP.exe -o SETUP-win7.exe --confirm [--name N] [--entry app/main.exe] [--stub nx-app-installer.exe] [--strict] [--no-source-ai]

## How it runs inside NX (Brok + NX Studio Code)
`translate` works on any program, but **Brok supervises it** (`nxat/supervisor.py`, uses `ai/service/brok_adapter.py`, so it runs on NX/Linux as a normal user):
1. **Gate 1 (before anything is changed):** hard deterministic blocks (keygen/crack/activator names, kernel drivers, anti-tamper protectors such as Themida/VMProtect, process-injection / keylogging / encrypt-and-enumerate API patterns) that nobody can override, then Brok reviews a fact sheet about the app as UNTRUSTED DATA and must answer an explicit `{"allow": true}`.
   **Fail closed:** Brok missing, timed out, or unclear -> translation refused. There is no flag to skip supervision.
2. **Adapt (binary level):** the fixes in the table below.
3. **Decompile:** Electron `app.asar` (built in), .NET via `ilspycmd`, native via `retdec-decompiler` when installed. Otherwise: no source, stays at step 2.
4. **Brok + NX Studio Code loop (up to 3 rounds):** Brok only *proposes* whole-file edits as JSON; **Gate 2** reviews the diff (rules + Brok) before anything is written; NX Studio Code's core applies it (conflict-safe patch apply) and checks with allowlisted commands under Safe Run (`node --check` for JS, mingw `-fsyntax-only` for C). Verified Electron source is repacked into `app.asar`; verified native C is rebuilt with mingw-w64 (Windows 7 target) and re-checked/patched; for .NET the edited source stays in the workspace (no automatic rebuild: needs NuGet/SDK access).
5. **Pack** the installer. Remaining problems are printed as a loud WARNING (`--strict` aborts instead).
Every decision is appended to an audit log (`$NXAT_AUDIT_LOG`, default `~/.local/share/nx-ai/nxat-audit.jsonl`). The installer stub is **native C** (`stub/nxstub.c` + miniz, no Python or runtime needed on the target; x86 build runs on 32- and 64-bit Windows 7+). Build it with `sh stub/build.sh`; `translate` finds `stub/bin/x86/nx-app-installer.exe` automatically (or `NXAT_STUB`, `/usr/share/nx/`). Digital signatures are dropped (accepted).
Supervision lowers abuse; it cannot guarantee it - heuristics and an LLM can both be wrong.

Pipeline: **unpack** (folder, zip, `.asar`, MSI/NSIS/SFX via 7-Zip, Inno via innoextract) -> **analyze** -> **adapt** -> **re-analyze (static Win7 check)**
-> **pack** (stub exe + payload + manifest + SHA-256 trailer). The user runs the produced installer: per-user install to
`%LOCALAPPDATA%\Programs\<Name>`, Start-menu shortcut, HKCU uninstall entry (`uninstall.exe`).

## What adapt really does (and nothing more)
| Problem found | Automatic action |
|---|---|
| PE header says OS/subsystem > 6.1 | lowered to 6.1 (only valid if the code does not truly need newer features) |
| Static import of an API that is missing on Win7 (24 APIs, `nxshim7.dll`) | import table rewritten so those functions come from `nxshim7.dll` (placed next to the exe). On newer Windows the shim forwards to the real API; on Win7 it uses a fallback |
| Electron > 22 | runtime replaced by Electron 22.3.27 (last Win7 version), `resources/` kept. Your JS must not need newer Electron APIs; native `.node` modules are reported, **not** rebuilt |
| Frozen Python 3.9+, .NET 7+, APIs with no shim | **reported as blockers**; the Brok loop may try when source can be recovered, otherwise a WARNING is printed and the installer is still built (`--strict` aborts) |

Fallback quality (honest list): precise time -> normal system time; WaitOnAddress -> polling; thread description -> no-op; per-monitor DPI -> system DPI;
CompareObjectHandles -> handle equality; VirtualAlloc2/MapViewOfFile3 -> only the plain (no extended parameters) case, otherwise they fail with
`ERROR_CALL_NOT_IMPLEMENTED`.

## Limits - read this
Status of each weakness (what was done about it and what is left):
1. **Never run on real Windows 7.** Done about it: every shim export is exercised by a probe with the Windows 7 *fallback* code forced on (22+ checks, x86 + x64, under Wine), and `win7-selftest/` is a one-click kit (probe, shim, original-vs-translated program, native installer) to run on a real Windows 7 laptop: copy the kit folder, double-click `RUN-ME.bat`, send back `RESULT.txt`. **Still open until someone runs it.**
2. **Real Brok with a real model not run.** Done: `nxat brok-selftest` feeds 6 synthetic fact sheets (3 benign, 3 suspicious) to the real Brok and prints expected vs. actual; verdicts need a per-call random id (a planted `{"allow": true}` in the app's data is ignored); content indicators (ransom phrases, stealer strings, Tor addresses) and API patterns hard-block before Brok is even asked; fail closed. **Still open: nobody has measured the real model.**
3. **.NET (Core 7+):** EXPERIMENTAL downgrade (runtimeconfig -> 6.0 and System.*/Microsoft.* assembly references re-pointed to 6.0.0.0, needs `dnfile`); only works if the app uses no API newer than .NET 6 - not verified, no .NET runtime here. .NET Framework apps need nothing. No source-level rebuild (ilspycmd/NuGet unavailable).
4. **Native code without source:** binary-level fixes (header, import redirection) are the dependable path. RetDec (real, tested) produces C, but that output does not compile back without errors (12 errors on a 20-line program: duplicate struct definitions); the Brok loop gets the compiler errors and may repair it, rebuild is attempted with mingw-w64 and re-checked. Treat source-level native rebuild as research-grade. **Frozen Python 3.9+ apps: not fixable** (bytecode is version-specific); reported as a blocker.
5. **Supervision is not a guarantee** (heuristics and an LLM can both be wrong); it is fail-closed, audited, and has hard rules nobody can override.

General notes: modified binaries lose their digital signature (accepted); `--confirm` acknowledges the notice, Brok supervision is what gates abuse; do not redistribute translated third-party software; delay-load imports are not rewritten; the native stub needs nothing beyond Windows 7 SP1.
Verification so far (all under Wine, a proxy): 42 unit tests on Python 3.8 and 3.12 (supervision/agent loop use a FAKE Brok; real Brok repo run without a model = fail closed); translated x86/x64 programs, the native installer (install, shortcut, registry, uninstall, corrupt/zip-slip refusal) and a real Electron 30 -> 22.3.27 swap (the swapped runtime started and ran our repacked `app.asar`); the fallback probe in strict mode; the self-test kit's `RUN-ME.bat`.

## Build
`sh shim/build.sh` (mingw-w64) -> `shim/bin/{x64,x86}/nxshim7.dll`; CI builds `nx-app-translator.exe` and `nx-app-installer.exe` (the stub) with PyInstaller 5.13.2.
Brok check: `python -m nxat brok-selftest`. Windows 7 kit: `python win7-selftest/make_kit.py OUTDIR`. Tests: `python -m unittest discover -s tests` (compiler/shim tests skip if mingw is missing; `NXAT_WINE=1` also runs the programs under Wine).
