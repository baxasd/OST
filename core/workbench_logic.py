import io
import json
import os
import struct
import sys
import numpy as np
import pandas as pd
from scipy.signal import detrend
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

# =============================================================================
# 1. CONSTANTS & THEME
# =============================================================================

COLOR_LEFT = "#005FB8"
COLOR_RIGHT = "#D83B01"
COLOR_CENTER = "#8764B8" 
COLOR_RAW_DATA = "#D83B01"
COLOR_CLEAN_DATA = "#107C10"
PREP_RAW_WIDTH = 1.5
PREP_CLEAN_WIDTH = 2.5
COLOR_JOINT = "#323130"
COLOR_SKELETON_BG = "rgba(0,0,0,0.02)"
COLOR_REF_LINE = "rgba(0,0,0,0.15)"

if getattr(sys, 'frozen', False):
    # In one-directory mode with contents_directory='libs', 
    # the actual files are in the 'libs' folder.
    root_base = sys._MEIPASS
    libs_path = os.path.join(root_base, 'libs')
    if os.path.exists(libs_path):
        ROOT_DIR = libs_path
    else:
        ROOT_DIR = root_base
    BASE_DIR = os.path.dirname(sys.executable)
else:
    _current_dir = os.path.dirname(os.path.abspath(__file__))
    ROOT_DIR = os.path.abspath(os.path.join(_current_dir, '..'))
    BASE_DIR = ROOT_DIR

LOGO_PATH = os.path.join(ROOT_DIR, 'assets', 'logo.png')
ICON_PATH = os.path.join(ROOT_DIR, 'assets', 'icon.ico')
COMMAND_ICON = os.path.join(ROOT_DIR, 'assets', 'command.ico')
APP_VERSION = "0.1.0"

# =============================================================================
# 2. DATA STRUCTURES (MediaPipe Topology mapped to Math Engine Names)
# =============================================================================

POSE_LANDMARKS = {
    0: "nose", 1: "left_eye_inner", 2: "left_eye", 3: "left_eye_outer",
    4: "right_eye_inner", 5: "right_eye", 6: "right_eye_outer",
    7: "left_ear", 8: "right_ear", 9: "mouth_left", 10: "mouth_right",
    11: "left_shoulder", 12: "right_shoulder", 13: "left_elbow", 14: "right_elbow",
    15: "left_wrist", 16: "right_wrist", 17: "left_pinky", 18: "right_pinky",
    19: "left_index", 20: "right_index", 21: "left_thumb", 22: "right_thumb",
    23: "left_hip", 24: "right_hip", 25: "left_knee", 26: "right_knee",
    27: "left_ankle", 28: "right_ankle", 29: "left_heel", 30: "right_heel",
    31: "left_foot_index", 32: "right_foot_index"
}

NAME_TO_ID = {v: k for k, v in POSE_LANDMARKS.items()}

def _resolve_joint_index(prefix: str):
    """Map a column prefix to a MediaPipe landmark index.

    Accepts three naming conventions:
      • 'joint_25'   (binary recorder output)
      • 'j25'        (compact)
      • 'left_knee'  (named landmark, e.g. CSV exports)
    Returns the integer index, or None if the prefix is not a joint.
    """
    if prefix in NAME_TO_ID:
        return NAME_TO_ID[prefix]
    if prefix.startswith('joint_'):
        try:
            return int(prefix.split('_')[1])
        except (ValueError, IndexError):
            return None
    if len(prefix) >= 2 and prefix[0] == 'j' and prefix[1:].isdigit():
        return int(prefix[1:])
    return None

def identify_joint_columns(columns: List[str]) -> List[str]:
    return [c for c in columns if c.endswith('_x') and _resolve_joint_index(c[:-2]) is not None]

@dataclass
class Joint:
    name: str = "unknown"
    metric: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    # Raw 2D image pixel (px, py). NaN when unavailable (e.g. CSV without pixels).
    pixel: Tuple[float, float] = (float('nan'), float('nan'))

@dataclass
class Frame:
    timestamp: float
    frame_id: int
    joints: Dict[int, Joint] = field(default_factory=dict) 

@dataclass
class Session:
    frames: List[Frame] = field(default_factory=list)
    @property
    def fps(self):
        if len(self.frames) < 2: return 30.0
        dur = self.duration
        return len(self.frames) / dur if dur > 0.001 else 30.0
    @property
    def duration(self):
        if not self.frames: return 0.0
        return self.frames[-1].timestamp - self.frames[0].timestamp

