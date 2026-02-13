# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_all

block_cipher = None
ost_root = os.path.abspath(os.getcwd())

# SETTINGS
sys.path.append(ost_root)
from core.settings import APP_NAME, ICON, COMMAND_ICON


# COLLECTION 
# We rely on collect_all
mp_datas, mp_binaries, mp_hidden = collect_all('mediapipe')
rs_datas, rs_binaries, rs_hidden = collect_all('pyrealsense2')
cv_datas, cv_binaries, cv_hidden = collect_all('cv2')

# Merge Data
final_datas = [('assets', 'assets')] + mp_datas + rs_datas + cv_datas
# Merge Hidden Imports
final_hidden = mp_hidden + rs_hidden + cv_hidden + ['sensors.realsense', 'core.io', 'core.pose', 'core.transforms', 'core.settings']

# BUILD DEFINITIONS

# RECORDER
a_rec = Analysis(
    ['tools/record.py'],
    pathex=[ost_root],
    datas=final_datas,
    hiddenimports=final_hidden,
    runtime_hooks=['core/hook_fix.py'],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz_rec = PYZ(a_rec.pure, a_rec.zipped_data, cipher=block_cipher)
splash_rec = Splash('assets/splash.png', binaries=a_rec.binaries, datas=a_rec.datas, text_size=12, minify_script=True, always_on_top=True)

exe_rec = EXE(
    pyz_rec,
    a_rec.scripts,
    splash_rec,
    splash_rec.binaries,
    [],
    exclude_binaries=True,
    name='record',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=COMMAND_ICON,
    manifest='core/app.manifest',
    contents_directory='libs'
)

# STUDIO
a_stu = Analysis(
    ['tools/studio.py'], 
    pathex=[ost_root],
    datas=final_datas,
    hiddenimports=final_hidden + ['core.data', 'core.metrics', 'core.processing'],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz_stu = PYZ(a_stu.pure, a_stu.zipped_data, cipher=block_cipher)
splash_stu = Splash('assets/splash.png', binaries=a_stu.binaries, datas=a_stu.datas, text_size=12, minify_script=True, always_on_top=True)

exe_stu = EXE(
    pyz_stu,
    a_stu.scripts,
    splash_stu,
    splash_stu.binaries,
    [],
    exclude_binaries=True,
    name='studio',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=COMMAND_ICON,
    manifest='core/app.manifest',
    contents_directory='libs'
)

# LAUNCHER
a_main = Analysis(
    ['main.py'],
    pathex=[ost_root],
    binaries=[],
    datas=[('assets', 'assets')],
    hiddenimports=['core.paths', 'core.settings'],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz_main = PYZ(a_main.pure, a_main.zipped_data, cipher=block_cipher)

exe_main = EXE(
    pyz_main,
    a_main.scripts,
    [],
    exclude_binaries=True,
    name='Launcher',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=ICON,
    manifest='core/app.manifest',
    contents_directory='libs'
)

# MERGE & ORGANIZE
coll = COLLECT(
    exe_main,
    a_main.binaries,
    a_main.zipfiles,
    a_main.datas,
    
    exe_rec,
    a_rec.binaries,
    a_rec.zipfiles,
    a_rec.datas,
    
    exe_stu,
    a_stu.binaries,
    a_stu.zipfiles,
    a_stu.datas,
    
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME,
    contents_directory='libs'
)