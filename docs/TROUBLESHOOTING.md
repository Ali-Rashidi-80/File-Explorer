# Troubleshooting

**Languages:** **English** · [فارسی](TROUBLESHOOTING.fa.md)

## Runtime

### `ModuleNotFoundError: No module named 'PySide6'`

```bat
pip install -r requirements.txt
```

Confirm the same interpreter:

```bat
python -c "import PySide6; print(PySide6.__version__)"
```

### Window opens then closes / Qt plugin errors

- Reinstall PySide6.
- On headless CI, set `QT_QPA_PLATFORM=offscreen` (tests already do this).
- GPU / remote desktop quirks: try updating GPU drivers or run from source.

### Drag & Drop does nothing

- Ensure the drop target is a **folder**.
- App must not be busy (scan/reverse in progress).

### Scan seems stuck on huge repos

- Full mode may take time; watch the progress bar.
- Hitting the **50 MB** cap stops content extraction by design.
- Ignored dirs still skip `.git` / `node_modules` — verify you are not scanning an unexpected root.

### JSON option greyed out / ignored

By design in **full** mode. Switch to **structure only**.

### Reverse created empty files

By design. Content restore is not implemented in v5.1.

### Path rejected during reverse

The map likely contains `..`, absolute segments, illegal characters, or Windows reserved names. Sanitize the map or regenerate from a trusted scan.

## Build

### `Python not found` in `build.bat`

Install Python 3.10+, tick “Add to PATH”, reopen CMD/PowerShell.

### PyInstaller fails / missing EXE

- Scroll up for the first Python traceback.
- Delete `build\FileExplorer_Portable` and `dist\FileExplorer_Portable.exe`, then rebuild.
- Antivirus locking Qt DLLs can cause file-in-use errors — retry after a moment.

### EXE is very large

Expected for Qt onefile bundles (tens of MB). UPX may shrink modestly when available.

## Tests / QA

### pytest cannot import the app

Tests load `file-explorer-pyside6.py` by path; keep that filename stable.

### `qa.bat` fails on formatting

```bat
python -m isort file-explorer-pyside6.py tests
python -m black file-explorer-pyside6.py tests
```

Then re-run `qa.bat`.

### bandit / pylint noise

`qa.bat` uses bandit medium+ and pylint errors-only. Fix real findings; do not blanket-disable without cause.

## Still stuck?

Open an issue with OS, Python version, PySide6 version, exact command, and logs:
https://github.com/Ali-Rashidi-80/File-Explorer/issues
