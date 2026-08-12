# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['src/cli/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('.venv/lib/python3.12/site-packages/pymupdf/layout/resources', 'pymupdf/layout/resources'),
        ('.venv/lib/python3.12/site-packages/pymupdf4llm/ocr/ocr_decision_model.onnx', 'pymupdf4llm/ocr/'),
    ],
    hiddenimports=[],
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
    name='books_to_markdown',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[],
    exclude_binaries=False,
)