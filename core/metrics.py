import math
import numpy as np
from core.data import Frame, NAME_TO_ID

def _get_vec(frame, name_or_id):
    """Internal helper to get numpy vector from frame."""
    idx = name_or_id
    if isinstance(name_or_id, str):
        idx = NAME_TO_ID.get(name_or_id)
    
    if idx is None or idx not in frame.joints:
        return None
    
    j = frame.joints[idx]
    # Return 3D vector now (x, y, z) to support depth calculations
    return np.array([j.metric[0], j.metric[1], j.metric[2]])

def get_point(f: Frame, name: str):
    """Returns 2D (x, y) tuple for visualization."""
    if name == "hip_mid":
        l = _get_vec(f, "left_hip")
        r = _get_vec(f, "right_hip")
        if l is not None and r is not None:
            res = (l + r) / 2
            return (res[0], res[1])
    elif name == "shoulder_mid":
        l = _get_vec(f, "left_shoulder")
        r = _get_vec(f, "right_shoulder")
        if l is not None and r is not None:
            res = (l + r) / 2
            return (res[0], res[1])
    else:
        v = _get_vec(f, name)
        if v is not None:
            return (v[0], v[1])
    return None

def calculate_joint_angle(f: Frame, p1: str, p2: str, p3: str) -> float:
    """Calculates 3D angle at p2."""
    a = _get_vec(f, p1)
    b = _get_vec(f, p2)
    c = _get_vec(f, p3)

    if a is None or b is None or c is None: return 0.0

    ba = a - b
    bc = c - b

    norm_ba = np.linalg.norm(ba)
    norm_bc = np.linalg.norm(bc)
    
    if norm_ba == 0 or norm_bc == 0: return 0.0

    cosine_angle = np.dot(ba, bc) / (norm_ba * norm_bc)
    angle = np.arccos(np.clip(cosine_angle, -1.0, 1.0))

    return np.degrees(angle)

def calculate_frontal_lean(f: Frame) -> float:
    """Calculates Side-to-Side Lean (X-Y plane)."""
    rh = _get_vec(f, "right_hip")
    lh = _get_vec(f, "left_hip")
    rs = _get_vec(f, "right_shoulder")
    ls = _get_vec(f, "left_shoulder")

    if rh is None or lh is None or rs is None or ls is None: return 0.0

    mid_hip = (rh + lh) / 2
    mid_shoulder = (rs + ls) / 2

    # X and Y difference
    dx = mid_shoulder[0] - mid_hip[0]
    dy = mid_shoulder[1] - mid_hip[1]
    
    # Angle relative to vertical (0, 1)
    return np.degrees(math.atan2(dx, -dy))

def calculate_sagittal_lean(f: Frame) -> float:
    """Calculates Forward/Backward Lean (Z-Y plane)."""
    rh = _get_vec(f, "right_hip")
    lh = _get_vec(f, "left_hip")
    rs = _get_vec(f, "right_shoulder")
    ls = _get_vec(f, "left_shoulder")

    if rh is None or lh is None or rs is None or ls is None: return 0.0

    mid_hip = (rh + lh) / 2
    mid_shoulder = (rs + ls) / 2

    # Z (depth) and Y (vertical) difference
    dz = mid_shoulder[2] - mid_hip[2]
    dy = mid_shoulder[1] - mid_hip[1]
    
    return np.degrees(math.atan2(dz, -dy))

def compute_all_metrics(f: Frame) -> dict:
    return {
        'lean_x': calculate_frontal_lean(f),   # Side-to-side
        'lean_z': calculate_sagittal_lean(f),  # Forward/Back
        
        'l_knee': calculate_joint_angle(f, "left_hip", "left_knee", "left_ankle"),
        'r_knee': calculate_joint_angle(f, "right_hip", "right_knee", "right_ankle"),
        
        'l_hip':  calculate_joint_angle(f, "left_shoulder", "left_hip", "left_knee"),
        'r_hip':  calculate_joint_angle(f, "right_shoulder", "right_hip", "right_knee"),
        
        'l_sho':  calculate_joint_angle(f, "left_hip", "left_shoulder", "left_elbow"),
        'r_sho':  calculate_joint_angle(f, "right_hip", "right_shoulder", "right_elbow"),
        
        'l_elb':  calculate_joint_angle(f, "left_shoulder", "left_elbow", "left_wrist"),
        'r_elb':  calculate_joint_angle(f, "right_shoulder", "right_elbow", "right_wrist")
    }