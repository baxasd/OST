# ost/core/data.py
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from datetime import datetime

# --- 1. CORE DATA STRUCTURES ---

@dataclass
class Joint:
    """Represents a single skeletal joint."""
    name: str = "unknown"
    pixel: Tuple[int, int] = (0, 0)       # (x, y) in image coordinates
    metric: Tuple[float, float, float] = (0.0, 0.0, 0.0) # (x, y, z) in meters
    visibility: float = 0.0               # 0.0 to 1.0 confidence score

@dataclass
class Frame:
    """Represents a single captured moment."""
    timestamp: float    # Seconds from start (or epoch)
    frame_id: int
    joints: Dict[int, Joint] = field(default_factory=dict) # Key is Mediapipe index (0-32)

    def get_joint(self, name_or_idx):
        """Helper to retrieve a joint by name or index safely."""
        # Mapping for common names if needed, or direct index access
        if isinstance(name_or_idx, int):
            return self.joints.get(name_or_idx)
        # Add string name lookup here if you implement a name map later
        return None

@dataclass
class Session:
    """Represents a full recording session."""
    subject_id: str = "Anonymous"
    date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    frames: List[Frame] = field(default_factory=list)

    @property
    def duration(self):
        if not self.frames:
            return 0.0
        return self.frames[-1].timestamp - self.frames[0].timestamp

# --- 2. THE BRIDGE (Conversion Logic) ---

def session_to_df(session: Session) -> pd.DataFrame:
    """Converts a Session object into a Pandas DataFrame (Long format for easy analysis)."""
    rows = []
    for f in session.frames:
        # Base row data
        row_base = {
            'timestamp': f.timestamp,
            'frame': f.frame_id
        }
        
        # Flatten joints into columns
        # Output format: joint_0_x, joint_0_y, joint_0_z ...
        for j_idx, joint in f.joints.items():
            # Metric Data (Primary for analysis)
            row_base[f'joint_{j_idx}_x'] = joint.metric[0]
            row_base[f'joint_{j_idx}_y'] = joint.metric[1]
            row_base[f'joint_{j_idx}_z'] = joint.metric[2]
            
            # Pixel Data (Useful for overlay debugging)
            row_base[f'joint_{j_idx}_px'] = joint.pixel[0]
            row_base[f'joint_{j_idx}_py'] = joint.pixel[1]
            
            # Visibility
            row_base[f'joint_{j_idx}_vis'] = joint.visibility
            
        rows.append(row_base)
    
    return pd.DataFrame(rows)

def df_to_session(df: pd.DataFrame) -> Session:
    """
    Converts a Pandas DataFrame back into a Session object.
    Robust against missing columns (e.g., if pixel data was dropped during processing).
    """
    # Create a new session
    # You might want to parse real date from metadata if available, defaulting to now
    sess = Session(subject_id="Processed", date=str(pd.Timestamp.now()))
    
    if df.empty:
        return sess

    # Sort by frame/time to ensure order
    if 'frame' in df.columns:
        df = df.sort_values('frame')
    
    for _, row in df.iterrows():
        # 1. Basic Info
        ts = row.get('timestamp', 0.0)
        fid = int(row.get('frame', 0))
        
        f = Frame(timestamp=ts, frame_id=fid)
        
        # 2. Scan columns to reconstruct joints
        # We look for columns pattern 'joint_{ID}_x' to identify valid joints
        processed_indices = set()
        for col in df.columns:
            if col.startswith('joint_') and col.endswith('_x'):
                try:
                    # Extract ID (e.g., "joint_11_x" -> 11)
                    idx = int(col.split('_')[1])
                    processed_indices.add(idx)
                except (ValueError, IndexError):
                    continue
        
        # 3. Populate Joints
        for idx in processed_indices:
            # Metric (Required for analysis)
            mx = row.get(f'joint_{idx}_x', 0.0)
            my = row.get(f'joint_{idx}_y', 0.0)
            mz = row.get(f'joint_{idx}_z', 0.0)
            
            # Pixel (Optional - might not exist in processed files)
            px = int(row.get(f'joint_{idx}_px', 0))
            py = int(row.get(f'joint_{idx}_py', 0))
            
            # Visibility (Optional)
            vis = row.get(f'joint_{idx}_vis', 1.0) # Default to 1.0 if missing
            
            f.joints[idx] = Joint(
                name=str(idx), # Can map to real names later (e.g. "Left Shoulder")
                pixel=(px, py),
                metric=(mx, my, mz),
                visibility=vis
            )
            
        sess.frames.append(f)
        
    return sess

# --- 3. HELPER (Optional Name Mapping) ---
# Useful if you want to access joints by name like 'left_shoulder'

POSE_LANDMARKS = {
    0: "nose", 1: "left_eye_inner", 2: "left_eye", 3: "left_eye_outer",
    4: "right_eye_inner", 5: "right_eye", 6: "right_eye_outer", 7: "left_ear",
    8: "right_ear", 9: "mouth_left", 10: "mouth_right", 11: "left_shoulder",
    12: "right_shoulder", 13: "left_elbow", 14: "right_elbow", 15: "left_wrist",
    16: "right_wrist", 17: "left_pinky", 18: "right_pinky", 19: "left_index",
    20: "right_index", 21: "left_thumb", 22: "right_thumb", 23: "left_hip",
    24: "right_hip", 25: "left_knee", 26: "right_knee", 27: "left_ankle",
    28: "right_ankle", 29: "left_heel", 30: "right_heel", 31: "left_foot_index",
    32: "right_foot_index"
}