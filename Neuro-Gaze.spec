# -*- mode: python ; coding: utf-8 -*-
"""
Neuro-Gaze.spec
-----------------
PyInstaller build specification for Neuro-Gaze.

Usage:
    pyinstaller Neuro-Gaze.spec

Output:
    dist/Neuro-Gaze/Neuro-Gaze.exe   (one-folder build)

Notes:
  - Uses one-folder mode for reliability (faster cold-start vs one-file)
  - MediaPipe model is bundled as a data file
  - PySide6 Qt plugins are collected automatically via collect_all()
"""

import sys
from PyInstaller.utils.hooks import collect_all, collect_data_files

# ── Collect PySide6 + MediaPipe data/binaries ─────────────────
pyside6_datas, pyside6_binaries, pyside6_hiddenimports = collect_all("PySide6")
mp_datas, mp_binaries, mp_hiddenimports = collect_all("mediapipe")

block_cipher = None

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=pyside6_binaries + mp_binaries,
    datas=[
        # MediaPipe model
        ("models/face_landmarker.task", "models"),
        # Assets
        ("assets", "assets"),
        # PySide6 & MediaPipe data
        *pyside6_datas,
        *mp_datas,
    ],
    hiddenimports=[
        "pyttsx3",
        "pyttsx3.drivers",
        "pyttsx3.drivers.sapi5",
        "pyautogui",
        "cv2",
        "numpy",
        *pyside6_hiddenimports,
        *mp_hiddenimports,
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "scipy",
        "pandas",
        "jupyter",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Neuro-Gaze",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,                   # No console window
    icon="assets/app_icon.ico" if sys.platform == "win32" else None,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Neuro-Gaze",
)
