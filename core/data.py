import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Tuple
from datetime import datetime

# Mediapipe Mapping
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

@dataclass
class Joint:
    name: str = "unknown"
    pixel: Tuple[int, int] = (0, 0)       
    metric: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    visibility: float = 0.0

@dataclass
class Frame:
    timestamp: float
    frame_id: int
    joints: Dict[int, Joint] = field(default_factory=dict) 

@dataclass
class Session:
    subject_id: str = "Anonymous"
    date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    frames: List[Frame] = field(default_factory=list)

    @property
    def fps(self):
        if len(self.frames) < 2: return 30.0
        dur = self.frames[-1].timestamp - self.frames[0].timestamp
        return len(self.frames) / dur if dur > 0 else 30.0

    @property
    def duration(self):
        if not self.frames: return 0.0
        return self.frames[-1].timestamp - self.frames[0].timestamp

def session_to_df(session: Session) -> pd.DataFrame:
    rows = []
    for f in session.frames:
        row = {'timestamp': f.timestamp, 'frame': f.frame_id}
        for j_idx, joint in f.joints.items():
            row[f'j{j_idx}_x'] = joint.metric[0]
            row[f'j{j_idx}_y'] = joint.metric[1]
            row[f'j{j_idx}_z'] = joint.metric[2]
        rows.append(row)
    return pd.DataFrame(rows)

def df_to_session(df: pd.DataFrame) -> Session:
    sess = Session(subject_id="Processed", date=str(pd.Timestamp.now()))
    if df.empty: return sess
    
    # Identify Columns
    x_cols = [c for c in df.columns if c.endswith('_x') and (c.startswith('j') or c.startswith('joint'))]

    # --- TIMESTAMP FIX ---
    start_time = None
    
    for i, row in df.iterrows():
        # Handle Timestamp (String vs Float)
        raw_ts = row.get('timestamp', 0.0)
        ts = 0.0
        
        try:
            # Case A: String (ISO format from Recorder)
            if isinstance(raw_ts, str):
                dt = datetime.fromisoformat(raw_ts)
                if start_time is None: start_time = dt
                ts = (dt - start_time).total_seconds()
            
            # Case B: Float/Int (Already seconds or epoch)
            else:
                raw_val = float(raw_ts)
                if start_time is None: start_time = raw_val
                ts = raw_val - start_time

        except Exception:
            # Fallback if parsing fails totally
            ts = float(i) * 0.033 

        f = Frame(timestamp=ts, frame_id=int(i))
        
        for col in x_cols:
            try:
                # Parse ID
                prefix = col[:-2] 
                if 'joint_' in prefix: idx = int(prefix.split('_')[1])
                else: idx = int(prefix[1:])
                
                mx = float(row.get(f'{prefix}_x', 0.0))
                my = float(row.get(f'{prefix}_y', 0.0))
                mz = float(row.get(f'{prefix}_z', 0.0))
                
                real_name = POSE_LANDMARKS.get(idx, str(idx))
                f.joints[idx] = Joint(name=real_name, metric=(mx, my, mz))
            except: continue
            
        sess.frames.append(f)
    return sess