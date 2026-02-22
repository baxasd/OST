import sys
import os
from PyInstaller.utils.hooks import collect_all

# 1. PATHS
# SPECPATH is a PyInstaller global that points to the folder containing this .spec file (ops/)
project_root = os.path.abspath(os.path.join(SPECPATH, '..')) #type: ignore

# Add the project root to sys.path so we can import our config directly
sys.path.insert(0, project_root)
from core.config import APP_NAME, ICON, COMMAND_ICON

# Explicit asset paths for the builder
SPLASH_IMG = os.path.join(project_root, 'assets', 'splash.png')
MANIFEST = os.path.join(project_root, 'ops', 'manifest.xml')
DLL_FIX = os.path.join(project_root, 'ops', 'dllFix.py')

block_cipher = None

# 2. COLLECT EXTERNAL LIBRARIES
mp_datas, mp_binaries, mp_hidden = collect_all('mediapipe')
rs_datas, rs_binaries, rs_hidden = collect_all('pyrealsense2')
cv_datas, cv_binaries, cv_hidden = collect_all('cv2')

# Merge Data & Hidden Imports (Added pyarrow for Parquet support)
final_datas = [(os.path.join(project_root, 'assets'), 'assets')] + mp_datas + rs_datas + cv_datas
final_hidden = mp_hidden + rs_hidden + cv_hidden + ['pyarrow.vendored.version']

# =============================================================================
#   BUILD 1: RECORDER
# =============================================================================
rec_hidden = final_hidden + ['sensors.realsense', 'core.storage', 'core.pose', 'core.depth', 'core.config']

a_rec = Analysis( #type: ignore
    [os.path.join(project_root, 'tools', 'record.py')],
    pathex=[project_root],
    datas=final_datas,
    hiddenimports=rec_hidden,
    runtime_hooks=[DLL_FIX],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz_rec = PYZ(a_rec.pure, a_rec.zipped_data, cipher=block_cipher) #type: ignore

# Note: Splash will only trigger if splash.png exists in your assets folder
if os.path.exists(SPLASH_IMG):
    splash_rec = Splash(SPLASH_IMG, binaries=a_rec.binaries, datas=a_rec.datas, text_size=12, minify_script=True, always_on_top=True) #type: ignore
    rec_splash_args = [splash_rec, splash_rec.binaries]
else:
    rec_splash_args = []

exe_rec = EXE( #type: ignore
    pyz_rec,
    a_rec.scripts,
    *rec_splash_args,
    [],
    exclude_binaries=True,
    name='record',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=COMMAND_ICON,
    manifest=MANIFEST,
    contents_directory='libs'
)

# =============================================================================
#   BUILD 2: STUDIO
# =============================================================================
stu_hidden = final_hidden + ['core.data', 'core.math', 'core.filters', 'core.widgets', 'core.render', 'core.config', 'pyqtgraph', 'pandas']

a_stu = Analysis( #type: ignore
    [os.path.join(project_root, 'tools', 'studio.py')], 
    pathex=[project_root],
    datas=final_datas,
    hiddenimports=stu_hidden,
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz_stu = PYZ(a_stu.pure, a_stu.zipped_data, cipher=block_cipher)  #type: ignore

if os.path.exists(SPLASH_IMG):
    splash_stu = Splash(SPLASH_IMG, binaries=a_stu.binaries, datas=a_stu.datas, text_size=12, minify_script=True, always_on_top=True) #type: ignore
    stu_splash_args = [splash_stu, splash_stu.binaries]
else:
    stu_splash_args = []

exe_stu = EXE( #type: ignore
    pyz_stu,
    a_stu.scripts,
    *stu_splash_args,
    [],
    exclude_binaries=True,
    name='studio',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=COMMAND_ICON,
    manifest=MANIFEST,
    contents_directory='libs'
)

# =============================================================================
#   BUILD 3: LAUNCHER (MAIN)
# =============================================================================
a_main = Analysis( #type: ignore
    [os.path.join(project_root, 'main.py')],
    pathex=[project_root],
    binaries=[],
    datas=[(os.path.join(project_root, 'assets'), 'assets')],
    hiddenimports=['core.config'],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz_main = PYZ(a_main.pure, a_main.zipped_data, cipher=block_cipher) #type: ignore

exe_main = EXE( #type: ignore
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
    manifest=MANIFEST,
    contents_directory='libs'
)

# =============================================================================
#   FINAL MERGE & ORGANIZE
# =============================================================================
coll = COLLECT( #type: ignore
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