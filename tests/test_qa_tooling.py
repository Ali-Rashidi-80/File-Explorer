"""Meta-QA: configs/scripts exist and bytecode compiles (honest, no lint mocks)."""

import compileall
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_qa_config_files_exist():
    assert (ROOT / "pyproject.toml").is_file()
    assert (ROOT / ".flake8").is_file()
    assert (ROOT / "requirements.txt").is_file()
    assert (ROOT / "requirements-dev.txt").is_file()
    assert (ROOT / "qa.bat").is_file()


def test_compileall_active_sources():
    ok = compileall.compile_file(str(ROOT / "file-explorer-pyside6.py"), quiet=1)
    assert ok is True
    ok_tests = compileall.compile_dir(str(ROOT / "tests"), quiet=1, force=True)
    assert ok_tests is True


def test_ruff_clean_on_active_tree():
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            str(ROOT / "file-explorer-pyside6.py"),
            str(ROOT / "tests"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_flake8_clean_on_active_tree():
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "flake8",
            str(ROOT / "file-explorer-pyside6.py"),
            str(ROOT / "tests"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_black_check_clean():
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "black",
            "--check",
            str(ROOT / "file-explorer-pyside6.py"),
            str(ROOT / "tests"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_isort_check_clean():
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "isort",
            "--check-only",
            str(ROOT / "file-explorer-pyside6.py"),
            str(ROOT / "tests"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_mypy_clean():
    proc = subprocess.run(
        [sys.executable, "-m", "mypy", str(ROOT / "file-explorer-pyside6.py"), str(ROOT / "tests")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_no_terminate_and_has_interruption_guards():
    src = (ROOT / "file-explorer-pyside6.py").read_text(encoding="utf-8")
    assert ".terminate(" not in src
    assert "requestInterruption" in src
    assert "isInterruptionRequested" in src
    assert "safe_join_under" in src


def test_pylint_errors_only_clean():
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pylint",
            "--errors-only",
            f"--rcfile={ROOT / '.pylintrc'}",
            str(ROOT / "file-explorer-pyside6.py"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_bandit_no_high_medium_issues():
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "bandit",
            "-q",
            "-ll",
            "-r",
            str(ROOT / "file-explorer-pyside6.py"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
