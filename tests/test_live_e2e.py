"""
Live end-to-end tests: real QThreads, real filesystem, real MainWindow flows.
No mocked scanner outputs. QMessageBox is stubbed only to avoid modal deadlock in CI.
"""

import json
import sys
from pathlib import Path

import pytest
from conftest import run_qthread
from PySide6.QtCore import QMimeData, QUrl
from PySide6.QtWidgets import QLabel, QMessageBox


@pytest.fixture
def no_modal(monkeypatch, app_mod):
    """Prevent QMessageBox.information/warning/critical from blocking the test thread."""
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


# ---------------------------------------------------------------------------
# Live scan ↔ reverse round-trips
# ---------------------------------------------------------------------------


def test_live_structure_txt_scan_reverse_roundtrip(app_mod, qapp, sample_project, tmp_path):
    out_dir = tmp_path / "restored_txt"
    out_dir.mkdir()
    map_path = tmp_path / "structure.txt"

    scan = app_mod.FileScanner(sample_project, mode="structure", output_format="txt")
    res = run_qthread(scan)
    assert res["error"] is None, res["error"]
    assert res["finished"]
    assert "core.py" in res["finished"]
    # Ignore-dirs must not appear as tree nodes (.gitignore file name is OK)
    assert "├── node_modules/" not in res["finished"] and "└── node_modules/" not in res["finished"]
    assert "├── .git/" not in res["finished"] and "└── .git/" not in res["finished"]
    assert "├── build/" not in res["finished"] and "└── build/" not in res["finished"]
    assert ".gitignore" in res["finished"]
    map_path.write_text(res["finished"], encoding="utf-8")

    rev = app_mod.ReverseScanner(map_path, out_dir, "txt")
    r2 = run_qthread(rev)
    assert r2["error"] is None, r2["error"]
    assert (out_dir / "src" / "pkg" / "core.py").is_file()
    assert (out_dir / "src" / "main.py").is_file()
    assert (out_dir / "docs" / "README.md").is_file()
    assert (out_dir / ".env").is_file()
    assert (out_dir / "empty.txt").is_file()
    assert (out_dir / "src" / "pkg" / "core.py").read_text(encoding="utf-8") == ""
    assert not (out_dir / "node_modules").exists()
    assert not (out_dir / ".git").exists()
    assert not (out_dir / "build").exists()


def test_live_structure_json_scan_reverse_roundtrip(app_mod, qapp, sample_project, tmp_path):
    out_dir = tmp_path / "restored_json"
    out_dir.mkdir()
    map_path = tmp_path / "structure.json"

    scan = app_mod.FileScanner(sample_project, mode="structure", output_format="json")
    res = run_qthread(scan)
    assert res["error"] is None, res["error"]
    data = json.loads(res["finished"])
    assert data["type"] == "directory"
    names = {c["name"] for c in data["children"]}
    assert "src" in names and "docs" in names
    assert "node_modules" not in names and "build" not in names and ".git" not in names
    map_path.write_text(res["finished"], encoding="utf-8")

    rev = app_mod.ReverseScanner(map_path, out_dir, "json")
    r2 = run_qthread(rev)
    assert r2["error"] is None, r2["error"]
    assert (out_dir / "src" / "pkg" / "core.py").is_file()
    assert (out_dir / "docs" / "README.md").is_file()
    assert (out_dir / "assets" / "logo.bin").is_file()


def test_live_full_scan_extracts_text_skips_noise(app_mod, qapp, sample_project):
    scan = app_mod.FileScanner(sample_project, mode="full", output_format="txt")
    res = run_qthread(scan)
    assert res["error"] is None, res["error"]
    out = res["finished"]
    assert "def add(a, b)" in out
    assert "SECRET=demo" in out
    assert "live test project" in out
    assert "باینری" in out
    assert "node_modules" not in out
    assert "\\.git\\" not in out and "/.git/" not in out
    assert "objects" not in out  # from ignored .git/objects
    assert res["progress"], "full scan must emit progress percentages"
    assert max(res["progress"]) == 100
    assert res["tree"] is not None
    tree_names = {c["name"] for c in res["tree"]["children"]}
    assert "node_modules" not in tree_names
    assert "build" not in tree_names


def test_live_full_then_structure_modes_differ(app_mod, qapp, sample_project):
    full = run_qthread(app_mod.FileScanner(sample_project, mode="full", output_format="txt"))
    struct = run_qthread(app_mod.FileScanner(sample_project, mode="structure", output_format="txt"))
    assert full["error"] is None and struct["error"] is None
    assert "def add" in full["finished"]
    assert "def add" not in struct["finished"]
    assert "├──" in struct["finished"] or "└──" in struct["finished"]


# ---------------------------------------------------------------------------
# Live attack / safety maps through ReverseScanner
# ---------------------------------------------------------------------------


