import sys
import os

# --- APP DIMENSIONS ---
WINDOW_WIDTH = 1024
WINDOW_HEIGHT = 650
MIN_WINDOW_WIDTH = 800
MIN_WINDOW_HEIGHT = 550
PANEL_WIDTH = 320

# --- UI PALETTE ---
ACCENT_COLOR = "#0FA6C1"
ACCENT_HOVER = "#167B87"
BG_DARK = "#18181b"
BG_PANEL = "#27272a"
TEXT_MAIN = "#e4e4e7"
TEXT_DIM = "#a1a1aa"
BORDER = "#3f3f46"

# --- SKELETON & GRAPH PALETTE ---
COLOR_BONE_LEFT = "#9e2a2b"
COLOR_BONE_RIGHT = "#2e86c1"
COLOR_BONE_CENTER = "#7fb069"
COLOR_JOINT = "#f4e9d8"

GRAPH_LEFT = "#9e2a2b"
GRAPH_RIGHT = "#2e86c1"
GRAPH_CENTER = "#fbbf24"
GRAPH_Z_AXIS = "#7fb069"

# --- APP STRINGS ---
APP_NAME = "OST Suite"
VERSION = "v0.2.0"
MAX_HISTORY_LENGTH = 40

# --- UNIVERSAL CSS THEMES ---
CSS_MAIN_WINDOW = f"QMainWindow {{ background-color: {BG_DARK}; }}"
CSS_SIDEBAR = f"background-color: {BG_PANEL}; border-left: 1px solid {BORDER}; border-right: 1px solid {BORDER};"
CSS_HEADER = f"color: {TEXT_MAIN}; font-weight: bold; font-size: 11px; border: none; margin-bottom: 2px;"
CSS_INPUT = f"background-color: #18181b; color: white; border: 1px solid {BORDER}; padding: 6px; border-radius: 4px;"

CSS_BTN_PRIMARY = f"""
    QPushButton {{ background-color: {ACCENT_COLOR}; color: {BG_DARK}; font-weight: bold; padding: 10px; border: none; border-radius: 4px; }}
    QPushButton:hover {{ background-color: {ACCENT_HOVER}; }}
    QPushButton:disabled {{ background-color: #3f3f46; color: #71717a; }}
"""
CSS_BTN_OUTLINE = f"""
    QPushButton {{ background-color: transparent; color: {TEXT_DIM}; font-weight: bold; border: 1px solid {BORDER}; padding: 10px; border-radius: 4px; }}
    QPushButton:hover {{ border-color: {ACCENT_COLOR}; color: {ACCENT_COLOR}; }}
    QPushButton:disabled {{ border-color: #333; color: #555; }}
"""


# --- METRIC GRAPH CONFIGURATIONS ---
# Format: (Dictionary Key, UI Title, Color, Min Range, Max Range)
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

# --- PATH RESOLUTION ---
def get_base_path():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

BASE_DIR = get_base_path()
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

ICON = os.path.join(ASSETS_DIR, "icon-main-background.ico")
COMMAND_ICON = os.path.join(ASSETS_DIR, "command.ico")
LOGO = os.path.join(ASSETS_DIR, "logo-main-whiteText.png")

# --- BOILERPLATE UTILS ---
def close_splash():
    """Safely closes the PyInstaller splash screen if it exists."""
    try:
        import pyi_splash # type: ignore
        if pyi_splash.is_alive():
            pyi_splash.close()
    except Exception:
        pass