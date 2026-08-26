# Security Policy

**Languages:** **English** · [فارسی](SECURITY.fa.md)

## Supported versions

| Version | Supported |
|---------|-----------|
| 5.1.x   | ✅ |
| &lt; 5.1  | ❌ (please upgrade) |

## What counts as a vulnerability

Please report privately if you find issues such as:

- Path traversal / write-outside-root during reverse rebuild
- Symlink follow that escapes the selected project root during scan
- Unexpected code execution from crafted maps or filenames
- Denial-of-service that bypasses documented size caps in a severe way

## What is **not** a vulnerability (by design)

- Reverse rebuild creating **empty** files (no content restore)
- Skipping ignored dirs (`.git`, `node_modules`, …)
- Stopping full scan at the **50 MB** output cap or **10 MB**/file skip
- JSON disabled in **full** scan mode

## How to report

1. Prefer a **private** channel: email the maintainer at the address on their [GitHub profile](https://github.com/Ali-Rashidi-80), **or** open a GitHub Security Advisory if enabled for this repository.
2. Include: OS, app version (`5.1.0`), steps to reproduce, expected vs actual, and a minimal PoC map/folder if safe.
3. Do **not** open a public issue with exploit details until a fix is available.

## Response expectations

- Acknowledgement aim: within **7 days**
- Fix / mitigation aim: as soon as practical for confirmed high-severity issues
- Credit: we are happy to acknowledge reporters who wish to be named (optional)

## Hardening already in v5.1

- `safe_join_under` + `is_relative_to` for reverse writes
- Rejection of `..`, absolute segments, invalid characters, Windows reserved device names
- Symlink skip during directory iteration
- Output size caps to reduce memory blow-ups

Thank you for helping keep users safe.
