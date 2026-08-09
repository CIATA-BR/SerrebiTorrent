# -*- mode: python ; coding: utf-8 -*-
import os
import importlib.util
import sys
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

if importlib.util.find_spec('libtorrent') is None:
    raise RuntimeError(
        'libtorrent is required for SerrebiTorrent releases. Import the '
        'module successfully before building.'
    )

required_native_files = [
    'libcrypto-3-x64.dll',
    'libssl-3-x64.dll',
    'libcrypto-1_1-x64.dll',
    'libssl-1_1-x64.dll',
    'libcrypto-1_1.dll',
    'libssl-1_1.dll',
]
missing_native_files = [name for name in required_native_files if not os.path.isfile(name)]
if missing_native_files:
    raise RuntimeError(
        'Required libtorrent/OpenSSL files are missing: '
        + ', '.join(missing_native_files)
    )

# Base hidden imports
hiddenimports = [
    'libtorrent',
    'flask',
    'requests',
    'bs4',
    'yaml',
    'qbittorrentapi',
    'transmission_rpc',
    'werkzeug',
    'jinja2',
    'click',
    'itsdangerous',
    'wx.adv',
    'wx.html',
    'xmlrpc.client',
    'winreg',
    'base64',
]

# Meticulously collect all submodules for main dependencies
hiddenimports += collect_submodules('flask')
hiddenimports += collect_submodules('requests')
hiddenimports += collect_submodules('qbittorrentapi')
hiddenimports += collect_submodules('transmission_rpc')
hiddenimports += collect_submodules('bs4')
hiddenimports += collect_submodules('yaml')
hiddenimports += collect_submodules('werkzeug')
hiddenimports += collect_submodules('jinja2')
hiddenimports += collect_submodules(
    'urllib3',
    filter=lambda name: not (
        name.startswith('urllib3.contrib.emscripten')
        or name.startswith('urllib3.http2.connection')
    ),
)
hiddenimports += collect_submodules('chardet', filter=lambda name: not name.startswith('chardet.pipeline'))
hiddenimports += collect_submodules('idna')
hiddenimports += collect_submodules('certifi')

# Project submodules
local_modules = [
    'app_paths',
    'app_version',
    'clients',
    'config_manager',
    'libtorrent_env',
    'rss_manager',
    'search_dialog',
    'session_manager',
    'torrent_creator',
    'torrent_parsing',
    'torrent_search',
    'updater',
    'web_server',
]
hiddenimports += local_modules

datas = [(os.path.abspath('web_static'), 'web_static'), (os.path.abspath('update_helper.bat'), '.')]
if os.path.exists('icon.ico'):
    datas.append((os.path.abspath('icon.ico'), '.'))
datas += collect_data_files('flask')

a = Analysis(
    ['main.py'],
    pathex=[os.path.abspath('.')],
    binaries=[(name, '.') for name in required_native_files],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[os.path.abspath('hooks')],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'urllib3.contrib.emscripten',
        'urllib3.contrib.emscripten.fetch',
        'urllib3.http2.connection',
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
    strip=False,
    upx=False,
    upx_exclude=[],
    name='SerrebiTorrent',
)
