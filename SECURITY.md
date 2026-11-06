# Security
Report vulnerabilities privately to the maintainer. No release is currently supported.
## NX Studio Code (submodule code-studio/)
Security properties of the editor (secret scanning, approval-first AI agent, API key in the OS keychain, telemetry off) are defined by the NX-Studio-Code project: see code-studio/SECURITY.md. LEGACY uses Electron 22 / Chromium 108, which no longer receives security fixes: keep Workspace Trust on and avoid untrusted web content.

## NX APP TRANSLATOR (LEGACY)
Brok supervises every translation (fail closed, hard rules, audit log; see windows/nx-app-translator/README.md); it reduces abuse but is not a guarantee. Modifies third-party binaries: modified files lose their digital signature, so Windows/SmartScreen will treat the produced installer as unsigned. Archive extraction rejects path traversal (zip-slip, asar). The installer stub verifies a SHA-256 of its payload (integrity against corruption, not authenticity - there is no signature). Use only on software you may modify; do not redistribute translated third-party software. `nxshim7.dll` is loaded from the application directory: keep that directory non-writable for untrusted users.
