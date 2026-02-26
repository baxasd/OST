import sys
import os

# ================================================
# APP DIMENSIONS
# ================================================
WINDOW_WIDTH = 1024
WINDOW_HEIGHT = 650
MIN_WINDOW_WIDTH = 800
MIN_WINDOW_HEIGHT = 550
PANEL_WIDTH = 280

# UNIVERSAL UI PALETTE
# Backgrounds
BG_DARK = "#F3F3F3"        # Windows base background (Absorbs glare)
BG_PANEL = "#FFFFFF"       # Elevated Card background (Pure White)
BORDER = "#E5E5E5"         # Very soft, subtle divider lines

# Typography
TEXT_MAIN = "#1A1A1A"      # Crisp near-black for primary readability
TEXT_DIM = "#605E5C"       # Soft slate for secondary text

# Branding & Accents
ACCENT_COLOR = "#005FB8"   # Classic Windows 11 Blue (High contrast)
ACCENT_HOVER = "#004E98"   # Slightly darker blue for active states

# Status & Console Colors
COLOR_ERROR = "#C42B1C"    # Fluent UI Error Red
COLOR_SUCCESS = "#0F7B0F"  # Fluent UI Success Green
COLOR_CONSOLE_BG = "#FAFAFA" 
COLOR_CONSOLE_TXT = "#1A1A1A"

# Launcher Specific Colors
LAUNCHER_BTN_BG = "#FFFFFF"
LAUNCHER_BTN_HOVER = "#F3F3F3"
LAUNCHER_BTN_PRESS = "#EDEBE9"
LAUNCHER_TITLE = "#1A1A1A"
LAUNCHER_SUBTITLE = "#605E5C"
LAUNCHER_VER = "#A19F9D"

# ================================================
# SKELETON & GRAPH PALETTE (Colorblind Safe)
# ================================================
COLOR_BONE_LEFT = "#005FB8"   # Blue
COLOR_BONE_RIGHT = "#D83B01"  # Rust/Orange
COLOR_BONE_CENTER = "#8764B8" # Purple
COLOR_JOINT = "#323130"       # Dark Gray

GRAPH_LEFT = "#005FB8"
GRAPH_RIGHT = "#D83B01"
GRAPH_CENTER = "#8764B8"
GRAPH_Z_AXIS = "#107C10"

# Advanced Analysis Plot Colors
PLOT_LEAN_X = "#D83B01"
PLOT_LEAN_Z = "#005FB8"
PLOT_KNEE_L = "#005FB8"
PLOT_KNEE_R = "#D83B01"
PLOT_HIP_L = "#005FB8"
PLOT_HIP_R = "#D83B01"
PLOT_SHO_L = "#005FB8"
PLOT_SHO_R = "#D83B01"
PLOT_ELB_L = "#005FB8"
PLOT_ELB_R = "#D83B01"

# ================================================
# ADVANCED CSS THEMES (The "Windows 11" Look)
# ================================================

# Main Window & Modern Scrollbars
CSS_MAIN_WINDOW = f"""
    QMainWindow {{ background-color: {BG_DARK}; }}
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 0px; }}
    QScrollBar::handle:vertical {{ background-color: #CCCCCC; min-height: 20px; border-radius: 5px; margin: 2px; }}
    QScrollBar::handle:vertical:hover {{ background-color: #999999; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
"""

# Turns the sidebar into a floating white card instead of a hard column
CSS_SIDEBAR = f"""
    QFrame {{
        background-color: {BG_PANEL}; 
        border: 2px solid {BORDER}; 
        border-radius: 15px;
    }}
"""

# Softened, sentence-case headers
CSS_HEADER = f"""
    color: {TEXT_MAIN}; 
    font-weight: 600; 
    font-size: 13px; 
    border: none; 
    margin-top: 12px;
    margin-bottom: 4px;
"""

