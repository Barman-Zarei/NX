# Security
Report vulnerabilities privately to the maintainer. No release is currently supported.
## Code Studio (added)
- Claude API key: never hard-coded; read from ANTHROPIC_API_KEY or a 0600 key file (group/world-readable file is refused); redacted from errors. AI can be disabled; local editing works without it. Mock replies are labelled source="mock".
- Safe Run is NOT a sandbox: it scrubs env, applies timeout/rlimits and kills process groups; filesystem and (unless unshare works) network are not isolated.
- AI changes require approval of the diff; edits made by the user while the AI works are never overwritten.
- Archive extraction rejects path traversal, links, devices and oversize archives.
- Destructive Git operations (discard, delete branch, force-push) need explicit confirm=True.
