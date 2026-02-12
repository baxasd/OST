# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_all

block_cipher = None
ost_root = os.path.abspath(os.getcwd())

# --- 1. SETTINGS ---
sys.path.append(ost_root)
from core.settings import APP_NAME, ICON

exe_icon_path = ICON
if exe_icon_path and exe_icon_path.endswith('.png'):
    possible_ico = exe_icon_path.replace('.png', '.ico')
    if os.path.exists(possible_ico):
        exe_icon_path = possible_ico

if not os.path.exists(exe_icon_path):
    exe_icon_path = None

# --- 2. CONFLICT RESOLUTION FUNCTION ---
def deduplicate_binaries(bin_list):
    """
    Filters out duplicate DLLs.
    Keeps the FIRST occurrence of any filename.
    """
    seen = set()
    unique = []
    for src, dest in bin_list:
        # Normalize destination to filename to catch conflicts
        file_name = os.path.basename(src).lower()
        if file_name in seen:
            print(f"[-] Dropping duplicate binary to prevent conflict: {file_name}")
            continue
        seen.add(file_name)
        unique.append((src, dest))
    return unique

# --- 3. COLLECT DEPENDENCIES ---
extra_datas = [('assets', 'assets')]

# A. Collect MediaPipe FIRST (Priority High)
# We want MediaPipe's version of OpenCV DLLs to win.
mp_datas, mp_binaries, mp_hidden = collect_all('mediapipe')

# B. Collect RealSense
rs_datas, rs_binaries, rs_hidden = collect_all('pyrealsense2')

# C. Collect OpenCV (Priority Low)
# If MediaPipe already provided an opencv dll, we discard the one from here.
cv_datas, cv_binaries, cv_hidden = collect_all('cv2')

# --- 4. MERGE & FILTER ---
# Order matters here! mp_binaries must be first for the deduplicator to keep them.
raw_binaries = mp_binaries + rs_binaries + cv_binaries
final_binaries = deduplicate_binaries(raw_binaries)

final_datas = extra_datas + mp_datas + rs_datas + cv_datas

# Add specific hidden imports that MediaPipe C++ often misses
final_hidden = mp_hidden + rs_hidden + cv_hidden + [
    'sensors.realsense', 
    'core.io', 
    'core.pose', 
    'core.transforms', 
    'core.settings', 
    'mediapipe.python._framework_bindings',
    'mediapipe.python.solution_base',
    'google.protobuf'
]

# --- BUILD: RECORDER ---
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
exe_rec = EXE(
    pyz_rec,
    a_rec.scripts,
    [],
    exclude_binaries=True,
    name='record',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Keep True for debugging errors
    icon=exe_icon_path
)

# --- BUILD: STUDIO ---
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
exe_stu = EXE(
    pyz_stu,
    a_stu.scripts,
    [],
    exclude_binaries=True,
    name='studio',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=exe_icon_path
)

# --- BUILD: LAUNCHER ---
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
    icon=exe_icon_path
)

# --- MERGE ---
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
)