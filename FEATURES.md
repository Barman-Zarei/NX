# FEATURES

See FEATURE_PRESERVATION.md for all 50 features. Counts: IMPLEMENTED AND TESTED=7, PARTIALLY=7, PLANNED=36.

## Feature 50: NX Studio Code
Replaced: the former in-tree Python/Qt `nxcs` was removed. `code-studio/` is the git submodule of https://github.com/Barman-Zarei/NX-Studio-Code (branch main). Module status is whatever that project documents (code-studio/README.md); NX re-tested only its Python core (36 tests) and extension smoke test. The editor was NOT built here. Control Center action `Open NX Studio Code` starts a built copy ($NX_STUDIO_CODE_BIN) or reports honestly that none exists.
