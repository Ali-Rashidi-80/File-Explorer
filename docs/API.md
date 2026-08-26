# API — pure helpers

**Languages:** **English** · [فارسی](API.fa.md)

These helpers live in `file-explorer-pyside6.py` and are imported by tests via `importlib`. They are the stable logic surface for contributors.

## Path safety

### `is_valid_path_segment(name: str) -> bool`

Rejects empty, `.`, `..`, trailing space/dot, absolute paths, invalid Win characters, and Windows reserved device names.

### `safe_join_under(root, *parts) -> Path`

Joins one segment at a time under `root`, resolves, and requires `is_relative_to(root)`. Raises `ValueError` on dangerous input.

### `win_long_path(path: Path) -> Path`

On Windows, prefixes `\\?\` (or UNC form) for long-path APIs.

### `mkdir_safe` / `touch_safe`

Create dirs/files with long-path fallback on `OSError`.

## Tree & text

### `is_ignored_dir_name(name: str) -> bool`

Membership in `IGNORED_DIRS`.

### `is_text_file_heuristic(filepath) -> bool`

Extension / known filename allow-list, null-byte sniff, small-file heuristic.

### `generate_tree_structure(root_path, prefix="") -> list[str]`

ASCII tree lines for structure TXT export.

### `build_tree_data(path: Path) -> dict`

Nested `{name, type, children}` for JSON and UI.

### `parse_txt_structure(content: str) -> list[tuple[list[str], bool]]`

Parses `├──` / `└──` lines; level from connector column index (`// 4`); skips `[meta]` names.

### `count_tree_nodes(node: dict) -> int`

Recursive node count for UI expansion guards.

### `read_file_content(file_path) -> str`

Tries encodings: utf-8, utf-8-sig, cp1252, latin-1; long-path retry on Windows.

### `create_from_json(node, output_root: Path, current_rel=()) -> None`

Recursively materializes empty dirs/files under `output_root` via `safe_join_under`.

## Workers (signals)

| Class | Key signals |
|-------|-------------|
| `FileScanner` | `progress(int)`, `finished(str)`, `error(str)`, `tree_data(dict)` |
| `ReverseScanner` | `finished(str)`, `error(str)`, `preview(str)` |

Constructor notes:

- `FileScanner(root_path, mode="full"|"structure", output_format="txt"|"json")`
- `ReverseScanner(map_file_path, output_path, input_format="txt"|"json")`

## Constants

| Name | Meaning |
|------|---------|
| `KNOWN_TEXT_EXTENSIONS` | Suffix allow-list |
| `KNOWN_TEXT_FILENAMES` | Name allow-list (`dockerfile`, `.gitignore`, …) |
| `IGNORED_DIRS` | Directory names skipped |
| `MAX_TEXT_FILE_SIZE_MB` | Per-file skip threshold (`10`) |
| `MAX_TOTAL_OUTPUT_BYTES` | Full-scan cap (`50 * 1024 * 1024`) |
| `MAX_TREE_EXPAND_NODES` | UI tree expansion guard (`2000`) |

There is no published installable Python package API in v5.1 — the desktop app is the product.
