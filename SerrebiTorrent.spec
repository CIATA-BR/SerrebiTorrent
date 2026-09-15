# -*- mode: python ; coding: utf-8 -*-
import importlib
import importlib.util
import os
import sys

block_cipher = None

libtorrent_spec = importlib.util.find_spec('libtorrent')
if libtorrent_spec is None or not libtorrent_spec.origin:
    raise RuntimeError(
        'libtorrent is required for SerrebiTorrent releases. Import the '
        'module successfully before building.'
    )

libtorrent = importlib.import_module('libtorrent')
libtorrent_version = getattr(libtorrent, '__version__', None)
if not libtorrent_version:
    raise RuntimeError('The installed libtorrent module has no version information.')
print(f'Packaging libtorrent {libtorrent_version} from {libtorrent_spec.origin}')

datas = [(os.path.abspath('web_static'), 'web_static')]
if os.path.isdir('locales'):
    datas.append((os.path.abspath('locales'), 'locales'))
if sys.platform == 'win32':
    datas.append((os.path.abspath('update_helper.bat'), '.'))
if os.path.exists('icon.ico'):
    datas.append((os.path.abspath('icon.ico'), '.'))

# Adding the extension explicitly makes a missing libtorrent binding a hard
# packaging failure. PyInstaller follows its native dependencies and includes
# only the DLLs/shared libraries referenced by the selected wheel.
binaries = [(os.path.abspath(libtorrent_spec.origin), '.')]

a = Analysis(
    ['app_entry.py'],
    pathex=[os.path.abspath('.')],
    binaries=binaries,
    datas=datas,
    hiddenimports=['libtorrent'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'pip',
        'setuptools',
        'urllib3.contrib.emscripten',
        'urllib3.contrib.emscripten.fetch',
        'urllib3.http2.connection',
        'wheel',
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
    name='SerrebiTorrent',
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
    icon=['icon.ico'] if os.path.exists('icon.ico') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=sys.platform.startswith('linux'),
    upx=False,
    upx_exclude=[],
    name='SerrebiTorrent',
)

if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='SerrebiTorrent.app',
        icon='icon.icns' if os.path.exists('icon.icns') else None,
        bundle_identifier='com.serrebidev.serrebitorrent',
    )
