# Contributing

**Languages:** **English** · [فارسی](CONTRIBUTING.fa.md)

Thanks for helping improve File Explorer. This guide keeps contributions safe, testable, and honest.

## Code of conduct

Participation is governed by [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Security reports

Do **not** file public issues for vulnerabilities. Follow [SECURITY.md](SECURITY.md).

## Development setup

```bat
git clone https://github.com/Ali-Rashidi-80/File-Explorer.git
cd "File-Explorer"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
python file-explorer-pyside6.py
```

## Project rules (please respect)

1. **Active app** = `file-explorer-pyside6.py`. Do not expand `file_explorer.py` unless fixing a doc pointer.
2. **Reverse = empty scaffold** unless a PR explicitly adds opt-in content restore with caps and tests.
3. **JSON only in structure mode** — keep the UI lock and tests aligned.
4. Prefer pure helpers at module top for logic that can be unit-tested without GUI.
5. No secrets in the repo. No drive-by refactors unrelated to the PR goal.

## Quality gate

Before opening a PR, run:

```bat
qa.bat
```

Or the equivalent pieces:

```bat
python -m pytest tests -q
python -m ruff check file-explorer-pyside6.py tests
python -m black --check file-explorer-pyside6.py tests
python -m mypy file-explorer-pyside6.py tests
```

## Pull request process

1. Fork / branch from `main` (`feat/…`, `fix/…`, `docs/…`).
2. Add or update tests for behavior changes (especially path safety and scan/reverse).
3. Update docs (`README.md` / `README.fa.md` and relevant `docs/*`) when user-facing behavior changes.
4. Keep commits focused; describe **why** in the PR body.
5. Link related issues.

### PR checklist

- [ ] `qa.bat` passes locally
- [ ] New behavior has tests
- [ ] Docs updated (EN + FA when applicable)
- [ ] No accidental scope creep on legacy `file_explorer.py`

## Issue guidelines

- **Bug:** steps, expected/actual, OS, Python/PySide6 versions, sample folder if possible
- **Feature:** problem statement, proposed UX, honesty about limits (size caps, reverse semantics)

## Questions

Open a [GitHub Issue](https://github.com/Ali-Rashidi-80/File-Explorer/issues) for discussion.
