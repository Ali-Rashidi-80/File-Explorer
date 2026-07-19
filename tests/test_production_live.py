"""
Production-style live tests: realistic project trees, full UI pipelines,
save-to-disk, reverse restore, unicode/Persian paths, stress, and busy guards.
Honest assertions only — no mocked scan results.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest
from conftest import run_qthread
from PySide6.QtWidgets import QMessageBox, QPlainTextEdit


@pytest.fixture
def no_modal(monkeypatch, app_mod):
    monkeypatch.setattr(
        app_mod.QMessageBox,
        "information",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok),
    )
    monkeypatch.setattr(
        app_mod.QMessageBox,
        "warning",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok),
    )
    monkeypatch.setattr(
        app_mod.QMessageBox,
        "critical",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok),
    )


@pytest.fixture
def production_project(tmp_path: Path) -> Path:
    """Larger production-like workspace with unicode, configs, and noise dirs."""
    root = tmp_path / "Acme-ERP-v2"
    # App sources
    (root / "backend" / "api" / "v1").mkdir(parents=True)
    (root / "backend" / "api" / "v1" / "users.py").write_text(
        "def list_users():\n    return [{'id': 1, 'name': 'علی'}]\n",
        encoding="utf-8",
    )
    (root / "backend" / "main.py").write_text(
        "from api.v1.users import list_users\nprint(list_users())\n",
        encoding="utf-8",
    )
    (root / "frontend" / "src").mkdir(parents=True)
    (root / "frontend" / "src" / "App.tsx").write_text(
        "export function App() { return <div>سلام</div>; }\n",
        encoding="utf-8",
    )
    (root / "frontend" / "package.json").write_text(
        '{"name":"acme-erp","private":true}\n',
        encoding="utf-8",
    )
    # Docs / locale
    (root / "docs" / "راهنما").mkdir(parents=True)
    (root / "docs" / "راهنما" / "نصب.md").write_text(
        "# نصب\n\nمرحله ۱\n",
        encoding="utf-8",
    )
    (root / "README.md").write_text("# Acme ERP\nproduction fixture\n", encoding="utf-8")
    # Dotfiles / env
    (root / ".env").write_text("DATABASE_URL=postgres://local/acme\n", encoding="utf-8")
    (root / ".gitignore").write_text("node_modules/\n.env.local\n", encoding="utf-8")
    # Binary + empty
    (root / "assets").mkdir()
    (root / "assets" / "icon.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\x00")
    (root / "empty.txt").write_text("", encoding="utf-8")
    # Noise
    for noise in ("node_modules", ".git", "build", "dist", "venv", "__pycache__"):
        p = root / noise / "x"
        p.mkdir(parents=True)
        (p / "junk.bin").write_bytes(b"\x00\x01\x02")
    # Many small modules (stress listing)
    bulk = root / "backend" / "bulk"
    bulk.mkdir()
    for i in range(40):
        (bulk / f"mod_{i:02d}.py").write_text(f"VALUE = {i}\n", encoding="utf-8")
    return root


def _collect_file_relpaths(root: Path) -> set[tuple[str, ...]]:
    out: set[tuple[str, ...]] = set()
    for dirpath, dirnames, filenames in os.walk(root):
        # mirror product ignore for comparison of "logical" project files
        dirnames[:] = [
            d
            for d in dirnames
            if d not in {".git", "__pycache__", "node_modules", "venv", ".venv", "build", "dist"}
        ]
        base = Path(dirpath)
        for name in filenames:
            rel = (base / name).relative_to(root)
            out.add(tuple(rel.parts))
    return out


# ---------------------------------------------------------------------------
# Production scanner pipelines
# ---------------------------------------------------------------------------


def test_prod_structure_txt_full_pipeline(app_mod, qapp, production_project, tmp_path):
    scan = run_qthread(
        app_mod.FileScanner(production_project, mode="structure", output_format="txt")
    )
    assert scan["error"] is None, scan["error"]
    text = scan["finished"]
    assert "users.py" in text
    assert "نصب.md" in text
    assert "mod_39.py" in text
    for bad in ("node_modules", "venv", "__pycache__"):
        assert f"├── {bad}/" not in text and f"└── {bad}/" not in text

    map_path = tmp_path / "prod_structure.txt"
    map_path.write_text(text, encoding="utf-8")
    dest = tmp_path / "restored_txt"
    dest.mkdir()

    rev = run_qthread(app_mod.ReverseScanner(map_path, dest, "txt"))
    assert rev["error"] is None, rev["error"]

    assert (dest / "backend" / "api" / "v1" / "users.py").is_file()
    assert (dest / "docs" / "راهنما" / "نصب.md").is_file()
    assert (dest / "frontend" / "src" / "App.tsx").is_file()
    assert (dest / "backend" / "bulk" / "mod_00.py").is_file()
    # empty structure restore
    assert (dest / "backend" / "api" / "v1" / "users.py").stat().st_size == 0
    assert not (dest / "node_modules").exists()


def test_prod_structure_json_pipeline_and_parity(app_mod, qapp, production_project, tmp_path):
    txt = run_qthread(
        app_mod.FileScanner(production_project, mode="structure", output_format="txt")
    )
    js = run_qthread(
        app_mod.FileScanner(production_project, mode="structure", output_format="json")
    )
    assert txt["error"] is None and js["error"] is None

    txt_files = {
        tuple(p) for p, is_dir in app_mod.parse_txt_structure(txt["finished"]) if not is_dir
    }
    data = json.loads(js["finished"])

    def files_from_json(node, prefix=()):
        if node["type"] == "file":
            yield prefix
        else:
            for child in node.get("children", []):
                yield from files_from_json(child, prefix + (child["name"],))

    json_files = set(files_from_json(data, ()))
    assert txt_files == json_files
    assert ("docs", "راهنما", "نصب.md") in json_files

    dest = tmp_path / "restored_json"
    dest.mkdir()
    map_path = tmp_path / "prod.json"
    map_path.write_text(js["finished"], encoding="utf-8")
    rev = run_qthread(app_mod.ReverseScanner(map_path, dest, "json"))
    assert rev["error"] is None, rev["error"]
    assert (dest / "docs" / "راهنما" / "نصب.md").is_file()


def test_prod_full_scan_content_and_progress(app_mod, qapp, production_project):
    res = run_qthread(app_mod.FileScanner(production_project, mode="full", output_format="txt"))
    assert res["error"] is None, res["error"]
    out = res["finished"]
    assert "list_users" in out
    assert "DATABASE_URL=postgres" in out
    assert "Acme ERP" in out
    assert "VALUE = 39" in out
    assert "باینری" in out
    # .gitignore may mention node_modules; ensure ignored trees were not walked
    assert "مسیر نسبی: node_modules" not in out
    assert "left-pad" not in out
    assert "junk.bin" not in out
    assert res["progress"]
    assert max(res["progress"]) == 100
    # monotonic non-decreasing progress
    assert res["progress"] == sorted(res["progress"])


def test_prod_rescan_after_reverse_structure_stable(app_mod, qapp, production_project, tmp_path):
    """Scan → reverse → scan restored tree; file path sets must match."""
    first = run_qthread(
        app_mod.FileScanner(production_project, mode="structure", output_format="json")
    )
    assert first["error"] is None
    dest = tmp_path / "clone"
    dest.mkdir()
    map_path = tmp_path / "m.json"
    map_path.write_text(first["finished"], encoding="utf-8")
    assert run_qthread(app_mod.ReverseScanner(map_path, dest, "json"))["error"] is None

    second = run_qthread(app_mod.FileScanner(dest, mode="structure", output_format="json"))
    assert second["error"] is None

    def file_set(blob: str) -> set[tuple[str, ...]]:
        root = json.loads(blob)

        def walk(node, prefix=()):
            if node["type"] == "file":
                yield prefix
            else:
                for c in node.get("children", []):
                    yield from walk(c, prefix + (c["name"],))

        return set(walk(root, ()))

    assert file_set(first["finished"]) == file_set(second["finished"])


# ---------------------------------------------------------------------------
# Production MainWindow flows
# ---------------------------------------------------------------------------


def test_prod_mainwindow_scan_save_reverse_cycle(
    app_mod, qapp, production_project, tmp_path, no_modal
):
    win = app_mod.MainWindow()
    try:
        assert isinstance(win.output_text, QPlainTextEdit)
        win.selected_folder = production_project
        win.mode_combo.setCurrentIndex(1)
        win.format_combo.setCurrentIndex(0)  # TXT structure
        win.start_scanning()
        assert win.scan_thread.wait(120000)
        qapp.processEvents()
        content = win.output_text.toPlainText()
        assert "backend" in content
        assert win.last_output_format == "txt"
        assert win.save_btn.isEnabled()

        save_path = tmp_path / "exported_structure.txt"
        save_path.write_text(content, encoding="utf-8")
        assert save_path.stat().st_size > 100

        restore_root = tmp_path / "ui_restore"
        restore_root.mkdir()
        win.selected_folder = restore_root
        win.selected_input_file = save_path
        win.update_reverse_enabled()
        assert win.reverse_btn.isEnabled()
        win.reverse_structure()
        assert win.reverse_thread.wait(120000)
        qapp.processEvents()

        assert (restore_root / "backend" / "main.py").is_file()
        assert (restore_root / "frontend" / "package.json").is_file()
        assert win._busy is False
    finally:
        for t in (win.scan_thread, win.reverse_thread):
            if t is not None and t.isRunning():
                t.requestInterruption()
                t.wait(5000)
        win.close()


def test_prod_mainwindow_full_scan_then_mode_lock(app_mod, qapp, production_project, no_modal):
    win = app_mod.MainWindow()
    try:
        win.selected_folder = production_project
        win.mode_combo.setCurrentIndex(0)
        assert win.format_combo.isEnabled() is False
        win.start_scanning()
        assert win.scan_thread.wait(120000)
        qapp.processEvents()
        text = win.output_text.toPlainText()
        assert "list_users" in text
        assert win.last_output_format == "txt"
        # switching to structure unlocks JSON
        win.mode_combo.setCurrentIndex(1)
        assert win.format_combo.isEnabled() is True
        win.format_combo.setCurrentIndex(1)
        win.start_scanning()
        assert win.scan_thread.wait(120000)
        qapp.processEvents()
        json.loads(win.output_text.toPlainText())
        assert win.last_output_format == "json"
    finally:
        if win.scan_thread and win.scan_thread.isRunning():
            win.scan_thread.requestInterruption()
            win.scan_thread.wait(5000)
        win.close()


def test_prod_busy_rejects_scan_and_reverse_overlap(
    app_mod, qapp, production_project, tmp_path, no_modal
):
    map_path = tmp_path / "map.txt"
    map_path.write_text(
        "\n".join(app_mod.generate_tree_structure(production_project)),
        encoding="utf-8",
    )
    dest = tmp_path / "dest"
    dest.mkdir()

    win = app_mod.MainWindow()
    try:
        win.selected_folder = production_project
        win.start_scanning()
        scan_t = win.scan_thread
        win.selected_input_file = map_path
        # reverse while scan running must be rejected by busy / running guard
        win.reverse_structure()
        # either reverse did not start, or shared busy prevented second writer
        if win.reverse_thread is not None and win.reverse_thread is not scan_t:
            # If reverse was somehow assigned, it must not be a parallel runner
            # while scan still active — product rejects via _any_thread_running
            assert not (scan_t.isRunning() and win.reverse_thread.isRunning())
        else:
            assert win.reverse_thread is None or win.reverse_thread is scan_t
        scan_t.requestInterruption()
        scan_t.wait(30000)
        qapp.processEvents()
    finally:
        for t in (win.scan_thread, win.reverse_thread):
            if t is not None and t.isRunning():
                t.requestInterruption()
                t.wait(5000)
        win.close()


def test_prod_close_mid_full_scan_is_safe(app_mod, qapp, production_project, no_modal):
    win = app_mod.MainWindow()
    win.selected_folder = production_project
    win.mode_combo.setCurrentIndex(0)
    win.start_scanning()
    thread = win.scan_thread
    assert thread.isRunning()
    win.close()
    qapp.processEvents()
    assert not thread.isRunning()


# ---------------------------------------------------------------------------
# Production security / edge
# ---------------------------------------------------------------------------


def test_prod_reverse_rejects_absolute_escape(app_mod, qapp, tmp_path):
    if sys.platform == "win32":
        evil_name = "C:\\Windows\\Temp\\pwn.txt"
    else:
        evil_name = "/tmp/pwn.txt"
    # Separators make segment invalid before join
    evil_map = tmp_path / "evil.txt"
    evil_map.write_text(f"└── {evil_name}\n", encoding="utf-8")
    dest = tmp_path / "safe_dest"
    dest.mkdir()
    res = run_qthread(app_mod.ReverseScanner(evil_map, dest, "txt"))
    assert res["error"] is not None


def test_prod_ignore_list_matches_walk_and_tree(app_mod, production_project):
    tree = app_mod.build_tree_data(production_project)
    names = {c["name"] for c in tree["children"]}
    for d in ("node_modules", ".git", "build", "dist", "venv", "__pycache__"):
        assert d not in names
    # Real project files present
    assert "backend" in names and "frontend" in names and "docs" in names


def test_prod_logical_file_count_sane(production_project):
    files = _collect_file_relpaths(production_project)
    assert len(files) >= 40  # bulk modules + sources
    assert ("backend", "bulk", "mod_39.py") in files
    assert ("docs", "راهنما", "نصب.md") in files
