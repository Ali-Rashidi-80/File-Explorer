# Changelog

All notable changes to **File Explorer** (Smart Project Explorer) are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project aims to adhere to [Semantic Versioning](https://semver.org/).

**Languages:** **English** · [فارسی](CHANGELOG.fa.md)

---

## [5.1.0] — 2026-07 — Bulletproof Polish

### Added

- Path safety helpers: `safe_join_under`, reserved Windows name rejection, traversal guards for TXT and JSON reverse rebuilds.
- Memory / size caps: skip text files over **10 MB**; stop full-scan output at **50 MB** cumulative.
- Separate `FileScanner` / `ReverseScanner` thread lifecycle, busy UI, and safer `closeEvent` wait.
- Tree parse fix using connector column index; skip meta `[…]` lines.
- UI format lock: JSON only in **structure** mode.
- Shared `IGNORED_DIRS` for walk + tree generation; symlink skip.
- Test suites: core, live E2E, production-live, QA tooling; `qa.bat` multi-linter gate.
- `pyproject.toml` tooling (black, ruff, mypy, pytest).
- Portable onefile packaging via `FileExplorer.portable.spec` + `build.bat` / `build_portable.bat`.

### Changed

- Active product surface is **PySide6** `file-explorer-pyside6.py` (Enterprise / v5.1 UI copy).
- Reverse mode messaging clarified: **empty scaffold only** (no content restore).

### Security

- Zip-slip–style path escape attempts rejected under the chosen output root.
- Worker interruption and single-job busy guard to reduce race/UI deadlocks.

---

## [5.0.0] — prior

- PySide6 desktop UI with Scan + Reverse tabs, dark theme, Drag & Drop.
- Full-content TXT extraction and structure TXT/JSON export foundations.

---

## [3.x] — legacy

- Older PyQt6 script retained as [`file_explorer.py`](file_explorer.py) for historical reference; **not** the packaging entry point.

---

[5.1.0]: https://github.com/Ali-Rashidi-80/File-Explorer
