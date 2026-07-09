# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

SCRIPT_DIR = Path("D:/Code/wxauto_git/win")

block_cipher = None

added_files = [
    (str(SCRIPT_DIR / "runtime_paths.py"), "."),
    (str(SCRIPT_DIR / "capture_chat.py"), "."),
    (str(SCRIPT_DIR / "scrape_history.py"), "."),
    (str(SCRIPT_DIR / "stitch.py"), "."),
]

hiddenimports = [
    "PIL",
    "PIL.Image",
    "PIL.ImageGrab",
    "PIL.ImageTk",
    "uiautomation",
    "winrt",
    "winrt.windows.media.ocr",
    "winrt.windows.graphics.imaging",
    "winrt.windows.globalization",
]

a = Analysis(
    [str(SCRIPT_DIR / "gui.py")],
    pathex=[str(SCRIPT_DIR)],
    binaries=[],
    datas=added_files,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="微信聊天截图工具",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(SCRIPT_DIR.parent / "icon.ico"),
)
