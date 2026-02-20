# --- APP DIMENSIONS ---
WINDOW_WIDTH = 1024
WINDOW_HEIGHT = 650
MIN_WINDOW_WIDTH = 800
MIN_WINDOW_HEIGHT = 550
PANEL_WIDTH = 320

# --- UI PALETTE ---
ACCENT_COLOR = "#0FA6C1"      # Cyan Accent (Used for Highlights & Buttons)
ACCENT_HOVER = "#167B87"      # Darker Cyan (Hover State)
BG_DARK = "#18181b"           # Zinc 950 (Main Window)
BG_PANEL = "#27272a"          # Zinc 800 (Side Panel)
TEXT_MAIN = "#e4e4e7"         # Zinc 200
TEXT_DIM = "#a1a1aa"          # Zinc 400
BORDER = "#3f3f46"            # Zinc 700

# --- SKELETON PALETTE (Unique/Lateral) ---
COLOR_BONE_LEFT = "#9e2a2b"
COLOR_BONE_RIGHT = "#2e86c1"
COLOR_BONE_CENTER = "#7fb069"
COLOR_JOINT = "#f4e9d8"

# --- GRAPH PALETTE ---
GRAPH_LEFT = "#9e2a2b"        # Matches Bone Left
GRAPH_RIGHT = "#2e86c1"       # Matches Bone Right
GRAPH_CENTER = "#fbbf24"      # Amber
GRAPH_Z_AXIS = "#7fb069"    # Emerald

# Version
VERSION = "v0.2.0"

# Recording Settings
STYLESHEET = """
QMainWindow { background-color: #2b2b2b; }
QFrame#Sidebar { background-color: #212121; border-right: 1px solid #3a3a3a; }
QLabel { color: #e0e0e0; font-family: 'Segoe UI', Arial; }
QLineEdit { 
    background-color: #3a3a3a; color: white; border: 1px solid #555; 
    border-radius: 4px; padding: 4px; font-size: 12px;
}
QComboBox { 
    background-color: #3a3a3a; color: white; border: 1px solid #555; 
    border-radius: 4px; padding: 4px;
}
QComboBox::drop-down { border: none; }
QPushButton#RecBtn { 
    background-color: #28a745; color: white; border-radius: 5px; 
    font-weight: bold; font-size: 14px;
}
QPushButton#RecBtn:hover { background-color: #218838; }
QPushButton#RecBtn:pressed { background-color: #1e7e34; }
QPushButton#RecBtn[recording="true"] { background-color: #dc3545; }
QPushButton#RecBtn[recording="true"]:hover { background-color: #c82333; }
"""

# History of Line Graphs
MAX_HISTORY_LENGTH = 40

import sys
import os

def get_base_path():
    """Returns the base directory whether frozen or script."""
    if getattr(sys, 'frozen', False):
        # In frozen mode, assets are usually in the internal temporary folder
        return sys._MEIPASS
    else:
        # In dev mode, return the project root
        # This file is in ost/core/, so we go up two levels
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

BASE_DIR = get_base_path()

# Define Paths
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
ICON = os.path.join(ASSETS_DIR, "icon-main-background.ico")
COMMAND_ICON = os.path.join(ASSETS_DIR, "command.ico")
LOGO = os.path.join(ASSETS_DIR, "logo-main-whiteText.png")



# Configs
APP_NAME = "OST Suite"
VERSION = "V0.1.0"