def test_live_reverse_blocks_txt_zipslip(app_mod, qapp, tmp_path):
    evil_map = tmp_path / "evil.txt"
    evil_map.write_text(
        "\n".join(
            [
                "├── safe/",
                "│   └── ok.txt",
                "└── ../escape.txt",
            ]
        ),
        encoding="utf-8",
    )
    dest = tmp_path / "dest"
    dest.mkdir()
    (dest / "marker").write_text("keep", encoding="utf-8")

    res = run_qthread(app_mod.ReverseScanner(evil_map, dest, "txt"))
    assert res["error"] is not None
    assert not (tmp_path / "escape.txt").exists()
    assert (dest / "marker").read_text(encoding="utf-8") == "keep"


def test_live_reverse_blocks_json_zipslip(app_mod, qapp, tmp_path):
    evil = {
        "name": "root",
        "type": "directory",
        "children": [
            {"name": "ok.txt", "type": "file"},
            {"name": "..", "type": "file"},
        ],
    }
    map_path = tmp_path / "evil.json"
    map_path.write_text(json.dumps(evil), encoding="utf-8")
    dest = tmp_path / "dest"
    dest.mkdir()
    res = run_qthread(app_mod.ReverseScanner(map_path, dest, "json"))
    assert res["error"] is not None


def test_live_reverse_blocks_windows_reserved(app_mod, qapp, tmp_path):
    if sys.platform != "win32":
        pytest.skip("Windows only")
    evil_map = tmp_path / "reserved.txt"
    evil_map.write_text("└── NUL\n", encoding="utf-8")
    dest = tmp_path / "dest"
    dest.mkdir()
    res = run_qthread(app_mod.ReverseScanner(evil_map, dest, "txt"))
    assert res["error"] is not None


def test_live_reverse_invalid_json_errors(app_mod, qapp, tmp_path):
    map_path = tmp_path / "bad.json"
    map_path.write_text("{not-json", encoding="utf-8")
    dest = tmp_path / "dest"
    dest.mkdir()
    res = run_qthread(app_mod.ReverseScanner(map_path, dest, "json"))
    assert res["error"] is not None


# ---------------------------------------------------------------------------
# Live MainWindow workflows
# ---------------------------------------------------------------------------


def test_live_mainwindow_scan_structure_json_and_save_format(
    app_mod, qapp, sample_project, no_modal
):
    win = app_mod.MainWindow()
    try:
        win.selected_folder = sample_project
        win.start_btn.setEnabled(True)
        win.mode_combo.setCurrentIndex(1)
        win.format_combo.setCurrentIndex(1)
        assert win.format_combo.isEnabled() is True

        win.start_scanning()
        assert win._busy is True
        thread = win.scan_thread
        assert thread is not None
        assert thread.wait(60000)
        qapp.processEvents()

        text = win.output_text.toPlainText()
        assert text.strip()
        data = json.loads(text)
        assert data["type"] == "directory"
        assert win.last_output_format == "json"
        assert win.save_btn.isEnabled() is True
        assert win._busy is False
    finally:
        if win.scan_thread and win.scan_thread.isRunning():
            win.scan_thread.requestInterruption()
            win.scan_thread.wait(5000)
        win.close()


def test_live_mainwindow_full_scan_locks_json(app_mod, qapp, sample_project, no_modal):
    win = app_mod.MainWindow()
    try:
        win.mode_combo.setCurrentIndex(1)
        win.format_combo.setCurrentIndex(1)
        win.mode_combo.setCurrentIndex(0)
        assert win.format_combo.currentIndex() == 0
        assert win.format_combo.isEnabled() is False

        win.selected_folder = sample_project
        win.start_scanning()
        assert win.scan_thread.wait(60000)
        qapp.processEvents()

        assert "def add" in win.output_text.toPlainText()
        assert win.last_output_format == "txt"
    finally:
        if win.scan_thread and win.scan_thread.isRunning():
            win.scan_thread.requestInterruption()
            win.scan_thread.wait(5000)
        win.close()


def test_live_mainwindow_reverse_flow(app_mod, qapp, sample_project, tmp_path, no_modal):
    scan = run_qthread(app_mod.FileScanner(sample_project, mode="structure", output_format="txt"))
    assert scan["error"] is None
    map_path = tmp_path / "live_map.txt"
    map_path.write_text(scan["finished"], encoding="utf-8")
    dest = tmp_path / "mw_restore"
    dest.mkdir()

    win = app_mod.MainWindow()
    try:
        win.selected_folder = dest
        win.selected_input_file = map_path
        win.update_reverse_enabled()
        assert win.reverse_btn.isEnabled() is True

        win.reverse_structure()
        assert win.reverse_thread is not None
        assert win.reverse_thread.wait(60000)
        qapp.processEvents()

        assert (dest / "src" / "main.py").is_file()
        assert win._busy is False
        assert win.output_text.toPlainText()
    finally:
        if win.reverse_thread and win.reverse_thread.isRunning():
            win.reverse_thread.requestInterruption()
            win.reverse_thread.wait(5000)
        win.close()