def df_to_session(df: pd.DataFrame) -> Session:
    sess = Session()
    if df.empty: return sess
    x_cols = identify_joint_columns(df.columns)
    start_time = None
    records = df.to_dict('records')
    parsed_columns = []
    for col in x_cols:
        prefix = col[:-2]
        idx = _resolve_joint_index(prefix)
        if idx is None: continue
        real_name = POSE_LANDMARKS.get(idx, str(idx))
        # Decide the 2D source per joint at load time: use raw pixels when the
        # recording has them, otherwise treat world (x, y) as the 2D coordinate.
        # This prevents any per-frame mixing of pixel- and world-space vectors.
        has_px = f'{prefix}_px' in df.columns and f'{prefix}_py' in df.columns
        parsed_columns.append((prefix, idx, real_name, has_px))

    for i, row in enumerate(records):
        raw_ts = row.get('timestamp') or row.get('Timestamp') or row.get('time') or 0.0
        try:
            if isinstance(raw_ts, (int, float)):
                if start_time is None: start_time = float(raw_ts)
                ts = float(raw_ts) - start_time
            else:
                dt = pd.to_datetime(raw_ts)
                if start_time is None: start_time = dt
                ts = (dt - start_time).total_seconds()
        except: ts = float(i) * 0.033 
        
        f = Frame(timestamp=ts, frame_id=int(i))
        for prefix, idx, real_name, has_px in parsed_columns:
            wx = float(row.get(f'{prefix}_x', 0.0))
            wy = float(row.get(f'{prefix}_y', 0.0))
            wz = float(row.get(f'{prefix}_z', 0.0))
            if has_px:
                px = float(row.get(f'{prefix}_px', float('nan')))
                py = float(row.get(f'{prefix}_py', float('nan')))
            else:
                px, py = wx, wy   # no pixels in this recording -> use world x,y as 2D
            f.joints[idx] = Joint(name=real_name, metric=(wx, wy, wz), pixel=(px, py))
        sess.frames.append(f)
    return sess

# =============================================================================
# 3. DSP FILTERS
# =============================================================================

class PipelineProcessor:
    @staticmethod
    def _get_all_joint_cols(df: pd.DataFrame) -> list:
        x_cols = identify_joint_columns(df.columns)
        all_cols = []
        for c in x_cols:
            base = c[:-2]
            # Include pixel channels so interpolation/smoothing also clean the
            # px,py signals that the sagittal metrics are computed from.
            all_cols.extend([f"{base}_x", f"{base}_y", f"{base}_z", f"{base}_px", f"{base}_py"])
        return [c for c in all_cols if c in df.columns]

    @staticmethod
    def validate(df: pd.DataFrame):
        x_cols = identify_joint_columns(df.columns)
        if not x_cols: return "CRITICAL: No joint data found.", False
        existing_cols = PipelineProcessor._get_all_joint_cols(df)
        zeros = (df[existing_cols] == 0.0).sum().sum()
        nans = df[existing_cols].isna().sum().sum()
        report = []
        if zeros > 0: report.append(f"• Tracking Loss: {(zeros / df[existing_cols].size) * 100:.1f}% zeros.")
        if nans > 0: report.append(f"• Data Gaps: {nans} NaNs.")
        return ("DATA INTEGRITY: PASS", False) if not report else ("ISSUES:\n" + "\n".join(report), True)

    @staticmethod
    def remove_teleportation(df: pd.DataFrame, threshold=0.5):
        df_clean = df.copy()
        x_cols = identify_joint_columns(df_clean.columns)
        teleports = 0
        for c in x_cols:
            base = c[:-2]
            cols = [f"{base}_x", f"{base}_y", f"{base}_z"]
            if not all(k in df_clean.columns for k in cols): continue
            dists = np.sqrt((df_clean[cols].diff()**2).sum(axis=1))
            jump_idx = dists > threshold
            teleports += jump_idx.sum()
            df_clean.loc[jump_idx, cols] = np.nan
        return df_clean, teleports

    @staticmethod
    def repair(df: pd.DataFrame, method='linear', limit=30):
        df_clean = df.copy()
        valid_cols = PipelineProcessor._get_all_joint_cols(df_clean)
        df_clean[valid_cols] = df_clean[valid_cols].replace(0.0, np.nan).interpolate(method=method, limit=limit, limit_direction='both').fillna(0.0)
        return df_clean

    @staticmethod
    def smooth(df: pd.DataFrame, window=5):
        df_proc = df.copy()
        valid_cols = PipelineProcessor._get_all_joint_cols(df_proc)
        if valid_cols: df_proc[valid_cols] = df_proc[valid_cols].rolling(window=window, min_periods=1, center=True).mean()
        return df_proc

