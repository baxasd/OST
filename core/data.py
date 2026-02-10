# ost/core/data.py
from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional

@dataclass
class Joint:
    """Represents a single skeletal joint."""
    pixel: Tuple[int, int]  # (x, y) in image coordinates
    metric: Tuple[float, float, float]  # (x, y, z) in meters (real world)
    visibility: float = 1.0

@dataclass
class Frame:
    """Represents a single captured moment."""
    timestamp: float
    frame_id: int
    joints: Dict[int, Joint] = field(default_factory=dict) # Key is Mediapipe index (0-32)