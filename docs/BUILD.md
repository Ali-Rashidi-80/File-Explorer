# Build guide (portable EXE)

**Languages:** **English** · [فارسی](BUILD.fa.md)

## Goal

Produce a **single-file** Windows executable:

`dist\FileExplorer_Portable.exe`

No install step on the target machine. First launch may unpack briefly.

## One command

```bat
build_portable.bat
```

(`build_portable.bat` delegates to `build.bat`.)

## What `build.bat` does

| Step | Action |
|------|--------|
| 1 | Verify Python on `PATH` |
| 2 | `pip install` PySide6 + PyInstaller |
| 3 | Find or download UPX into `tools\upx` (optional) |
| 4 | Remove previous portable `build\` / `dist\` artifacts |
| 5 | `python -m PyInstaller --noconfirm [ --upx-dir … ] FileExplorer.portable.spec` |
| 6 | Verify the EXE exists and print approximate size |

## Spec highlights (`FileExplorer.portable.spec`)

- Entry: `file-explorer-pyside6.py`
- Onefile `EXE` named `FileExplorer_Portable`
- `console=False` (windowed)
- Embeds `icon.ico` when present
- Excludes heavy unused stacks (tkinter, numpy, pandas, PyQt5/6, …)
- UPX enabled with excludes for sensitive Qt/Python DLLs

## Manual PyInstaller

```bat
python -m PyInstaller --noconfirm FileExplorer.portable.spec
```

See also [`../pyinstaller.txt`](../pyinstaller.txt).

## Common build failures

| Problem | Mitigation |
|---------|------------|
| Python not found | Install Python 3.10+ and reopen the shell |
| WinError 32 on clean | Script avoids global `--clean`; delete only portable outputs |
| Missing icon | Build continues; default Qt icon at runtime |
| Huge EXE | Expected with Qt; UPX helps modestly when available |

## Artifacts (gitignored)

- `build/`
- `dist/`
- `tools/upx/` (downloaded compressor)

Do not commit binaries unless the project explicitly decides to release them via GitHub Releases.
