from PyQt6.QtWidgets import QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel
from core.config import *

class MetricGraph(QWidget):
    """Compact line graph for Studio Dashboard. Lazy-loads pyqtgraph."""
    def __init__(self, title, color, min_v=0, max_v=180):
        super().__init__()
        
        # Lazy import to ensure fast application startup
        import pyqtgraph as pg 
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 15) 
        layout.setSpacing(4)
        
        header = QHBoxLayout()
        t_lbl = QLabel(title.upper())
        t_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 9px; font-weight: bold; border: none;")
        self.v_lbl = QLabel("--")
        self.v_lbl.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: bold; border: none;")
        
        header.addWidget(t_lbl)
        header.addStretch()
        header.addWidget(self.v_lbl)
        layout.addLayout(header)
        
        self.box = QFrame()
        self.box.setFixedHeight(80) 
        self.box.setStyleSheet(f"background-color: {BG_DARK}; border: 1px solid {BORDER}; border-radius: 4px;")
        box_lay = QVBoxLayout(self.box)
        box_lay.setContentsMargins(0, 0, 0, 0)
        
        self.plot = pg.PlotWidget()
        self.plot.setBackground(None)
        self.plot.hideAxis('bottom')
        self.plot.hideAxis('left')
        self.plot.showGrid(x=True, y=True, alpha=0.2)
        self.plot.setMouseEnabled(x=False, y=False)
        self.plot.setYRange(min_v, max_v, padding=0.1)
        
        self.curve = self.plot.plot(pen=pg.mkPen(color, width=2))
        box_lay.addWidget(self.plot)
        layout.addWidget(self.box)

    def update_data(self, data_list):
        if not data_list: 
            return
        self.curve.setData(data_list)
        self.v_lbl.setText(f"{int(data_list[-1])}°")


class SkeletonLegend(QFrame):
    """Simple color legend for the 3D visualizer."""
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"border: none; background: transparent;")
        l = QHBoxLayout(self)
        l.setContentsMargins(0, 5, 0, 15)
        
        def add_item(name, color):
            box = QLabel()
            box.setFixedSize(10, 10)
            box.setStyleSheet(f"background-color: {color}; border-radius: 2px; border: none;")
            txt = QLabel(name)
            txt.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px; border: none;")
            l.addWidget(box)
            l.addWidget(txt)
            l.addSpacing(10)
            
        add_item("Left", COLOR_BONE_LEFT)
        add_item("Right", COLOR_BONE_RIGHT)
        add_item("Center", COLOR_BONE_CENTER)
        l.addStretch()