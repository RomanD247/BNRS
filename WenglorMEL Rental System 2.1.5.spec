# -*- mode: python ; coding: utf-8 -*-
import os

a = Analysis(
    [os.path.join(SPECPATH, 'main.py')],
    pathex=[],
    binaries=[
        (os.path.join(SPECPATH, 'bnrs', 'Lib', 'site-packages', 'pylibdmtx', 'libdmtx-64.dll'), '.'),
    ],
    datas=[
        (os.path.join(SPECPATH, 'rental.db'), '.'),
        (os.path.join(SPECPATH, 'scanner_config.default.json'), '.'),
        (os.path.join(SPECPATH, 'bnrs', 'Lib', 'site-packages', 'nicegui'), 'nicegui/'),
        (os.path.join(SPECPATH, 'web_viewer'), 'web_viewer/'),
        (os.path.join(SPECPATH, 'assets'), 'assets/'),
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
    [],
    name='WenglorMEL Rental System 2.1.5',
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
    icon=[os.path.join(SPECPATH, 'assets', 'icon.ico')],
)
