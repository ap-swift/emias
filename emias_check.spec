# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec для EMIAS Check (GUI)."""

import os

block_cipher = None
ROOT = os.path.abspath(os.path.dirname(SPECPATH))

a = Analysis(
    [os.path.join(ROOT, 'run_gui.pyw')],
    pathex=[ROOT],
    binaries=[],
    datas=[
        (os.path.join(ROOT, 'emias_check', 'templates', 'report.html'),
         os.path.join('emias_check', 'templates')),
    ],
    hiddenimports=[
        'emias_check',
        'emias_check.rules.order530n',
        'emias_check.rules.clinical',
    ],
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
    name='emias_check',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=None,
)
