from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def app_mod():
    path = ROOT / "file-explorer-pyside6.py"
    spec = importlib.util.spec_from_file_location("file_explorer_app", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def sample_project(tmp_path):
    """Realistic nested project used by live E2E tests."""
    root = tmp_path / "demo_project"
    (root / "src" / "pkg").mkdir(parents=True)
    (root / "src" / "pkg" / "__init__.py").write_text("# init\n", encoding="utf-8")
    (root / "src" / "pkg" / "core.py").write_text(
        "def add(a, b):\n    return a + b\n", encoding="utf-8"
    )
    (root / "src" / "main.py").write_text(
        "from pkg.core import add\nprint(add(2, 3))\n", encoding="utf-8"
    )
    (root / "docs").mkdir()
    (root / "docs" / "README.md").write_text("# Demo\n\nlive test project\n", encoding="utf-8")
    (root / ".env").write_text("SECRET=demo\n", encoding="utf-8")
    (root / ".gitignore").write_text("*.pyc\n", encoding="utf-8")
    (root / "assets").mkdir()
    (root / "assets" / "logo.bin").write_bytes(b"\x00PNG\x00\x01\x02\x03")
    # Noise that must be ignored by scanner/tree
    (root / "node_modules" / "left-pad").mkdir(parents=True)
    (root / "node_modules" / "left-pad" / "index.js").write_text(
        "module.exports=1\n", encoding="utf-8"
    )
    (root / ".git" / "objects").mkdir(parents=True)
    (root / ".git" / "objects" / "pack").write_bytes(b"\x00\x00")
    (root / "build" / "out").mkdir(parents=True)
    (root / "build" / "out" / "app.exe").write_bytes(b"MZ\x00\x00")
    (root / "empty.txt").write_text("", encoding="utf-8")
    return root


def run_qthread(thread, timeout_ms=60000):
    """Drive a QThread to completion via Qt event loop; fail honestly on hang."""
    from PySide6.QtCore import QEventLoop, QTimer

    loop = QEventLoop()
    box: dict[str, Any] = {
        "finished": None,
        "error": None,
        "tree": None,
        "preview": None,
        "progress": [],
    }

    def on_finished(v):
        box["finished"] = v
        loop.quit()

    def on_error(e):
        box["error"] = e
        loop.quit()

    thread.finished.connect(on_finished)
    thread.error.connect(on_error)
    if hasattr(thread, "tree_data"):
        thread.tree_data.connect(lambda t: box.__setitem__("tree", t))
    if hasattr(thread, "preview"):
        thread.preview.connect(lambda t: box.__setitem__("preview", t))
    if hasattr(thread, "progress"):
        progress_list: list[int] = box["progress"]
        thread.progress.connect(progress_list.append)

    thread.start()
    QTimer.singleShot(timeout_ms, loop.quit)
    loop.exec()
    if thread.isRunning():
        thread.wait(5000)
    if thread.isRunning():
        thread.requestInterruption()
        thread.wait(3000)
        pytest.fail(f"{type(thread).__name__} did not finish within {timeout_ms}ms")
    return box