# =============================================================================
# 4. KINEMATICS (Math Engine Restoration from motion.py)
# =============================================================================

def _get_vec(frame: Frame, name_or_id):
    """3D world vector (meters). NOTE: depth-scaled and noisy on a single
    side-camera — prefer _get_vec2d for sagittal-plane metrics."""
    idx = NAME_TO_ID.get(name_or_id) if isinstance(name_or_id, str) else name_or_id
    if idx is None or idx not in frame.joints: return None
    j = frame.joints[idx]
    return np.array([j.metric[0], j.metric[1], j.metric[2]])

def _get_vec2d(frame: Frame, name_or_id):
    """2D sagittal-plane vector [px, py]. The source (raw pixels vs world x,y)
    is resolved once per joint at load time in df_to_session, so this never
    mixes coordinate spaces. Returns None if the joint is missing/non-finite."""
    idx = NAME_TO_ID.get(name_or_id) if isinstance(name_or_id, str) else name_or_id
    if idx is None or idx not in frame.joints: return None
    j = frame.joints[idx]
    v = np.array([float(j.pixel[0]), float(j.pixel[1])])
    return v if np.all(np.isfinite(v)) else None

def _midpoint2d(f: Frame, a: str, b: str):
    va, vb = _get_vec2d(f, a), _get_vec2d(f, b)
    if va is None or vb is None: return None
    return (va + vb) / 2.0

def _hip_mid2d(f: Frame):      return _midpoint2d(f, "left_hip", "right_hip")
def _shoulder_mid2d(f: Frame): return _midpoint2d(f, "left_shoulder", "right_shoulder")

def calculate_joint_angle(f: Frame, p1: str, p2: str, p3: str) -> float:
    """Interior angle at p2 in full 3D (degrees). Depth-scaled; kept as a
    utility but the 2D form is used for the sagittal gait metrics."""
    a, b, c = _get_vec(f, p1), _get_vec(f, p2), _get_vec(f, p3)
    if any(v is None for v in [a, b, c]): return float('nan')
    ba, bc = a - b, c - b
    na, nc = np.linalg.norm(ba), np.linalg.norm(bc)
    if na == 0 or nc == 0: return float('nan')
    return float(np.degrees(np.arccos(np.clip(np.dot(ba, bc) / (na * nc), -1.0, 1.0))))

def calculate_joint_angle_2d(f: Frame, p1: str, p2: str, p3: str) -> float:
    """Interior angle at p2 in the 2D image (sagittal) plane, degrees."""
    a, b, c = _get_vec2d(f, p1), _get_vec2d(f, p2), _get_vec2d(f, p3)
    if a is None or b is None or c is None: return float('nan')
    ba, bc = a - b, c - b
    na, nc = np.linalg.norm(ba), np.linalg.norm(bc)
    if na == 0 or nc == 0: return float('nan')
    return float(np.degrees(np.arccos(np.clip(np.dot(ba, bc) / (na * nc), -1.0, 1.0))))

def _lean_from_vertical_2d(base, top) -> float:
    """Lean angle (deg) of the base->top segment away from image-vertical.
    +Y is down in image space, so -dy is the upward component; positive angle
    leans toward +X (image right)."""
    if base is None or top is None: return float('nan')
    dx = top[0] - base[0]
    dy = top[1] - base[1]
    return float(np.degrees(np.arctan2(dx, -dy)))

def calculate_trunk_lean(f: Frame) -> float:
    """Forward/back trunk lean in the sagittal plane (hip-mid -> shoulder-mid)."""
    return _lean_from_vertical_2d(_hip_mid2d(f), _shoulder_mid2d(f))

