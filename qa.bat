@echo off
setlocal
cd /d "%~dp0"
echo ===== pytest =====
python -m pytest tests -q
if errorlevel 1 exit /b 1

echo ===== ruff =====
python -m ruff check file-explorer-pyside6.py tests
if errorlevel 1 exit /b 1

echo ===== flake8 =====
python -m flake8 file-explorer-pyside6.py tests
if errorlevel 1 exit /b 1

echo ===== isort =====
python -m isort --check-only file-explorer-pyside6.py tests
if errorlevel 1 exit /b 1

echo ===== black =====
python -m black --check file-explorer-pyside6.py tests
if errorlevel 1 exit /b 1

echo ===== mypy =====
python -m mypy file-explorer-pyside6.py tests
if errorlevel 1 exit /b 1

echo ===== compileall =====
python -m compileall -q file-explorer-pyside6.py tests
if errorlevel 1 exit /b 1

echo ===== pylint (errors-only) =====
python -m pylint --errors-only --rcfile=.pylintrc file-explorer-pyside6.py
if errorlevel 1 exit /b 1

echo ===== bandit (medium+) =====
python -m bandit -q -ll -r file-explorer-pyside6.py
if errorlevel 1 exit /b 1

echo.
echo All QA checks passed.
exit /b 0
