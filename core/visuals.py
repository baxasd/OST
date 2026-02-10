import pyqtgraph as pg
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel

# Mapping
LM = {
    "nose": 0, "left_shoulder": 11, "right_shoulder": 12,
    "left_elbow": 13, "right_elbow": 14, "left_wrist": 15, "right_wrist": 16,
    "left_hip": 23, "right_hip": 24, "left_knee": 25, "right_knee": 26,
    "left_ankle": 27, "right_ankle": 28
}

BONES_MAP = [
    ("hip_mid", "shoulder_mid"), 
    ("shoulder_mid", "left_shoulder"), ("left_shoulder", "left_elbow"), ("left_elbow", "left_wrist"),
    ("shoulder_mid", "right_shoulder"), ("right_shoulder", "right_elbow"), ("right_elbow", "right_wrist"),
    ("hip_mid", "left_hip"), ("left_hip", "left_knee"), ("left_knee", "left_ankle"),
    ("hip_mid", "right_hip"), ("right_hip", "right_knee"), ("right_knee", "right_ankle"),
    ("shoulder_mid", "nose")
]

class SkeletonDisplay(pg.PlotWidget):
    def __init__(self):
        super().__init__()
        # 1. Scientific Background (Dark Grey, not Black)
        self.setBackground("#1e1e1e") 
        self.setAspectLocked(True)
        self.hideAxis('left')
        self.hideAxis('bottom')
        
        # 2. Grid (Subtle medical style)
        self.addItem(pg.GridItem(pen=pg.mkPen("#333", width=1)))
        
        # 3. Infinite Reference Line
        self.ref_line = pg.InfiniteLine(pos=0, angle=90, pen=pg.mkPen("#555", width=1, style=Qt.PenStyle.DashLine))
        self.addItem(self.ref_line)
        
        self.bones = {}
        # Joints: Matte White, smaller
        self.joints = pg.ScatterPlotItem(size=10, brush=pg.mkBrush("#e5e5e5"), pen=pg.mkPen("#1e1e1e", width=1))
        self.addItem(self.joints)

    def center_view(self, x, y):
        """Centers camera on specific coordinates."""
        self.setRange(xRange=(x-1.0, x+1.0), yRange=(y-1.2, y+1.2), padding=0)

    def _get_pt(self, f, name):
        if name == "hip_mid":
            p1, p2 = f.joints.get(LM["left_hip"]), f.joints.get(LM["right_hip"])
            if p1 and p2: return ((p1.metric[0]+p2.metric[0])/2, (p1.metric[1]+p2.metric[1])/2)
        elif name == "shoulder_mid":
            p1, p2 = f.joints.get(LM["left_shoulder"]), f.joints.get(LM["right_shoulder"])
            if p1 and p2: return ((p1.metric[0]+p2.metric[0])/2, (p1.metric[1]+p2.metric[1])/2)
        else:
            idx = LM.get(name)
            if idx is not None and idx in f.joints:
                return (f.joints[idx].metric[0], f.joints[idx].metric[1])
        return None

    def update_frame(self, f):
        if not f: return
        
        for (n1, n2) in BONES_MAP:
            p1 = self._get_pt(f, n1)
            p2 = self._get_pt(f, n2)
            
            if p1 and p2:
                key = f"{n1}_{n2}"
                
                # 4. Scientific Colors (Muted, Distinct)
                c = "#9ca3af" # Spine: Cool Grey
                if "left" in n1 or "left" in n2: c = "#e11d48" # Left: Muted Rose
                elif "right" in n1 or "right" in n2: c = "#2563eb" # Right: Royal Blue
                
                if key not in self.bones:
                    # Width 4 is standard for scientific vis
                    self.bones[key] = pg.PlotCurveItem(pen=pg.mkPen(c, width=4, cap_style=Qt.PenCapStyle.RoundCap))
                    self.addItem(self.bones[key])
                
                self.bones[key].setData([p1[0], p2[0]], [-p1[1], -p2[1]])

        xs, ys = [], []
        for name in LM:
            p = self._get_pt(f, name)
            if p:
                xs.append(p[0])
                ys.append(-p[1])
        self.joints.setData(xs, ys)

        # Update Infinite Line Position
        hip = self._get_pt(f, "hip_mid")
        if hip:
            self.ref_line.setPos(hip[0])

class MetricGraph(QFrame):
    def __init__(self, title, color, min_v=-180, max_v=180):
        super().__init__()
        # Black Background for Graphs only (High Contrast)
        self.setStyleSheet("background-color: #000; border: 1px solid #333; border-radius: 4px;") 
        self.setFixedHeight(80)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(0)
        
        # Header
        header = QHBoxLayout()
        t_lbl = QLabel(title.upper())
        t_lbl.setStyleSheet("color: #888; font-size: 8px; font-weight: bold; border: none;")
        self.v_lbl = QLabel("--")
        self.v_lbl.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold; border: none;")
        
        header.addWidget(t_lbl)
        header.addStretch()
        header.addWidget(self.v_lbl)
        layout.addLayout(header)
        
        self.plot = pg.PlotWidget()
        self.plot.setBackground(None)
        self.plot.setFrameStyle(QFrame.Shape.NoFrame)
        self.plot.hideAxis('bottom')
        self.plot.hideAxis('left')
        self.plot.setMouseEnabled(x=False, y=False)
        self.plot.setYRange(min_v, max_v)
        
        self.plot.addItem(pg.InfiniteLine(pos=0, angle=0, pen=pg.mkPen('#333', width=1, style=Qt.PenStyle.DashLine)))
        
        self.curve = self.plot.plot(pen=pg.mkPen(color, width=2))
        layout.addWidget(self.plot)

    def update_data(self, data_list):
        if not data_list: return
        self.curve.setData(data_list)
        self.v_lbl.setText(f"{int(data_list[-1])}°")