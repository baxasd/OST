# config.py

# ================= COLORS =================
C_BG        = "#0b0f19"   
C_PANEL_BG  = "#111827"   
C_CARD      = "#1f2937"   
C_GRID      = "#334155"   
C_AXIS      = "#475569"   
C_TEXT_MAIN = "#f8fafc"   
C_TEXT_SUB  = "#94a3b8"   

# Accents
C_TRACE     = "#f59e0b"   # Amber (Trunk Lean)
C_LEFT      = "#ef4444"   # Red
C_RIGHT     = "#3b82f6"   # Blue
C_TORSO     = "#cbd5e1"   # Grey
C_HEAD      = "#facc15"   # Yellow

# ================= SETTINGS =================
HISTORY_LEN = 150
# Window Width reduced slightly since we removed the extra graph column
WIN_WIDTH   = 1000  
WIN_HEIGHT  = 750

BONES_MAP = [
    ("hip_mid", "shoulder_mid"),
    ("shoulder_mid", "left_shoulder"), ("left_shoulder", "left_elbow"), ("left_elbow", "left_wrist"),
    ("shoulder_mid", "right_shoulder"), ("right_shoulder", "right_elbow"), ("right_elbow", "right_wrist"),
    ("hip_mid", "left_hip"), ("left_hip", "left_knee"), ("left_knee", "left_ankle"),
    ("hip_mid", "right_hip"), ("right_hip", "right_knee"), ("right_knee", "right_ankle"),
    ("shoulder_mid", "nose")
]