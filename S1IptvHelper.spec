# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for S1 IPTV Helper — onedir (folder) build, same
# approach as the sibling EchoAudioConverter.spec.
#
# Build with:
#   venv\Scripts\pyinstaller.exe S1IptvHelper.spec --clean
#
# Output lands in dist\S1IptvHelper\ — that whole folder is the
# distributable (S1IptvHelper.exe + a _internal\ folder of PyQt6/Python
# runtime files next to it). Zip the folder to hand it to someone.
#
# Personal data files (config.json, taxonomy.json, the log file, backups)
# are written next to S1IptvHelper.exe, not inside _internal\ -- see
# s1iptv/paths.py, which resolves this correctly for both a frozen build
# (via sys.executable) and running from source (via __file__).

a = Analysis(
    ['run_s1_iptv_helper.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('s1iptv/data/taxonomy.seed.json', 's1iptv/data'),
        ('s1iptv/assets/spin_up.png', 's1iptv/assets'),
        ('s1iptv/assets/spin_down.png', 's1iptv/assets'),
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
    [],
    exclude_binaries=True,
    name='S1IptvHelper',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='S1IptvHelper',
)
