@echo off
color 0B
echo.
echo [1/3] Checking dependencies...
:: Ensure pip, PySide6, and PyInstaller are installed and available
python -m pip install --upgrade pip
python -m pip install pyside6 pyinstaller

echo.
echo [2/3] Starting PyInstaller Build Process...
:: Using 'python -m PyInstaller' is more robust than calling 'pyinstaller' directly
:: Note: --icon="icon.ico" adds the icon to the actual .exe file properties
python -m PyInstaller --noconfirm --onefile --windowed --name "FileExplorer" --icon="icon.ico" --clean --exclude-module tkinter --exclude-module matplotlib --exclude-module numpy --exclude-module pandas --exclude-module scipy --exclude-module PyQt6 --exclude-module PyQt5 --upx-dir "C:\Program Files\upx-5.0.2-win64" file-explorer-pyside6.py

echo.
echo [3/3] Build Process Finished!
pause