def calculate_head_lean(f: Frame) -> float:
    """Head/neck lean relative to the shoulder line (shoulder-mid -> nose)."""
    return _lean_from_vertical_2d(_shoulder_mid2d(f), _get_vec2d(f, "nose"))

def _torso_length_px(f: Frame) -> float:
    hm, sm = _hip_mid2d(f), _shoulder_mid2d(f)
    if hm is None or sm is None: return float('nan')
    return float(np.linalg.norm(sm - hm))

def session_torso_length(session: Session) -> float:
    """Robust torso pixel-length (median over frames). Used to normalize
    distance metrics so they compare across subjects and camera distances."""
    vals = [_torso_length_px(f) for f in session.frames]
    vals = [v for v in vals if np.isfinite(v) and v > 1e-6]
    return float(np.median(vals)) if vals else float('nan')

def compute_all_metrics(f: Frame, torso_len: float = None) -> dict:
    """Per-frame sagittal-plane metrics, computed from 2D pixels.

    Upper body (primary): trunk lean, head lean, shoulder swing, elbow flexion.
    Pelvis position signals: com_x (-> X drift) and vert_osc (-> cadence),
    normalized by torso length when available so they are scale-invariant.
    """
    hip = _hip_mid2d(f)
    metrics = {
        'trunk_lean': calculate_trunk_lean(f),
        'head_lean':  calculate_head_lean(f),
        'l_sho': calculate_joint_angle_2d(f, "left_hip", "left_shoulder", "left_elbow"),
        'r_sho': calculate_joint_angle_2d(f, "right_hip", "right_shoulder", "right_elbow"),
        'l_elb': calculate_joint_angle_2d(f, "left_shoulder", "left_elbow", "left_wrist"),
        'r_elb': calculate_joint_angle_2d(f, "right_shoulder", "right_elbow", "right_wrist"),
    }
    scale = torso_len if (torso_len and np.isfinite(torso_len) and torso_len > 1e-6) else 1.0
    metrics['com_x']    = float(hip[0] / scale) if hip is not None else float('nan')
    metrics['vert_osc'] = float(hip[1] / scale) if hip is not None else float('nan')
    return metrics

# Headline angle metrics (degrees) emitted by compute_all_metrics.
ANGLE_METRICS = ['trunk_lean', 'head_lean', 'l_sho', 'r_sho', 'l_elb', 'r_elb']

# Angles that are trustworthy on a single side-mounted (sagittal) camera and have
# a clear fatigue direction — the Fatigue Analysis default. Trunk lean is the
# primary validated running-fatigue marker (runners lean further forward as they
# tire); head lean is a postural secondary. The left/right shoulder & elbow angles
# are intentionally excluded from the default because the far limb is occluded and
# estimated in profile, so their left/right split is unreliable.
RELIABLE_FATIGUE_METRICS = ['trunk_lean', 'head_lean']

def generate_analysis_report(session):
    torso_len = session_torso_length(session)
    data = []
    for f in session.frames:
        m = compute_all_metrics(f, torso_len)
        m.update({'timestamp': f.timestamp, 'frame': f.frame_id})
        data.append(m)
    df = pd.DataFrame(data)
    stats = df.drop(columns=['timestamp', 'frame']).describe()
    return df, stats

def build_summary(ts_df: pd.DataFrame, fps: float) -> pd.DataFrame:
    """Frame-level summary stats enriched with ROM and peak angular velocity.

    Computed from per-frame data (not per-second means) so that range-of-motion
    and peak velocity reflect true kinematics rather than time-averaged values.
    """
    exclude = {'timestamp', 'frame', 'time_sec', 'time_min'}
    metric_cols = [c for c in ts_df.columns if c not in exclude]
    stats = ts_df[metric_cols].describe().T
    stats['rom'] = stats['max'] - stats['min']
    dt = 1.0 / fps if fps and fps > 0 else 1.0 / 30.0
    for c in metric_cols:
        vel = (ts_df[c].diff().abs() / dt).to_numpy()
        stats.loc[c, 'peak_vel'] = float(np.nanmax(vel)) if vel.size and not np.all(np.isnan(vel)) else np.nan
    return stats

