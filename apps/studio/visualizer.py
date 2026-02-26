from PyQt6.QtWidgets import *
from PyQt6.QtCore import QTimer, Qt

from core import data, storage, math
from core.config import *
from core.widgets import MetricGraph, SkeletonLegend

class VisualizerPage(QWidget):
    def __init__(self, parent_app):
        super().__init__()
        self.parent_app = parent_app
        self.active_session = None
        self.frame_idx = 0
        self.playing = False
        
        self.keys = [cfg[0] for cfg in METRIC_CONFIGS]
        self.history = {k: [] for k in self.keys}
        self.graphs = {}
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.loading_lbl = QLabel("Initializing Graphics Engine...")
        self.loading_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_lbl.setStyleSheet(f"color: {TEXT_DIM};")
        self.layout.addWidget(self.loading_lbl)
        
        self.viz = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.loop)
        self.is_initialized = False

    def init_graphics(self):
        if self.is_initialized: return
            
        from core.render import SkeletonDisplay
        
        self.loading_lbl.setParent(None)
        self.viz = SkeletonDisplay()
        self.layout.addWidget(self.viz, stretch=1)
        
        # Panel & Controls
        dash_container = QWidget()
        dash_container.setFixedWidth(PANEL_WIDTH)
        dash_container.setStyleSheet(CSS_SIDEBAR)
        dash_layout = QVBoxLayout(dash_container)
        dash_layout.setContentsMargins(0, 0, 0, 0)
        dash_layout.setSpacing(0)
        
        # Scrollable area for info & graphs
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(CSS_SIDEBAR + "margin: 0px; padding: 0px;")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet(f"background-color: {BG_PANEL}; border: none;")
        self.grid = QGridLayout(scroll_content)
        self.grid.setContentsMargins(20, 20, 20, 20)
        self.grid.setSpacing(10)
        
        self.info_box_widget = QWidget()
        info_lay = QVBoxLayout(self.info_box_widget)
        info_lay.setContentsMargins(0, 0, 0, 0)
        info_lay.addWidget(QLabel("SESSION INFO", styleSheet=CSS_HEADER))
        self.info_vals = {}
        
        # Info rows after Header
        def add_info(lbl, key):
            row = QHBoxLayout()
            l = QLabel(lbl)
            l.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px; border: none; background: transparent; ")
            v = QLabel("--")
            v.setStyleSheet(f"color: {TEXT_MAIN}; font-size: 10px; font-weight: bold; border: none; background: transparent;")
            row.addWidget(l)
            row.addStretch()
            row.addWidget(v)
            info_lay.addLayout(row)
            self.info_vals[key] = v
            
        add_info("Subject", "lbl_subj")
        add_info("Activity", "lbl_act")
        add_info("FPS", "lbl_fps")
        add_info("Frames", "lbl_frames")
        add_info("Time", "lbl_time")
        
        self.grid.addWidget(self.info_box_widget, 0, 0, 1, 2)
        self.grid.addWidget(SkeletonLegend(), 1, 0, 1, 2)
        
        row_idx = 2
        for i in range(0, len(METRIC_CONFIGS), 2):
            for col_idx in range(2):
                if i + col_idx < len(METRIC_CONFIGS):
                    key, title, color, min_v, max_v = METRIC_CONFIGS[i + col_idx]
                    graph = MetricGraph(title, color, min_v, max_v)
                    self.graphs[key] = graph
                    self.grid.addWidget(graph, row_idx, col_idx)
            row_idx += 1
        
        scroll.setWidget(scroll_content)
        dash_layout.addWidget(scroll)
        
        footer = QFrame()
        footer.setStyleSheet(CSS_SIDEBAR)
        f_lay = QVBoxLayout(footer)
        f_lay.setContentsMargins(10, 10, 10, 10)
        
        self.btn_load_ext = QPushButton("LOAD DATA")
        self.btn_load_ext.clicked.connect(self.load_external)
        self.btn_load_ext.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_load_ext.setStyleSheet(CSS_BTN_PRIMARY)
    
        f_lay.addWidget(self.btn_load_ext)
        
        dash_layout.addWidget(footer)
        self.layout.addWidget(dash_container)
        self.is_initialized = True

    def load_session(self, session, filename="", subj="Unknown", act="Unknown"):
        if not self.is_initialized: return
        
        self.active_session = session
        self.frame_idx = 0
        self.history = {k: [] for k in self.keys}
        
        self.info_vals['lbl_subj'].setText(subj)
        self.info_vals['lbl_act'].setText(act)
        self.info_vals['lbl_fps'].setText(f"{session.fps:.1f}")
        self.info_vals['lbl_frames'].setText(str(len(session.frames)))
        
        self.viz.update_frame(None) 
        interval = int(1000 / session.fps) if session.fps > 0 else 33
        self.timer.setInterval(interval)
        self.playing = True
        self.timer.start()
        
        if session.frames:
            first_frame = session.frames[0]
            from core import math
            hip = math.get_point(first_frame, "hip_mid")
            if hip: 
                self.viz.center_view(hip[0], -hip[1]) 
            self.viz.update_frame(first_frame)

    def load_external(self):
        fn, _ = QFileDialog.getOpenFileName(self, "Open Cleaned Data", "", "Data Files (*.parquet *.csv)")
        if fn:
            try:
                df, subj, act = storage.load_session_data(fn)
                session = data.df_to_session(df)
                self.load_session(session, fn, subj, act)
            except Exception as e: 
                QMessageBox.critical(self, "Error", str(e))

    def trigger_analysis(self):
        if not self.active_session: return
        self.parent_app.run_fatigue_analysis()

    def toggle_play(self):
        if not self.is_initialized: return
        self.playing = not self.playing
        if self.playing: self.timer.start()
        else: self.timer.stop()
        
    def step(self, delta):
        if not self.is_initialized: return
        self.playing = False
        self.timer.stop()
        if not self.active_session: return
        self.frame_idx = (self.frame_idx + delta) % len(self.active_session.frames)
        self.loop(update_idx=False)

    def loop(self, update_idx=True):
        if not self.active_session or not self.active_session.frames: return
            
        f = self.active_session.frames[self.frame_idx]
        self.viz.update_frame(f)
        vals = math.compute_all_metrics(f)

        for key in self.keys:
            if key in vals and key in self.graphs:
                self.history[key].append(vals[key])
                if len(self.history[key]) > MAX_HISTORY_LENGTH: 
                    self.history[key].pop(0)
                self.graphs[key].update_data(self.history[key])
        
        # Updates time Label
        self.info_vals['lbl_time'].setText(f"{f.timestamp:.1f}s")
        if update_idx: 
            self.frame_idx = (self.frame_idx + 1) % len(self.active_session.frames)
