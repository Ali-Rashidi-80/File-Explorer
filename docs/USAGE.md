# Usage guide

**Languages:** **English** · [فارسی](USAGE.fa.md)

## Launch

```bat
pip install -r requirements.txt
python file-explorer-pyside6.py
```

Or run `dist\FileExplorer_Portable.exe` after building.

## Scan tab

1. Choose **mode**
   - Full — extract text/code contents into one TXT report
   - Structure only — tree map only
2. Choose **format**
   - TXT — always available
   - JSON — enabled only for structure mode
3. Select a project folder (button or Drag & Drop onto the window).
4. Click **Start scan**.
5. Watch the progress bar and the live tree on the right.
6. Use menu **Edit → Copy all** or **File → Save output**.

### What full mode writes

For each non-ignored, non-symlink file:

- Text-like files under 10 MB → content appended
- Oversized text → warning marker, content skipped
- Binary / non-text → binary marker with size
- When cumulative UTF-8 bytes exceed 50 MB → stop with a cap message

### What structure mode writes

- **TXT:** Persian header + ASCII tree with `├──` / `└──`
- **JSON:** nested `{name, type, children}` objects

## Reverse tab

1. Select a previously saved **TXT or JSON** map.
2. Choose an **output directory**.
3. Start reverse rebuild.
4. Confirm the empty scaffold was created.

> **Honest limit:** file bodies are **not** restored. Only directories and empty files are created.

## Menus

| Menu | Actions |
|------|---------|
| File | Select folder, Save output, Exit |
| Edit | Copy all content, Clear editor |
| Help | About (v5.1 feature summary) |

## Drag & Drop

Drop a folder onto the window to set it as the scan root (when not busy).

## Tips

- Prefer **structure JSON** when you need machine-readable scaffolds.
- Prefer **full TXT** when feeding an LLM with code context — mind the 50 MB cap on huge monorepos.
- Keep secrets out of exported maps (`.env` may be treated as text if present and not ignored by name heuristics — review before sharing).

## See also

- [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- [API.md](API.md)
- [../README.md](../README.md)