def compute_cadence(signal, fps: float, fmin: float = 0.5, fmax: float = 4.0) -> tuple:
    """Step cadence from a vertical-oscillation signal (e.g. vert_osc) via FFT.

    The pelvis rises and falls once per step, so the dominant spectral frequency
    in the gait band is the step frequency. Returns
    (cadence_steps_per_min, step_freq_hz); (nan, nan) if too short / no peak.
    """
    s = pd.Series(signal, dtype=float).interpolate(limit_direction='both').to_numpy()
    s = s[np.isfinite(s)]
    if s.size < int(max(2 * fps, 8)):
        return float('nan'), float('nan')
    s = detrend(s)
    n = s.size
    mag = np.abs(np.fft.rfft(s * np.hanning(n)))
    freqs = np.fft.rfftfreq(n, d=1.0 / fps)
    band = (freqs >= fmin) & (freqs <= fmax)
    if not band.any():
        return float('nan'), float('nan')
    f_dom = float(freqs[band][np.argmax(mag[band])])
    return f_dom * 60.0, f_dom

def compute_drift(signal, fps: float, smooth_sec: float = 3.0) -> tuple:
    """Slow positional drift of a normalized position signal (e.g. com_x).

    Low-passes out the per-stride oscillation (rolling mean over ~smooth_sec),
    then linear-fits the trend. Returns (net_drift, drift_rate_per_min) in the
    signal's units (torso lengths when com_x is torso-normalized).
    """
    s = pd.Series(signal, dtype=float).interpolate(limit_direction='both')
    if s.notna().sum() < 2:
        return float('nan'), float('nan')
    win = max(1, int(round(smooth_sec * fps)))
    low = s.rolling(win, min_periods=1, center=True).mean().to_numpy()
    t_min = np.arange(low.size) / float(fps) / 60.0
    mask = np.isfinite(low)
    if mask.sum() < 2:
        return float('nan'), float('nan')
    slope, _ = np.polyfit(t_min[mask], low[mask], 1)
    net = float(low[mask][-1] - low[mask][0])
    return net, float(slope)

# =============================================================================
# 4b. TIME WINDOWING & BASELINE / FATIGUE ANALYSIS
# =============================================================================

def build_time_mask(timestamps, exclude_regions) -> np.ndarray:
    """Boolean 'included' mask, True where a timestamp lies outside every
    exclude region. exclude_regions: iterable of (start_sec, end_sec)."""
    ts = np.asarray(timestamps, dtype=float)
    inc = np.ones(ts.shape, dtype=bool)
    for region in exclude_regions or []:
        if region is None:
            continue
        a, b = region
        if a is None or b is None:
            continue
        lo, hi = (a, b) if a <= b else (b, a)
        inc &= ~((ts >= lo) & (ts < hi))
    return inc

def compute_baseline(ts_df: pd.DataFrame, baseline_window, metrics) -> pd.DataFrame:
    """Per-metric baseline mean/std over the baseline window (intersected with
    the 'included' mask if present). Returns a DataFrame indexed by metric with
    columns ['baseline_mean', 'baseline_std', 'n']."""
    a, b = baseline_window
    lo, hi = (a, b) if a <= b else (b, a)
    m = (ts_df['timestamp'] >= lo) & (ts_df['timestamp'] < hi)
    if 'included' in ts_df.columns:
        m &= ts_df['included']
    present = [c for c in metrics if c in ts_df.columns]
    sub = ts_df.loc[m, present]
    return pd.DataFrame({
        'baseline_mean': sub.mean(),
        'baseline_std':  sub.std(),
        'n':             sub.count(),
    })