def test_live_mainwindow_rejects_second_scan(app_mod, qapp, sample_project, no_modal):
    win = app_mod.MainWindow()
    try:
        win.selected_folder = sample_project
        win.start_scanning()
        first = win.scan_thread
        win.start_scanning()
        assert win.scan_thread is first
        first.requestInterruption()
        first.wait(15000)
        qapp.processEvents()
    finally:
        if win.scan_thread and win.scan_thread.isRunning():
            win.scan_thread.requestInterruption()
            win.scan_thread.wait(5000)
        win.close()


def test_live_mainwindow_drop_uppercase_map_suffix(app_mod, qapp, tmp_path):
    win = app_mod.MainWindow()
    try:
        map_path = tmp_path / "MAP.JSON"
        map_path.write_text(
            json.dumps({"name": "r", "type": "directory", "children": []}),
            encoding="utf-8",
        )
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(map_path))])
        path = Path(mime.urls()[0].toLocalFile())
        assert path.suffix.lower() in {".txt", ".json"}
        win.selected_input_file = path
        win.update_reverse_enabled()
        assert win.reverse_btn.isEnabled() is False
        win.selected_folder = tmp_path / "dest"
        win.selected_folder.mkdir()
        win.update_reverse_enabled()
        assert win.reverse_btn.isEnabled() is True
    finally:
        win.close()


def test_live_mainwindow_close_during_scan(app_mod, qapp, sample_project, no_modal):
    win = app_mod.MainWindow()
    win.selected_folder = sample_project
    win.start_scanning()
    thread = win.scan_thread
    assert thread is not None and thread.isRunning()
    win.close()
    qapp.processEvents()
    assert not thread.isRunning()


def test_live_about_mentions_limits(app_mod, qapp):
    win = app_mod.MainWindow()
    try:
        dlg = app_mod.AboutDialog(win)
        texts = " ".join(label.text() for label in dlg.findChildren(QLabel))
        assert "۵۰" in texts
        assert "بازسازی" in texts or "ساختار" in texts
        dlg.close()
    finally:
        win.close()


def test_live_tree_expand_cap_constant(app_mod):
    assert app_mod.MAX_TREE_EXPAND_NODES == 2000
    assert app_mod.MAX_TOTAL_OUTPUT_BYTES == 50 * 1024 * 1024


def test_live_count_tree_nodes_matches_sample(app_mod, sample_project):
    tree = app_mod.build_tree_data(sample_project)
    n = app_mod.count_tree_nodes(tree)
    assert n >= 8

    def walk(node):
        yield node["name"]
        for c in node.get("children", []):
            yield from walk(c)

    names = set(walk(tree))
    assert "node_modules" not in names
    assert "core.py" in names


def test_live_encoding_cp1252_file_readable(app_mod, qapp, tmp_path):
    root = tmp_path / "enc"
    root.mkdir()
    (root / "legacy.txt").write_bytes("café résumé".encode("cp1252"))
    res = run_qthread(app_mod.FileScanner(root, mode="full", output_format="txt"))
    assert res["error"] is None, res["error"]
    # Decoded via cp1252/latin-1 path in read_file_content
    assert "caf" in res["finished"]


def test_live_sibling_tree_levels_match_generator(app_mod, sample_project):
    lines = app_mod.generate_tree_structure(sample_project)
    parsed = app_mod.parse_txt_structure("\n".join(lines))
    paths = {tuple(p) for p, is_dir in parsed if not is_dir}
    assert ("src", "pkg", "core.py") in paths
    assert ("src", "main.py") in paths
    assert ("docs", "README.md") in paths
    assert ("src", "pkg", "core.py", "main.py") not in paths


def test_live_chain_txt_to_json_consistency(app_mod, qapp, sample_project):
    """Same project: TXT reverse paths and JSON reverse paths must match file sets."""
    txt = run_qthread(app_mod.FileScanner(sample_project, mode="structure", output_format="txt"))
    js = run_qthread(app_mod.FileScanner(sample_project, mode="structure", output_format="json"))
    assert txt["error"] is None and js["error"] is None

    parsed = [tuple(p) for p, is_dir in app_mod.parse_txt_structure(txt["finished"]) if not is_dir]

    def collect_files(node, prefix=()):
        if node["type"] == "file":
            yield prefix + (node["name"],)
        else:
            for c in node.get("children", []):
                yield from collect_files(
                    c, prefix + ((node["name"],) if prefix or node is not None else ())
                )

    # JSON tree root name is folder name; children are relative to restore root
    data = json.loads(js["finished"])

    def files_from_json(node, prefix=()):
        if node["type"] == "file":
            yield prefix
        else:
            for c in node.get("children", []):
                yield from files_from_json(c, prefix + (c["name"],))

    json_files = set(files_from_json(data, ()))
    # TXT paths are relative (no root project name prefix)
    assert set(parsed) == json_files
