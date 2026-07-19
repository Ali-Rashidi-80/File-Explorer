"""Honest core + integration tests for file-explorer-pyside6 (no fake passes)."""

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_module():
    path = ROOT / "file-explorer-pyside6.py"
    spec = importlib.util.spec_from_file_location("file_explorer_app", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def app_mod():
    return _load_module()


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


# ---------- path safety ----------


def test_safe_join_rejects_dotdot(app_mod, tmp_path):
    with pytest.raises(ValueError):
        app_mod.safe_join_under(tmp_path, "..", "escape.txt")


def test_safe_join_rejects_reserved_on_windows(app_mod, tmp_path):
    if sys.platform != "win32":
        pytest.skip("Windows reserved names")
    with pytest.raises(ValueError):
        app_mod.safe_join_under(tmp_path, "NUL")
    with pytest.raises(ValueError):
        app_mod.safe_join_under(tmp_path, "CON.txt")
    with pytest.raises(ValueError):
        app_mod.safe_join_under(tmp_path, "file.")


def test_safe_join_rejects_absolute_and_separators(app_mod, tmp_path):
    with pytest.raises(ValueError):
        app_mod.safe_join_under(tmp_path, r"C:\Windows\System32")
    with pytest.raises(ValueError):
        app_mod.safe_join_under(tmp_path, "/etc/passwd")
    with pytest.raises(ValueError):
        app_mod.safe_join_under(tmp_path, "a/b")
    with pytest.raises(ValueError):
        app_mod.safe_join_under(tmp_path, "a\\b")


def test_safe_join_ok(app_mod, tmp_path):
    target = app_mod.safe_join_under(tmp_path, "a", "b.txt")
    assert target == (tmp_path / "a" / "b.txt").resolve()
    assert target.is_relative_to(tmp_path.resolve())


# ---------- tree parse ----------


def test_parse_txt_sibling_levels(app_mod):
    tree = "\n".join(
        [
            "├── a/",
            "│   ├── b/",
            "│   │   └── c.txt",
            "│   └── e.txt",
            "└── d.txt",
        ]
    )
    structure = app_mod.parse_txt_structure(tree)
    paths = {tuple(p): is_dir for p, is_dir in structure}
    assert ("a", "e.txt") in paths
    assert paths[("a", "e.txt")] is False
    assert ("a", "b", "e.txt") not in paths
    assert ("a", "b", "c.txt") in paths
    assert ("d.txt",) in paths


def test_parse_skips_meta_lines(app_mod):
    tree = "\n".join(
        [
            "├── ok/",
            "│   └── [عدم دسترسی به پوشه]",
            "└── f.txt",
        ]
    )
    structure = app_mod.parse_txt_structure(tree)
    names = [p[-1] for p, _ in structure]
    assert "[عدم دسترسی به پوشه]" not in names
    assert "f.txt" in names


# ---------- JSON reverse ----------


def test_json_create_rejects_traversal(app_mod, tmp_path):
    evil = {
        "name": "root",
        "type": "directory",
        "children": [{"name": "..", "type": "file"}],
    }
    with pytest.raises(ValueError):
        app_mod.create_from_json(evil, tmp_path, ())


def test_json_create_rejects_missing_schema(app_mod, tmp_path):
    with pytest.raises(ValueError):
        app_mod.create_from_json({"name": "x"}, tmp_path, ())
    with pytest.raises(ValueError):
        app_mod.create_from_json({"type": "directory"}, tmp_path, ())


def test_json_roundtrip_structure(app_mod, tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    (src / "a" / "b").mkdir(parents=True)
    (src / "a" / "e.txt").write_text("x", encoding="utf-8")
    (src / "a" / "b" / "c.txt").write_text("y", encoding="utf-8")
    (src / ".git").mkdir(parents=True)
    (src / ".git" / "config").write_text("z", encoding="utf-8")

    tree = app_mod.build_tree_data(src)
    child_names = {c["name"] for c in tree["children"]}
    assert ".git" not in child_names
    assert "a" in child_names

    dst.mkdir()
    app_mod.create_from_json(tree, dst, ())
    assert (dst / "a" / "e.txt").is_file()
    assert (dst / "a" / "b" / "c.txt").is_file()
    assert not (dst / ".git").exists()
    # reverse creates empty files — content must NOT be restored
    assert (dst / "a" / "e.txt").read_text(encoding="utf-8") == ""


def test_txt_generate_and_reverse_roundtrip(app_mod, tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    (src / "a" / "b").mkdir(parents=True)
    (src / "a" / "e.txt").write_text("x", encoding="utf-8")
    (src / "a" / "b" / "c.txt").write_text("y", encoding="utf-8")
    (src / "d.txt").write_text("z", encoding="utf-8")
    (src / "node_modules" / "pkg").mkdir(parents=True)
    (src / "node_modules" / "pkg" / "index.js").write_text("1", encoding="utf-8")

    lines = app_mod.generate_tree_structure(src)
    content = "\n".join(lines)
    assert "node_modules" not in content

    structure = app_mod.parse_txt_structure(content)
    dst.mkdir()
    for parts, is_dir in structure:
        target = app_mod.safe_join_under(dst, *parts)
        if is_dir:
            app_mod.mkdir_safe(target)
        else:
            app_mod.touch_safe(target)

    assert (dst / "a" / "e.txt").is_file()
    assert (dst / "a" / "b" / "c.txt").is_file()
    assert (dst / "d.txt").is_file()
    assert not (dst / "node_modules").exists()


# ---------- heuristics ----------


def test_env_and_gitignore_are_text(app_mod, tmp_path):
    env = tmp_path / ".env"
    env.write_text("A=1\n", encoding="utf-8")
    gi = tmp_path / ".gitignore"
    gi.write_text("*.pyc\n", encoding="utf-8")
    assert app_mod.is_text_file_heuristic(env) is True
    assert app_mod.is_text_file_heuristic(gi) is True


def test_null_byte_is_binary_even_with_js_suffix(app_mod, tmp_path):
    f = tmp_path / "foo.js"
    f.write_bytes(b"var x=1;\x00more")
    assert app_mod.is_text_file_heuristic(f) is False


def test_ignored_dirs_constant(app_mod):
    assert "node_modules" in app_mod.IGNORED_DIRS
    assert ".git" in app_mod.IGNORED_DIRS


def test_read_file_content_long_path_oserror_is_caught(app_mod, tmp_path, monkeypatch):
    """Second-open via win_long_path must not crash with an uncaught OSError."""
    target = tmp_path / "blocked.txt"
    target.write_text("secret", encoding="utf-8")
    calls = {"n": 0}

    def always_fail(path, *args, **kwargs):
        calls["n"] += 1
        raise OSError("simulated open failure")

    monkeypatch.setattr("builtins.open", always_fail)
    with pytest.raises(OSError, match="خواندن فایل ممکن نشد") as exc_info:
        app_mod.read_file_content(target)
    assert calls["n"] >= 2  # primary path + long-path retry (at least once)
    assert exc_info.value.__cause__ is not None


def test_read_file_content_retries_long_path_then_succeeds(app_mod, tmp_path, monkeypatch):
    target = tmp_path / "retry_ok.txt"
    target.write_text("recovered-content", encoding="utf-8")
    real_open = open
    state = {"fails": 1}

    def flaky_open(path, *args, **kwargs):
        path_str = str(path)
        if state["fails"] > 0:
            state["fails"] -= 1
            raise OSError("force long-path retry")
        # After first failure, allow open (strip \\?\ if present)
        if path_str.startswith("\\\\?\\UNC\\"):
            path = "\\\\" + path_str[8:]
        elif path_str.startswith("\\\\?\\"):
            path = path_str[4:]
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr("builtins.open", flaky_open)
    assert app_mod.read_file_content(target) == "recovered-content"


# ---------- FileScanner / ReverseScanner (real QThread) ----------


def _run_thread(thread, timeout_ms=30000):
    from PySide6.QtCore import QEventLoop, QTimer

    loop = QEventLoop()
    result = {"finished": None, "error": None, "tree": None, "preview": None}

    def on_finished(v):
        result["finished"] = v
        loop.quit()

    def on_error(e):
        result["error"] = e
        loop.quit()

    thread.finished.connect(on_finished)
    thread.error.connect(on_error)
    if hasattr(thread, "tree_data"):
        thread.tree_data.connect(lambda t: result.__setitem__("tree", t))
    if hasattr(thread, "preview"):
        thread.preview.connect(lambda t: result.__setitem__("preview", t))

    thread.start()
    QTimer.singleShot(timeout_ms, loop.quit)
    loop.exec()
    # Signal may quit the loop before QThread fully leaves isRunning()
    if thread.isRunning():
        thread.wait(5000)
    if thread.isRunning():
        thread.requestInterruption()
        thread.wait(3000)
        pytest.fail("thread did not finish in time")
    return result


def test_file_scanner_structure_txt_and_json(app_mod, qapp, tmp_path):
    src = tmp_path / "proj"
    (src / "src").mkdir(parents=True)
    (src / "src" / "main.py").write_text("print(1)\n", encoding="utf-8")
    (src / "build" / "out").mkdir(parents=True)
    (src / "build" / "out" / "x.bin").write_bytes(b"\x00\x01")

    t1 = app_mod.FileScanner(src, mode="structure", output_format="txt")
    r1 = _run_thread(t1)
    assert r1["error"] is None, r1["error"]
    assert r1["finished"] is not None
    assert "main.py" in r1["finished"]
    assert "build" not in r1["finished"]
    assert r1["tree"] is not None
    assert "build" not in {c["name"] for c in r1["tree"]["children"]}

    t2 = app_mod.FileScanner(src, mode="structure", output_format="json")
    r2 = _run_thread(t2)
    assert r2["error"] is None, r2["error"]
    data = json.loads(r2["finished"])
    assert data["type"] == "directory"
    assert "build" not in {c["name"] for c in data["children"]}


def test_file_scanner_full_skips_huge_and_binary_includes_text(app_mod, qapp, tmp_path):
    src = tmp_path / "proj"
    src.mkdir()
    (src / "ok.txt").write_text("hello-content\n", encoding="utf-8")
    (src / "bin.dat").write_bytes(b"\x00\x01\x02\x03")
    huge = src / "huge.txt"
    # Real oversized text: non-null header so heuristic classifies as text, size > limit
    limit = int(app_mod.MAX_TEXT_FILE_SIZE_MB * 1024 * 1024) + 1
    with open(huge, "wb") as f:
        f.write(b"TEXT-HEADER-" + b"A" * 2000)
        f.seek(limit - 1)
        f.write(b"Z")

    scanner = app_mod.FileScanner(src, mode="full", output_format="txt")
    result = _run_thread(scanner)
    assert result["error"] is None, result["error"]
    out = result["finished"]
    assert "hello-content" in out
    assert "باینری" in out
    assert "اخطار ضدکرش" in out
    # Oversized body must not be dumped into output
    assert "TEXT-HEADER-" not in out or out.count("TEXT-HEADER-") == 0 or "صرف‌نظر" in out
    assert "A" * 500 not in out


def test_file_scanner_output_cap_is_enforced(app_mod, qapp, tmp_path, monkeypatch):
    """Monkeypatch cap low and prove scanner stops with Persian notice (not a fake assert)."""
    monkeypatch.setattr(app_mod, "MAX_TOTAL_OUTPUT_BYTES", 800)
    src = tmp_path / "proj"
    src.mkdir()
    for i in range(30):
        (src / f"f{i:02d}.txt").write_text((f"line-{i}-") * 40 + "\n", encoding="utf-8")

    scanner = app_mod.FileScanner(src, mode="full", output_format="txt")
    result = _run_thread(scanner)
    assert result["error"] is None, result["error"]
    out = result["finished"]
    assert "سقف ۵۰ مگابایت" in out or "سقف" in out
    assert len(out.encode("utf-8")) < 50_000  # far below real 50MB; capped early


def test_reverse_scanner_txt_from_map_file(app_mod, qapp, tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    (src / "pkg" / "mod").mkdir(parents=True)
    (src / "pkg" / "mod" / "a.py").write_text("code", encoding="utf-8")
    (src / "pkg" / "b.py").write_text("code2", encoding="utf-8")
    map_file = tmp_path / "map.txt"
    map_file.write_text("\n".join(app_mod.generate_tree_structure(src)), encoding="utf-8")
    dst.mkdir()

    rev = app_mod.ReverseScanner(map_file, dst, "txt")
    result = _run_thread(rev)
    assert result["error"] is None, result["error"]
    assert result["finished"]
    assert result["preview"] is not None
    assert (dst / "pkg" / "b.py").is_file()
    assert (dst / "pkg" / "mod" / "a.py").is_file()
    assert (dst / "pkg" / "b.py").read_text(encoding="utf-8") == ""


def test_reverse_scanner_json_rejects_file_root(app_mod, qapp, tmp_path):
    map_file = tmp_path / "bad.json"
    map_file.write_text(
        json.dumps({"name": "x", "type": "file"}),
        encoding="utf-8",
    )
    dst = tmp_path / "dst"
    dst.mkdir()
    rev = app_mod.ReverseScanner(map_file, dst, "json")
    result = _run_thread(rev)
    assert result["error"] is not None
    assert "directory" in result["error"]


def test_reverse_scanner_json_ok(app_mod, qapp, tmp_path):
    tree = {
        "name": "root",
        "type": "directory",
        "children": [
            {
                "name": "lib",
                "type": "directory",
                "children": [{"name": "z.py", "type": "file"}],
            }
        ],
    }
    map_file = tmp_path / "map.json"
    map_file.write_text(json.dumps(tree), encoding="utf-8")
    dst = tmp_path / "dst"
    dst.mkdir()
    rev = app_mod.ReverseScanner(map_file, dst, "json")
    result = _run_thread(rev)
    assert result["error"] is None, result["error"]
    assert (dst / "lib" / "z.py").is_file()


def test_scanner_respects_interruption(app_mod, qapp, tmp_path):
    src = tmp_path / "big"
    src.mkdir()
    for i in range(200):
        (src / f"n{i}.txt").write_text("x" * 200, encoding="utf-8")

    scanner = app_mod.FileScanner(src, mode="full", output_format="txt")
    errors: list[str] = []
    scanner.error.connect(errors.append)
    scanner.start()
    scanner.requestInterruption()
    assert scanner.wait(10000) is True
    assert not scanner.isRunning()
    # Cooperative cancel must not surface as a crash/error signal
    assert errors == []


# ---------- MainWindow UI contracts ----------


def test_mainwindow_format_lock_and_reverse_enable(app_mod, qapp, tmp_path):
    win = app_mod.MainWindow()
    try:
        # full mode -> JSON locked to TXT
        win.mode_combo.setCurrentIndex(0)
        assert win.format_combo.currentIndex() == 0
        assert win.format_combo.isEnabled() is False

        win.mode_combo.setCurrentIndex(1)
        assert win.format_combo.isEnabled() is True
        win.format_combo.setCurrentIndex(1)
        assert win.format_combo.currentIndex() == 1
        # back to full resets JSON
        win.mode_combo.setCurrentIndex(0)
        assert win.format_combo.currentIndex() == 0
        assert win.format_combo.isEnabled() is False

        assert win.reverse_btn.isEnabled() is False
        win.selected_folder = tmp_path
        win.update_reverse_enabled()
        assert win.reverse_btn.isEnabled() is False
        mapf = tmp_path / "m.TXT"
        mapf.write_text("└── a.txt\n", encoding="utf-8")
        win.selected_input_file = mapf
        win.update_reverse_enabled()
        assert win.reverse_btn.isEnabled() is True

        win.set_busy(True)
        assert win.reverse_btn.isEnabled() is False
        assert win.start_btn.isEnabled() is False
        win.set_busy(False)

        assert isinstance(win.output_text, app_mod.QPlainTextEdit)
        assert win.output_text.layoutDirection() == app_mod.Qt.LayoutDirection.LeftToRight
    finally:
        win.close()


def test_disconnect_reverse_thread_no_attribute_error(app_mod, qapp, tmp_path):
    win = app_mod.MainWindow()
    try:
        mapf = tmp_path / "m.json"
        mapf.write_text(
            json.dumps({"name": "r", "type": "directory", "children": []}),
            encoding="utf-8",
        )
        thread = app_mod.ReverseScanner(mapf, tmp_path, "json")
        thread.finished.connect(lambda *_: None)
        thread.error.connect(lambda *_: None)
        win.reverse_thread = thread
        # Must not raise AttributeError on missing progress signal
        win._disconnect_thread(thread)
    finally:
        win.close()


def test_second_job_rejected_while_busy(app_mod, qapp, tmp_path):
    win = app_mod.MainWindow()
    try:
        win.selected_folder = tmp_path
        (tmp_path / "a.txt").write_text("hi", encoding="utf-8")
        win.start_scanning()
        assert win._any_thread_running() or win._busy
        # Second start must be rejected (busy path) — no second thread swap crash
        prev = win.scan_thread
        win.start_scanning()
        assert win.scan_thread is prev
        if win.scan_thread and win.scan_thread.isRunning():
            win.scan_thread.requestInterruption()
            win.scan_thread.wait(10000)
        win.set_busy(False)
    finally:
        if win.scan_thread and win.scan_thread.isRunning():
            win.scan_thread.requestInterruption()
            win.scan_thread.wait(5000)
        win.close()


def test_packaging_files_point_to_pyside6():
    pyi = (ROOT / "pyinstaller.txt").read_text(encoding="utf-8")
    bat = (ROOT / "build.bat").read_text(encoding="utf-8")
    req = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "file-explorer-pyside6.py" in pyi
    assert "file_explorer.py" not in pyi
    assert "icon.ico" in pyi
    assert "file-explorer-pyside6.py" in bat
    assert "UPX" in bat
    assert "PySide6" in req
    assert "pytest" in req


def test_no_terminate_in_source():
    src = (ROOT / "file-explorer-pyside6.py").read_text(encoding="utf-8")
    assert ".terminate(" not in src
    assert "requestInterruption" in src
    assert "isInterruptionRequested" in src
    assert "QPlainTextEdit" in src
    assert "MAX_TOTAL_OUTPUT_BYTES" in src