def compute_fatigue_curve(ts_df: pd.DataFrame, baseline: pd.DataFrame, metrics,
                          bin_sec: float = 60.0, min_frames: int = 1) -> pd.DataFrame:
    """Per-bin (default per-minute) deviation of each metric from baseline, in the
    metric's own units.

    Returns a tidy DataFrame with columns:
      time_min, metric, mean, delta, pct_change, n
    where delta = bin_mean - baseline_mean (real units, e.g. degrees) and
    pct_change = 100*delta/baseline_mean (guarded when baseline ~ 0). Bins with
    fewer than `min_frames` samples for a metric are dropped so a thin sliver at an
    exclusion boundary or the tail of the session can't produce a wild deviation.
    """
    df = ts_df[ts_df['included']] if 'included' in ts_df.columns else ts_df
    present = [c for c in metrics if c in df.columns]
    if df.empty or not present:
        return pd.DataFrame(columns=['time_min', 'metric', 'mean', 'delta', 'pct_change', 'n'])
    binid = np.floor(df['timestamp'].to_numpy() / bin_sec).astype(int)
    grouped = df.assign(_bin=binid).groupby('_bin')
    means  = grouped[present].mean()
    counts = grouped[present].count()
    rows = []
    for metric in present:
        b_mean = float(baseline.loc[metric, 'baseline_mean']) if metric in baseline.index else float('nan')
        for bin_idx in means.index:
            n = int(counts.loc[bin_idx, metric])
            val = means.loc[bin_idx, metric]
            if n < max(1, min_frames) or not np.isfinite(val):
                continue
            delta = val - b_mean
            pct = 100.0 * delta / b_mean if np.isfinite(b_mean) and abs(b_mean) > 1e-9 else float('nan')
            rows.append({
                'time_min': bin_idx * bin_sec / 60.0,
                'metric': metric, 'mean': float(val),
                'delta': float(delta), 'pct_change': float(pct), 'n': n,
            })
    return pd.DataFrame(rows)

# =============================================================================
# 5. BINARY RECORDING READER
# =============================================================================

_FRAME_HDR_FMT = struct.Struct("dI")   # timestamp (double) + joint count (uint)
_JOINT_FMT     = struct.Struct("Ifffii") # id + x,y,z (float) + px,py (int)

def read_bin(source) -> tuple:
    """Parse a .bin recording produced by recorder.py.

    source: file path (str/Path) or bytes/BytesIO object.
    Returns (metadata: dict, df: pd.DataFrame) where df has columns
    timestamp, joint_N_x, joint_N_y, joint_N_z for each joint present.
    """
    if isinstance(source, (str, os.PathLike)):
        with open(source, "rb") as fh:
            raw = fh.read()
    elif isinstance(source, (bytes, bytearray)):
        raw = source
    else:
        raw = source.read()

    buf = io.BytesIO(raw)

    meta_len = struct.unpack("I", buf.read(4))[0]
    metadata = json.loads(buf.read(meta_len).decode("utf-8"))

    rows = []
    fhdr_size = _FRAME_HDR_FMT.size
    jsize     = _JOINT_FMT.size

    while True:
        hdr_bytes = buf.read(fhdr_size)
        if len(hdr_bytes) < fhdr_size:
            break
        ts, n_joints = _FRAME_HDR_FMT.unpack(hdr_bytes)
        row = {"timestamp": ts}
        for _ in range(n_joints):
            jb = buf.read(jsize)
            if len(jb) < jsize:
                break
            j_id, x, y, z, px, py = _JOINT_FMT.unpack(jb)
            row[f"joint_{j_id}_x"] = x
            row[f"joint_{j_id}_y"] = y
            row[f"joint_{j_id}_z"] = z
            # Raw 2D pixels: depth-independent, the trustworthy sagittal-plane signal
            # for a side-mounted camera (world x,y are scaled by noisy depth).
            row[f"joint_{j_id}_px"] = px
            row[f"joint_{j_id}_py"] = py
        rows.append(row)

    df = pd.DataFrame(rows)
    return metadata, df


def read_csv(source, filename: str = "recording.csv") -> tuple:
    """Parse a CSV recording of joint coordinates.

    The CSV is expected to contain a timestamp column plus joint columns in any
    supported naming convention (joint_N_{x,y,z}, jN_{x,y,z}, or named landmarks
    such as left_knee_x). Returns (metadata: dict, df: pd.DataFrame) matching the
    shape produced by read_bin so the rest of the pipeline is identical.
    """
    if isinstance(source, (bytes, bytearray)):
        source = io.BytesIO(source)
    df = pd.read_csv(source)
    # Normalise a timestamp column so downstream code finds it.
    if 'timestamp' not in df.columns:
        for alt in ('Timestamp', 'time', 'Time', 'time_sec'):
            if alt in df.columns:
                df = df.rename(columns={alt: 'timestamp'})
                break
    n_joints = len(identify_joint_columns(df.columns))
    metadata = {"source": "csv", "filename": filename, "frames": len(df), "joints": n_joints}
    return metadata, df


def load_recording(source, filename: str) -> tuple:
    """Dispatch to the correct reader based on file extension (.bin or .csv)."""
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".csv":
        return read_csv(source, filename)
    return read_bin(source)


