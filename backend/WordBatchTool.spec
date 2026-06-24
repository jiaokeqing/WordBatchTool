# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

frontend_dist = Path("..") / "frontend" / "dist"

a = Analysis(
    ["launcher.py"],
    pathex=[],
    binaries=[],
    datas=[(str(frontend_dist), "frontend")],
    hiddenimports=[
        "multipart",
        "python_multipart",
        "webview",
        "webview.platforms.winforms",
        "webview.platforms.edgechromium",
    ],
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
    name="WordBatchTool",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
