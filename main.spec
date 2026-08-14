# -*- mode: python ; coding: utf-8 -*-

import sys
from PyInstaller.utils.hooks import collect_data_files

# Збираємо всі необхідні дані/ресурси для pymupdf
pymupdf_datas = collect_data_files('pymupdf')

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=pymupdf_datas,  # <--- Тепер змінна визначена
    hiddenimports=['pymupdf', 'pymupdf4llm'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Змініть на False, коли захочете приховати консоль
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)