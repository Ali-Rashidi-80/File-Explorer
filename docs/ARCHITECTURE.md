# Architecture

**Languages:** **English** · [فارسی](ARCHITECTURE.fa.md)

## Overview

File Explorer v5.1 is a single-module PySide6 desktop application. Business logic that can run without a GUI lives as **pure helpers** at the top of `file-explorer-pyside6.py`. Long-running I/O runs on **QThread** workers so the UI stays responsive.

```mermaid
flowchart TB
  subgraph Presentation
    MW[MainWindow]
    AD[AboutDialog]
  end

  subgraph DomainWorkers
    FS[FileScanner]
    RS[ReverseScanner]
  end

  subgraph DomainPure
    H1[Tree build / generate]
    H2[TXT parse]
    H3[Path safety]
    H4[Text heuristic + read]
    H5[JSON create_from_json]
  end

  MW --> FS
  MW --> RS
  MW --> AD
  FS --> H1
  FS --> H4
  RS --> H2
  RS --> H3
  RS --> H5
```

## Layers

| Layer | Components | Responsibility |
|-------|------------|----------------|
| UI | `MainWindow`, `AboutDialog` | Menus, tabs, DnD, theme, progress, save/copy |
| Workers | `FileScanner`, `ReverseScanner` | Background scan / reverse; emit signals |
| Pure core | helpers listed below | Deterministic, unit-tested filesystem logic |

## Threading model

```mermaid
stateDiagram-v2
  [*] --> Idle
  Idle --> BusyScan: start scanning
  Idle --> BusyReverse: start reverse
  BusyScan --> Idle: finished / error / interrupt
  BusyReverse --> Idle: finished / error / interrupt
  BusyScan --> BusyScan: second job rejected
  BusyReverse --> BusyReverse: second job rejected
```

- Separate attributes: `scan_thread`, `reverse_thread`
- Busy flag disables conflicting controls
- `closeEvent` requests interruption and waits briefly for clean shutdown

## Scan pipeline

1. Build in-memory tree (`build_tree_data`) → emit for UI preview.
2. **Structure mode:** emit TXT tree lines or JSON dump.
3. **Full mode:** `os.walk` with ignored dirs + symlink skip; for each file apply text heuristic; append content or markers; enforce byte caps; emit progress.

## Reverse pipeline

1. Read map as UTF-8 (long-path fallback on Windows).
2. **TXT:** `parse_txt_structure` → mkdir/touch via `safe_join_under`.
3. **JSON:** `create_from_json` recursively with the same join guard.

## Packaging topology

```mermaid
flowchart LR
  SRC[file-explorer-pyside6.py + icon.ico]
  SPEC[FileExplorer.portable.spec]
  PI[PyInstaller onefile]
  EXE[dist/FileExplorer_Portable.exe]
  SRC --> SPEC --> PI --> EXE
```

## Testing topology

| Test module | Proves |
|-------------|--------|
| `test_scanner_core` | Path guards, parse levels, helper contracts |
| `test_live_e2e` | Real threads + MainWindow happy paths |
| `test_production_live` | Unicode / stress / busy guards |
| `test_qa_tooling` | Tooling expectations |

## Related

- [USAGE.md](USAGE.md) — operator flows
- [API.md](API.md) — helper signatures
- [BUILD.md](BUILD.md) — EXE pipeline
- [../SECURITY.md](../SECURITY.md) — threat model notes
