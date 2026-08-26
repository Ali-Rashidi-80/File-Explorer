# AGENTS.md — guidance for AI coding agents

This file is the **canonical** agent guidance for the File Explorer repository.
Tool-specific instruction files should defer here rather than duplicating policy.

## Product facts (do not invent)

- **Name:** File Explorer / Smart Project Explorer
- **Version:** 5.1.0 (`pyproject.toml` / About dialog)
- **Active entry:** `file-explorer-pyside6.py` (PySide6)
- **Legacy:** `file_explorer.py` (PyQt6) — do not expand unless explicitly asked
- **Reverse rebuild:** creates **empty** dirs/files only — never claim content restore unless implemented with tests
- **JSON export:** structure mode only; full mode is TXT
- **Caps:** 10 MB per text file skip; 50 MB cumulative full-scan output
- **Docs:** English default (`README.md`); Persian siblings use `*.fa.md`

## When changing code

1. Prefer pure helpers at module top; keep GUI thin.
2. Preserve path safety (`safe_join_under`, reserved names, symlink skip).
3. Keep scan/reverse threads separate; respect busy UI / interrupt.
4. Update **both** EN and FA docs when user-facing behavior changes.
5. Run `qa.bat` (or at least `pytest` + ruff/black) before finishing.
6. Do not invent CI badges, screenshots, or features that are not in the tree.

## Forbidden without explicit user request

- Expanding reverse to restore file bodies without caps + tests + doc honesty
- Rewriting packaging to drop portable onefile without discussion
- Committing secrets, large `dist/` binaries, or UPX tool caches (`tools/upx` is gitignored)

## Key paths

| Path | Role |
|------|------|
| `file-explorer-pyside6.py` | Product |
| `tests/` | Automated honesty checks |
| `qa.bat` | Quality gate |
| `build.bat` | Portable EXE |
| `docs/` | Extended docs EN+FA |
| `SECURITY.md` | Vulnerability reporting |

## Language

User-facing UI strings in the app are primarily **Persian (RTL)**. Repository documentation defaults to **English** with Persian translations.
