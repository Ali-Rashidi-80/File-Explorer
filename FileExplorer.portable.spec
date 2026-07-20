# -*- mode: python ; coding: utf-8 -*-
# File Explorer — Single portable EXE (onefile + optional UPX)
import os

block_cipher = None
ROOT = os.path.abspath(SPECPATH)

datas = []
icon_path = os.path.join(ROOT, "icon.ico")
if os.path.isfile(icon_path):
    datas.append((icon_path, "."))

a = Analysis(
    [os.path.join(ROOT, "file-explorer-pyside6.py")],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "numpy",
        "pandas",
        "scipy",
        "PyQt6",
        "PyQt5",
    ],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, cipher=block_cipher)

# Skip UPX on sensitive Qt/Python DLLs (same idea as MediaConverterPro)
UPX_SKIP = [
    "Qt6Core.dll",
    "Qt6Gui.dll",
    "Qt6Widgets.dll",
    "Qt6Network.dll",
    "python3.dll",
    "python311.dll",
    "python312.dll",
    "python313.dll",
    "python314.dll",
    "vcruntime140.dll",
    "vcruntime140_1.dll",
    "libcrypto",
    "libssl",
]

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="FileExplorer_Portable",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=UPX_SKIP,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path if os.path.isfile(icon_path) else None,
)
