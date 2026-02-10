import math
import numpy as np
from core.data import Frame, Joint, POSE_LANDMARKS

# Reverse mapping for easier lookups
NAME_TO_ID = {v: k for k, v in POSE_LANDMARKS.items()}

def _get_vec(frame, name_or_id):
    """Helper to get numpy vector from frame."""
    idx = name_or_id
    if isinstance(name_or_id, str):
        idx = NAME_TO_ID.get(name_or_id)
    
    if idx is None or idx not in frame.joints:
        return None
    
    j = frame.joints[idx]
    return np.array([j.metric[0], j.metric[1]])

def calculate_joint_angle(f: Frame, p1_name: str, p2_name: str, p3_name: str) -> float:
    """Calculates 2D angle at p2."""
    a = _get_vec(f, p1_name)
    b = _get_vec(f, p2_name)
    c = _get_vec(f, p3_name)

    if a is None or b is None or c is None:
        return 0.0

    ba = a - b
    bc = c - b

    norm_ba = np.linalg.norm(ba)
    norm_bc = np.linalg.norm(bc)
    
    if norm_ba == 0 or norm_bc == 0:
        return 0.0

    cosine_angle = np.dot(ba, bc) / (norm_ba * norm_bc)
    angle = np.arccos(np.clip(cosine_angle, -1.0, 1.0))

    return np.degrees(angle)

def calculate_lean_angle(f: Frame) -> float:
    """
    Calculates Vertical Trunk Lean.
    Computes Mid-Hip and Mid-Shoulder dynamically.
    """
    # 1. Get 4 corners of torso
    rh = _get_vec(f, "right_hip")
    lh = _get_vec(f, "left_hip")
    rs = _get_vec(f, "right_shoulder")
    ls = _get_vec(f, "left_shoulder")

    if rh is None or lh is None or rs is None or ls is None:
        return 0.0

    # 2. Compute Midpoints
    mid_hip = (rh + lh) / 2
    mid_shoulder = (rs + ls) / 2

    # 3. Calculate Vector
    dx = mid_shoulder[0] - mid_hip[0]
    dy = mid_shoulder[1] - mid_hip[1]
    
    # 4. Angle vs Vertical (0, 1)
    # Using atan2(dx, dy) gives angle from vertical axis
    # dy is usually negative (up), so we flip it
    return np.degrees(math.atan2(dx, -dy))