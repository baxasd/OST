# -*- mode: python ; coding: utf-8 -*-
import sys
import os
import mediapipe  # <--- Import this to find the path
from PyInstaller.utils.hooks import collect_all

block_cipher = None
ost_root = os.path.abspath(os.getcwd())

# --- 1. SETTINGS ---
sys.path.append(ost_root)
from core.settings import APP_NAME, ICON

# --- 2. CONFLICT RESOLUTION ---
def deduplicate_binaries(bin_list):
    seen = set()
    unique = []
    for src, dest in bin_list:
        file_name = os.path.basename(src).lower()
        if file_name in seen:
            continue
        seen.add(file_name)
        unique.append((src, dest))
    return unique

# --- 3. COLLECT DEPENDENCIES (BRUTE FORCE METHOD) ---
extra_datas = [('assets', 'assets')]

# Find actual MediaPipe path on disk
mp_path = os.path.dirname(mediapipe.__file__)

# FORCE COPY: Map local 'site-packages/mediapipe' -> frozen 'mediapipe'
# This ensures 'mediapipe.python' exists because we are copying the files manually.
extra_datas.append((mp_path, 'mediapipe'))

# Collect Binaries (DLLs)
mp_datas_auto, mp_binaries, mp_hidden = collect_all('mediapipe')
rs_datas, rs_binaries, rs_hidden = collect_all('pyrealsense2')
cv_datas, cv_binaries, cv_hidden = collect_all('cv2')

# --- 4. MERGE & FILTER ---
# Merge binaries (MP first to win conflicts)
raw_binaries = mp_binaries + rs_binaries + cv_binaries
final_binaries = deduplicate_binaries(raw_binaries)

# Merge Datas (Our manual copy + others)
final_datas = extra_datas + rs_datas + cv_datas 
# Note: We excluded mp_datas_auto because we are manually copying the whole folder

final_hidden = rs_hidden + cv_hidden + [
    'sensors.realsense', 'core.io', 'core.pose', 'core.transforms', 'core.settings',
    # Critical imports
    'mediapipe', 
    'mediapipe.python',
    'mediapipe.python.solution_base',
    'mediapipe.python.solutions',
    'google.protobuf'
]

# =========================================================
# BUILD: RECORDER
# =========================================================
a_rec = Analysis(
    ['tools/record.py'],
    pathex=[ost_root],
    binaries=final_binaries,
    datas=final_datas,
    hiddenimports=final_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz_rec = PYZ(a_rec.pure, a_rec.zipped_data, cipher=block_cipher)

splash_rec = Splash(
    'assets/splash.png',
    binaries=a_rec.binaries,
    datas=a_rec.datas,
    text_pos=None,
    text_size=12,
    minify_script=True,
    always_on_top=True,
)

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
    icon=ICON,
    contents_directory='libs' 
)

# =========================================================
# BUILD: STUDIO
# =========================================================
a_stu = Analysis(
    ['tools/studio.py'], 
    pathex=[ost_root],
    binaries=final_binaries,
    datas=final_datas,
    hiddenimports=final_hidden + ['core.data', 'core.metrics', 'core.processing'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz_stu = PYZ(a_stu.pure, a_stu.zipped_data, cipher=block_cipher)

splash_stu = Splash(
    'assets/splash.png',
    binaries=a_stu.binaries,
    datas=a_stu.datas,
    text_pos=None,
    text_size=12,
    minify_script=True,
    always_on_top=True,
)

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
    icon=ICON,
    contents_directory='libs' 

)

# =========================================================
# BUILD: LAUNCHER
# =========================================================
a_main = Analysis(
    ['main.py'],
    pathex=[ost_root],
    binaries=[],
    datas=[('assets', 'assets')],
    hiddenimports=['core.paths', 'core.settings'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
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
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=ICON,
    contents_directory='libs' 
)

# --- MERGE ALL ---
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