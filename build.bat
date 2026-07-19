@echo off
color 0B
echo.
echo [1/3] Checking dependencies...
python -m pip install --upgrade pip
python -m pip install pyside6 pyinstaller

echo.
echo [2/3] Starting PyInstaller Build Process...
set "UPX_DIR=C:\Program Files\upx-5.0.2-win64"
set "COMMON=--noconfirm --onefile --windowed --name FileExplorer --icon=icon.ico --clean --exclude-module tkinter --exclude-module matplotlib --exclude-module numpy --exclude-module pandas --exclude-module scipy --exclude-module PyQt6 --exclude-module PyQt5"

if exist "%UPX_DIR%\upx.exe" (
  echo UPX found — compression enabled.
  python -m PyInstaller %COMMON% --upx-dir "%UPX_DIR%" file-explorer-pyside6.py
) else (
  echo UPX not found — building without UPX.
  python -m PyInstaller %COMMON% file-explorer-pyside6.py
)

echo.
echo [3/3] Build Process Finished!
pause
