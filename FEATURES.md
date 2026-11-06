# FEATURES

See FEATURE_PRESERVATION.md for all 50 features. Counts: IMPLEMENTED AND TESTED=7, PARTIALLY=7, PLANNED=36.

## Feature 50: NX Studio Code
Replaced: the former in-tree Python/Qt `nxcs` (code-studio/nxcs) was removed. `code-studio/` is now the git submodule of
https://github.com/Barman-Zarei/NX-Studio-Code (LEGACY branch here, `main` branch on NX `main`). Module status is whatever that project documents
(see code-studio/README.md "Project status" and docs/LEGACY.md); NX re-tested only its Python core (36 tests) and extension smoke test. The editor itself was NOT built here.

LEGACY editor engine: Electron 22 (Windows 7 SP1+, experimental). Control Center action `Open NX Studio Code` starts a built copy ($NX_STUDIO_CODE_BIN) or reports honestly that none exists.

## LEGACY-only: NX APP TRANSLATOR
windows/nx-app-translator/ - analyze + adapt a Windows program for Windows 7 SP1 and rebuild an installer. PARTIALLY IMPLEMENTED: loader-level fixes only (PE version fields, 24 shimmed APIs, Electron runtime swap); not a general decompiler; never run on real Windows 7. See its README.
