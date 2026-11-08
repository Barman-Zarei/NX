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
3. **Decompile:** Electron `app.asar` (built in), .NET via the ILSpy engine tool, frozen Python via pyinstxtractor-ng + pycdc, native via RetDec when installed. Otherwise: no source, stays at step 2.
4. **Brok + NX Studio Code loop (up to 3 rounds):** Brok only *proposes* whole-file edits as JSON; **Gate 2** reviews the diff (rules + Brok) before anything is written; NX Studio Code's core applies it (conflict-safe patch apply) and checks with allowlisted commands under Safe Run (`node --check` for JS, mingw `-fsyntax-only` for C). Verified Electron source is repacked into `app.asar`; verified C# is built with `mcs`; verified Python is re-frozen with Python 3.8; native C is rebuilt with mingw-w64 - each only if the differential run matches.
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
What each former weakness looks like now. "Needs infrastructure" means it cannot be finished by code alone.
| # | Weakness | Status |
|---|---|---|
| 1 | Never run on a real Windows 7 | **Needs infrastructure** (a Windows 7 machine; no KVM/Windows image is available where this was built). Done as far as code can: every shim export probed with the Windows 7 fallbacks forced on (24 checks, x86+x64, under Wine) and a one-click kit `win7-selftest/` (copy to a Windows 7 laptop, run `RUN-ME.bat`, send `RESULT.txt`) |
| 2 | Real Brok with a real model not run | **Needs infrastructure** (an API key / model; none was available). Done: `nxat brok-selftest` measures the real Brok on 6 fact sheets; verdicts are bound to a random per-call id; content/API hard-blocks run before Brok; fail closed |
| 3 | .NET 7+ apps | **Done (with limits).** Types missing in .NET 6 -> ILSpy v8.2 engine (built offline, `tools/nxdecompile/setup.sh`) -> C# 7.3 -> Brok adapts -> `mcs` -> a **.NET Framework 4 exe** (needs .NET Framework 4.x on Windows 7) -> differential run (`dotnet X.dll` vs `mono X.exe`) before anything is replaced. Verified on a real net8 app using `FrozenDictionary`/`TimeProvider`. Limits: mcs speaks ~C# 7; third-party dependency DLLs are not re-targeted; GUI apps that never exit cannot be compared (not replaced). Apps that need nothing newer than .NET 6 get an EXPERIMENTAL runtimeconfig/reference downgrade instead |
| 4 | Native code without source | **Impossible to do reliably (needs a decompiler that preserves semantics).** Binary-level fixes are the dependable route. Source-level: RetDec (real) + deterministic repair makes the C compile and link, but on an optimized program RetDec lost register-passed arguments and the rebuilt program printed a different result: the differential run **rejected** it (tested). So native rebuild never silently replaces a binary, and for such programs only the binary-level fixes apply |
| 5 | Frozen Python 3.9+ | **Done (with infrastructure).** Real Python 3.11 PyInstaller exe using `match`/`removeprefix` -> extract (pyinstxtractor-ng) -> pycdc (incomplete on new opcodes, the bytecode listing goes to Brok) -> Brok -> compile check on 3.8 -> re-freeze with PyInstaller 5.13.2 on a Windows CPython 3.8 under Wine -> differential run -> installed and run. Needs: Wine, `tools/setup_python_refreeze.sh`. Third-party packages are not reinstalled (a rebuild without them fails the differential run) |
| 6 | Supervision is not a guarantee | **Inherent.** Hard rules, fail closed, audit log; heuristics and an LLM can both be wrong |

Rules that hold for every source-level path: Brok only proposes edits; gate 2 reviews every patch; a rebuilt program replaces the original **only if a run without input gives the same exit code and output**, and a run that cannot be compared (no runner, does not finish) counts as "not verified", never as "identical".
General notes: modified binaries lose their digital signature (accepted); `--confirm` acknowledges the notice, Brok supervision is what gates abuse; do not redistribute translated third-party software; delay-load imports are not rewritten; the native stub needs nothing beyond Windows 7 SP1.
Verification so far (Wine is a proxy for Windows): 45 unit/integration tests on Python 3.8 and 3.12 (supervision and the Brok loop use a FAKE Brok; the real Brok repo without a model fails closed); translated x86/x64 programs; native installer (install, shortcut, registry, uninstall, corrupt/zip-slip refusal); real Electron 30 -> 22.3.27 (runs our repacked app.asar); real net8 app -> .NET Framework exe; real Python 3.11 exe -> Python 3.8 exe installed and run; fallback probe in strict mode; the self-test kit's `RUN-ME.bat`.

## Build
`sh shim/build.sh` (mingw-w64) -> `shim/bin/{x64,x86}/nxshim7.dll`; CI builds `nx-app-translator.exe` and `nx-app-installer.exe` (the stub) with PyInstaller 5.13.2.
Brok check: `python -m nxat brok-selftest`. Windows 7 kit: `python win7-selftest/make_kit.py OUTDIR`. Tests: `python -m unittest discover -s tests` (compiler/shim tests skip if mingw is missing; `NXAT_WINE=1` also runs the programs under Wine).
