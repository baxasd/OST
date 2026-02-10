import pyqtgraph as pg
from PyQt6.QtCore import Qt
from core import metrics
from core.settings import (BG_DARK, BORDER, COLOR_JOINT, 
                           COLOR_BONE_LEFT, COLOR_BONE_RIGHT, COLOR_BONE_CENTER)

# --- CONFIGURATION ---

VISIBLE_NAMES = [
    "nose", 
    "left_shoulder", "right_shoulder",
    "left_elbow", "right_elbow", 
    "left_wrist", "right_wrist",
    "left_hip", "right_hip", 
    "left_knee", "right_knee", 
    "left_ankle", "right_ankle"
]

# List of bone connections (Simple list, logic handles color)
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

class SkeletonDisplay(pg.PlotWidget):
    def __init__(self):
        super().__init__()
        self.setBackground(BG_DARK) 
        self.setAspectLocked(True)
        self.hideAxis('left')
        self.hideAxis('bottom')
        
        self.addItem(pg.GridItem(pen=pg.mkPen(BORDER, width=1)))
        
        # Faint center axis
        self.ref_line = pg.InfiniteLine(pos=0, angle=90, pen=pg.mkPen(BORDER, width=2))
        self.addItem(self.ref_line)
        
        self.bones = {}
        self.joints = pg.ScatterPlotItem(size=12, brush=pg.mkBrush(COLOR_JOINT), pen=pg.mkPen(BG_DARK, width=1))
        self.addItem(self.joints)

    def center_view(self, x, y):
        self.setRange(xRange=(x-1.0, x+1.0), yRange=(y-1.2, y+1.2), padding=0)

    def update_frame(self, f):
        if not f: return
        
        # --- DRAW BONES ---
        for (n1, n2) in BONES_LIST:
            p1 = metrics.get_point(f, n1)
            p2 = metrics.get_point(f, n2)
            
            if p1 and p2:
                key = f"{n1}_{n2}"
                
                # --- UNIQUE COLOR LOGIC ---
                # Default to Center
                c = COLOR_BONE_CENTER
                
                # Identify Side based on joint names
                if "left" in n1 or "left" in n2:
                    c = COLOR_BONE_LEFT
                elif "right" in n1 or "right" in n2:
                    c = COLOR_BONE_RIGHT
                
                if key not in self.bones:
                    self.bones[key] = pg.PlotCurveItem(pen=pg.mkPen(c, width=5, cap_style=Qt.PenCapStyle.RoundCap))
                    self.addItem(self.bones[key])
                
                self.bones[key].setData([p1[0], p2[0]], [-p1[1], -p2[1]])

        # --- DRAW JOINTS ---
        xs, ys = [], []
        for name in VISIBLE_NAMES:
            p = metrics.get_point(f, name) 
            if p:
                xs.append(p[0])
                ys.append(-p[1])
        self.joints.setData(xs, ys)

        # Update Infinite Line Position
        hip = metrics.get_point(f, "hip_mid")
        if hip:
            self.ref_line.setPos(hip[0])