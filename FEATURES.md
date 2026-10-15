# FEATURES

See FEATURE_PRESERVATION.md for all 50 features. Counts: IMPLEMENTED AND TESTED=7, PARTIALLY=7, PLANNED=36.

## Feature 50: NX Code Studio modules

| Module | Status | Works | Not done |
|---|---|---|---|
| 7.1 IDE Core | PARTIALLY IMPLEMENTED | tabs, explorer, save, command palette, terminal, search/replace(core), recent projects | no split view, themes, folding, syntax highlighting, LSP, plugin API |
| 7.2 Claude API | IMPLEMENTED AND TESTED for error handling/key safety/disable/mock-labelling; live request NOT TESTED (no key) | claude.py, gui Claude panel | streaming/cost UI absent |
| 7.3 NX Debugger | PARTIALLY IMPLEMENTED | Python-only bdb debugger: breakpoints, step/next, continue, stack, vars, eval | no DAP, no GUI panel, no other languages |
| 7.4 Pipeline Lab | PARTIALLY IMPLEMENTED | inspect workflows, run `run:` steps, honest unsupported list | no matrix/uses/services/secrets/expressions |
| 7.5 Project Intelligence | PARTIALLY IMPLEMENTED | language counts, entry points, Python AST symbols/imports, deps, traceback files | no JS/C symbol parsing, no LSP |
| 7.6 Code Review AI | PARTIALLY IMPLEMENTED | confirmed static Python checks with lines; AI review labelled speculative (mock-tested) | live AI review NOT TESTED |
| 7.7 Test Intelligence | PARTIALLY IMPLEMENTED | discover + run unittest, failures, locations | no pytest/coverage/test generation |
| 7.8 Git Command Center | PARTIALLY IMPLEMENTED | status/diff/stage/commit/branch/merge/conflicts/log, confirm for destructive | no pull, PR prep, GUI beyond status |
| 7.9 Dependency Guardian | PARTIALLY IMPLEMENTED | pip outdated parse + upgrade risk preview | outdated() NOT TESTED (needs index); advisories unavailable |
| 7.10 Task Graph | IMPLEMENTED AND TESTED | DAG, concurrency, skip-on-failure, cycle detection | no GUI; cancellation only stops scheduling new tasks |
| 7.11 Release Pilot | PARTIALLY IMPLEMENTED | semver bump, changelog from git, checklist | never publishes; no tag creation |
| 7.12 Language Engine | PLANNED | - | - |
| 7.13 Extension Hub | PLANNED | - | - |
| 7.14 Live Preview | IMPLEMENTED AND TESTED | 127.0.0.1-only static server, port status, logs | no GUI view |
| 7.15 Safe Run | PARTIALLY IMPLEMENTED | env scrub, timeout, rlimits, process-group kill; NOT a sandbox | network-namespace option NOT TESTED; POSIX limits only |
| 7.16 Project Agent | IMPLEMENTED AND TESTED with MOCK Claude only | approval gate, conflict protection, tests run and reported | live Claude NOT TESTED |
| 7.17 Performance Profiler | IMPLEMENTED AND TESTED | cProfile + tracemalloc for Python scripts | no other languages |
| 7.18 Environment Profiles | PARTIALLY IMPLEMENTED | shared-config secret rejection | no runtime env management |
| 7.19 Patch Review | IMPLEMENTED AND TESTED | diff, hunk-select, conflict-safe apply | no GUI diff view |
| 7.20 GitHub Bridge | PLANNED | - | - |
| 7.21 Studio Profiles | PARTIALLY IMPLEMENTED | 5 presets written to settings JSON | GUI does not consume them yet |
| 7.22 Project Forge | IMPLEMENTED AND TESTED | python/cli/web/c templates verified to run | no docs/Git-config templates |
| 7.23 Change Preview | PARTIALLY IMPLEMENTED | upgrade risk preview | no disk estimates |
| 7.24 Offline Library | PLANNED | - | - |
| 7.25 Repository Manager | PLANNED | - | - |
| 7.26 Log Explorer | IMPLEMENTED AND TESTED | level/regex filter + sanitize | no GUI |

On LEGACY, Code Studio runs only on PySide2 5.15 + Python 3.8 (main uses PySide6).