# Completely flattens the 3D inputs and adds the Fluent "Bottom Border" focus state
CSS_INPUT = f"""
    QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {{
        background-color: #FDFDFD;
        border: 2px solid #D1D1D1;
        border-bottom: 1px solid #8F8F8F;
        border-radius: 4px;
        padding: 5px 10px;
        color: {TEXT_MAIN};
        min-height: 22px;
    }}
    QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover, QLineEdit:hover {{
        background-color: #F3F3F3;
    }}
    QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QLineEdit:focus {{
        border-bottom: 2px;
        background-color: #FFFFFF;
    }}
    QSpinBox::up-button, QDoubleSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::down-button {{
        width: 24px; background: transparent; border: none;
    }}
    QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover, QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
        background-color: #EAEAEA; border-radius: 2px;
    }}
    QComboBox::drop-down {{
        border: none; width: 24px;
    }}
"""

# Modern Rounded Buttons
CSS_BTN_PRIMARY = f"""
    QPushButton {{ 
        background-color: {ACCENT_COLOR}; 
        color: #FFFFFF; 
        font-weight: 600; 
        font-size: 13px;
        padding: 8px 16px; 
        border: 1px solid {ACCENT_COLOR}; 
        border-radius: 6px; 
    }}
    QPushButton:hover {{ background-color: {ACCENT_HOVER}; border-color: {ACCENT_HOVER}; }}
    QPushButton:pressed {{ background-color: #004080; }}
    QPushButton:disabled {{ background-color: #F3F3F3; color: #A19F9D; border: 1px solid {BORDER}; }}
"""

CSS_BTN_OUTLINE = f"""
    QPushButton {{ 
        background-color: {BG_PANEL}; 
        color: {TEXT_MAIN}; 
        font-weight: 600; 
        font-size: 13px;
        padding: 8px 16px; 
        border: 1px solid #D1D1D1; 
        border-radius: 6px; 
    }}
    QPushButton:hover {{ background-color: #F6F6F6; border-color: #C2C2C2; }}
    QPushButton:pressed {{ background-color: #EAEAEA; }}
    QPushButton:disabled {{ background-color: #FAFAFA; color: #A19F9D; border: 1px solid {BORDER}; }}
"""

CSS_BTN_STOP = f"""
    QPushButton {{ 
        background-color: {COLOR_ERROR}; 
        color: white; 
        font-weight: 600; 
        padding: 8px 16px; 
        border: none; 
        border-radius: 6px; 
    }}
    QPushButton:hover {{ background-color: #A42618; }}
"""
# ================================================
# APP STRINGS
# ================================================
APP_NAME = "OST Suite"
VERSION = "v0.2.1"
MAX_HISTORY_LENGTH = 50

# ================================================
# METRIC GRAPH CONFIGURATIONS
# ================================================
METRIC_CONFIGS = [
    ('lean_x', "Trunk Lat.", GRAPH_CENTER, -45, 45),
    ('lean_z', "Trunk Depth", GRAPH_Z_AXIS, -45, 45),
    ('l_knee', "L.Knee Flex", GRAPH_LEFT, 0, 180),
    ('r_knee', "R.Knee Flex", GRAPH_RIGHT, 0, 180),
    ('l_hip',  "L.Hip Flex", GRAPH_LEFT, 0, 180),
    ('r_hip',  "R.Hip Flex", GRAPH_RIGHT, 0, 180),
    ('l_sho',  "L.Shoulder Flex", GRAPH_LEFT, 0, 180),
    ('r_sho',  "R.Shoulder Flex", GRAPH_RIGHT, 0, 180),
    ('l_elb',  "L.Elbow Flex", GRAPH_LEFT, 0, 180),
    ('r_elb',  "R.Elbow Flex", GRAPH_RIGHT, 0, 180)
]

# ================================================
# PATH RESOLUTION
# ================================================
def get_base_path():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

BASE_DIR = get_base_path()
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

ICON = os.path.join(ASSETS_DIR, "icon-main-background.ico")
COMMAND_ICON = os.path.join(ASSETS_DIR, "command.ico")
LOGO = os.path.join(ASSETS_DIR, "logo-main-whiteText.png")

# ================================================
# UTILS
# ================================================
def close_splash():
    """Safely closes the PyInstaller splash screen if it exists."""
    try:
        import pyi_splash # type: ignore
        if pyi_splash.is_alive():
            pyi_splash.close()
    except Exception:
        pass