# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_dynamic_libs, collect_data_files

hiddenimports = [
    'parsers.python',
    'parsers.javascript',
    'parsers.typescript',
    'tree_sitter',
    'tree_sitter_python',
    'tree_sitter_javascript',
    'tree_sitter_typescript',
]

binaries = []
binaries += collect_dynamic_libs('tree_sitter')
binaries += collect_dynamic_libs('tree_sitter_python')
binaries += collect_dynamic_libs('tree_sitter_javascript')
binaries += collect_dynamic_libs('tree_sitter_typescript')

datas = []
# Ensure tree-sitter language packages' query data is packaged just in case
datas += collect_data_files('tree_sitter_python')
datas += collect_data_files('tree_sitter_javascript')
datas += collect_data_files('tree_sitter_typescript')

a = Analysis(
    ['docswarm_entry.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='docswarm',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
