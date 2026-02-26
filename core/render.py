import pyqtgraph as pg
import pyqtgraph.opengl as gl
from PyQt6.QtCore import Qt
import numpy as np

from core import math
from core.config import *

# CONFIGURATION
VISIBLE_NAMES = [
    "nose", 
    "left_shoulder", "right_shoulder",
    "left_elbow", "right_elbow", 
    "left_wrist", "right_wrist",
    "left_hip", "right_hip", 
    "left_knee", "right_knee", 
    "left_ankle", "right_ankle"
]

# List of bone connections
BONES_LIST = [
    ("hip_mid", "shoulder_mid"),         # Spine
    ("hip_mid", "left_hip"),             # Pelvis L
    ("hip_mid", "right_hip"),            # Pelvis R
    ("shoulder_mid", "left_shoulder"),   # Clavicle L
    ("shoulder_mid", "right_shoulder"),  # Clavicle R
    
    ("left_shoulder", "left_elbow"),     # Arm L
    ("left_elbow", "left_wrist"),        # Forearm L
    ("right_shoulder", "right_elbow"),   # Arm R
    ("right_elbow", "right_wrist"),      # Forearm R
    
    ("left_hip", "left_knee"),           # Thigh L
    ("left_knee", "left_ankle"),         # Shin L
    ("right_hip", "right_knee"),         # Thigh R
    ("right_knee", "right_ankle"),       # Shin R
    
    ("shoulder_mid", "nose")             # Neck
]

def hex_to_rgba(hex_color, alpha=1.0):
    """Converts hex color string to (R, G, B, A) floats 0.0-1.0 for OpenGL"""
    c = pg.mkColor(hex_color)
    return (c.redF(), c.greenF(), c.blueF(), alpha)

def get_point_3d(f, name):
    """Helper to retrieve the full 3D vector for rendering"""
    if name == "hip_mid":
        l = math._get_vec(f, "left_hip")
        r = math._get_vec(f, "right_hip")
        if l is not None and r is not None:
            return (l + r) / 2.0
    elif name == "shoulder_mid":
        l = math._get_vec(f, "left_shoulder")
        r = math._get_vec(f, "right_shoulder")
        if l is not None and r is not None:
            return (l + r) / 2.0
    else:
        return math._get_vec(f, name)
    return None

class SkeletonDisplay(gl.GLViewWidget):
    def __init__(self):
        super().__init__()
        
        # Setup 3D Environment using your config colors
        self.setBackgroundColor(hex_to_rgba(BG_DARK))
        self.setCameraPosition(distance=2.5, elevation=15, azimuth=45)
        
        # Add Floor Grid
        grid = gl.GLGridItem()
        grid.setSize(x=5, y=5)
        grid.setSpacing(x=0.5, y=0.5)
        grid.setColor(hex_to_rgba(BORDER, alpha=0.5))
        self.addItem(grid)

        self.bones = {}
        
        # Joints Scatter Plot
        self.joints = gl.GLScatterPlotItem(color=hex_to_rgba(COLOR_JOINT), size=12.0)
        self.addItem(self.joints)

    def center_view(self, x, y, z=0):
        """Safely centers the 3D camera."""
        # Coordinate map: 3D_X = x, 3D_Y = z, 3D_Z = -y
        self.opts['center'] = pg.Vector(x, z, -y)

    def update_frame(self, f):
        if not f: return
        
        # Helper to map MediaPipe (X,Y,Z) to OpenGL Upright Coordinates
        def map_coords(vec):
            return np.array([vec[0], vec[2], -vec[1]], dtype=np.float32)

        # 1. DRAW BONES
        for (n1, n2) in BONES_LIST:
            key = f"{n1}_{n2}"
            v1 = get_point_3d(f, n1)
            v2 = get_point_3d(f, n2)
            
            # Create the bone object if it doesn't exist yet
            if key not in self.bones:
                hex_c = COLOR_BONE_CENTER
                if "left" in n1 or "left" in n2:
                    hex_c = COLOR_BONE_LEFT
                elif "right" in n1 or "right" in n2:
                    hex_c = COLOR_BONE_RIGHT
                
                self.bones[key] = gl.GLLinePlotItem(
                    color=hex_to_rgba(hex_c), 
                    width=4.0, 
                    antialias=True
                )
                self.addItem(self.bones[key])
            
            # FIX: Only draw the line if BOTH joints are visible. 
            # If one drops, ERASE the old line so it doesn't stretch across the screen!
            if v1 is not None and v2 is not None:
                p1 = map_coords(v1)
                p2 = map_coords(v2)
                self.bones[key].setData(pos=np.array([p1, p2], dtype=np.float32))
            else:
                self.bones[key].setData(pos=np.empty((0, 3), dtype=np.float32))

        # 2. DRAW JOINTS
        joint_positions = []
        for name in VISIBLE_NAMES:
            v = get_point_3d(f, name) 
            if v is not None:
                joint_positions.append(map_coords(v))
                
        if joint_positions:
            self.joints.setData(pos=np.array(joint_positions, dtype=np.float32))
        else:
            self.joints.setData(pos=np.empty((0, 3), dtype=np.float32))
            
        # Force the widget to repaint the new coordinates
        self.update()