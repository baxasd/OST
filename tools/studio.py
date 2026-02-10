import sys
import os
import pandas as pd
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QStackedWidget,
                             QSpinBox, QCheckBox, QFileDialog, QMessageBox, QFrame, QTextEdit)
from PyQt6.QtCore import QTimer, Qt

# Core Imports
from core import data, metrics, processing
from core.visuals import SkeletonDisplay, MetricGraph

#   PAGE 1: DATA STUDIO
class DataPrepPage(QWidget):
    def __init__(self, parent_app):
        super().__init__()
        self.parent_app = parent_app
        self.raw_df = None
        self.clean_df = None
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # --- LEFT: Log ---
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setStyleSheet("""
            QTextEdit {
                background-color: #212121; 
                color: #ccc; 
                border: none;
                border-right: 1px solid #333;
                font-family: Consolas; 
                font-size: 11px; 
                padding: 20px;}""")
        
        layout.addWidget(self.txt_log, stretch=1)

        # --- RIGHT: Controls ---
        ctrl_panel = QFrame()
        ctrl_panel.setFixedWidth(280)
        ctrl_panel.setStyleSheet("background-color: #2b2b2b;")
        ctrl_lay = QVBoxLayout(ctrl_panel)
        ctrl_lay.setContentsMargins(20, 20, 20, 20)
        ctrl_lay.setSpacing(15)
        ctrl_lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        lbl_h = "color: #bbb; font-weight: bold; font-size: 11px;"
        
        ctrl_lay.addWidget(QLabel("SOURCE DATA", styleSheet=lbl_h))
        self.btn_load = QPushButton("Select File")
        self.btn_load.clicked.connect(self.load_file)
        self.btn_load.setStyleSheet("background-color: #3a3a3a; color: white; padding: 8px; border: 1px solid #444;")
        ctrl_lay.addWidget(self.btn_load)
        
        self.lbl_file = QLabel("No file selected")
        self.lbl_file.setStyleSheet("color: #777; font-size: 10px;")
        ctrl_lay.addWidget(self.lbl_file)
        
        ctrl_lay.addSpacing(10)
        ctrl_lay.addWidget(QLabel("PIPELINE", styleSheet=lbl_h))
        self.chk_repair = QCheckBox("Interpolate Gaps")
        self.chk_repair.setChecked(True)
        self.chk_repair.setStyleSheet("color: #ddd;")
        ctrl_lay.addWidget(self.chk_repair)
        
        smooth_row = QHBoxLayout()
        smooth_row.addWidget(QLabel("Smoothing:", styleSheet="color: #ddd;"))
        self.spn_win = QSpinBox()
        self.spn_win.setRange(3, 51); self.spn_win.setValue(5); self.spn_win.setSingleStep(2)
        self.spn_win.setStyleSheet("background-color: #333; color: white; border: 1px solid #444;")
        smooth_row.addWidget(self.spn_win)
        ctrl_lay.addLayout(smooth_row)
        
        ctrl_lay.addSpacing(10)
        self.btn_process = QPushButton("PROCESS")
        self.btn_process.clicked.connect(self.run_pipeline)
        self.btn_process.setStyleSheet("background-color: #2563eb; color: white; font-weight: bold; padding: 10px; border: none;")
        self.btn_process.setEnabled(False)
        ctrl_lay.addWidget(self.btn_process)
        
        ctrl_lay.addStretch()
        self.btn_export = QPushButton("EXPORT CSV")
        self.btn_export.clicked.connect(self.export_file)
        self.btn_export.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 10px; border: none;")
        self.btn_export.setEnabled(False)
        ctrl_lay.addWidget(self.btn_export)
        
        layout.addWidget(ctrl_panel)

    def log(self, text): self.txt_log.append(text)

    def load_file(self):
        fn, _ = QFileDialog.getOpenFileName(self, "Open CSV", "", "CSV (*.csv)")
        if fn:
            self.txt_log.clear()
            self.log(f"> Loaded: {os.path.basename(fn)}")
            try:
                self.raw_df = pd.read_csv(fn)
                rep = processing.PipelineProcessor.validate(self.raw_df)
                self.log(rep)
                self.lbl_file.setText(os.path.basename(fn))
                self.btn_process.setEnabled(True)
            except Exception as e: self.log(f"Error: {e}")

    def run_pipeline(self):
        if self.raw_df is None: return
        df = self.raw_df.copy()
        self.log("\n> Processing...")
        if self.chk_repair.isChecked(): df = processing.PipelineProcessor.repair(df)
        w = self.spn_win.value()
        if w%2==0: w+=1
        df = processing.PipelineProcessor.smooth(df, window=w)
        self.clean_df = df
        self.log(f"> Done. Frames: {len(df)}")
        self.btn_export.setEnabled(True)
        self.parent_app.load_data_into_viz(self.clean_df)

    def export_file(self):
        if self.clean_df is None: return
        fn, _ = QFileDialog.getSaveFileName(self, "Save", "clean.csv", "CSV (*.csv)")
        if fn:
            self.clean_df.to_csv(fn, index=False)
            self.log(f"> Saved: {fn}")

#   PAGE 2: VISUALIZER
class VisualizerPage(QWidget):
    def __init__(self):
        super().__init__()
        self.active_session = None
        self.frame_idx = 0
        self.playing = False
        self.history = {'lean': [], 'l_knee': [], 'r_knee': []}
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Viewport
        self.viz = SkeletonDisplay()
        layout.addWidget(self.viz, stretch=1)
        
        # Dashboard
        self.dash = QFrame()
        self.dash.setFixedWidth(240) 
        self.dash.setStyleSheet("background-color: #2b2b2b; border-left: 1px solid #333;")
        d_lay = QVBoxLayout(self.dash)
        d_lay.setContentsMargins(15, 20, 15, 20)
        d_lay.setSpacing(5)
        
        # INFO LIST
        d_lay.addWidget(QLabel("SESSION INFO", styleSheet="color: #bbb; font-size: 11px; font-weight: bold; margin-bottom: 5px;"))
        
        self.info_box = QFrame()
        self.info_box.setStyleSheet("background-color: transparent;")
        info_lay = QVBoxLayout(self.info_box)
        info_lay.setSpacing(2)
        info_lay.setContentsMargins(0,0,0,0)
        
        def add_info_row(label, var_name):
            row = QHBoxLayout()
            l = QLabel(label)
            l.setStyleSheet("color: #777; font-size: 11px;")
            v = QLabel("--")
            v.setStyleSheet("color: #eee; font-size: 11px;")
            v.setAlignment(Qt.AlignmentFlag.AlignRight)
            row.addWidget(l)
            row.addWidget(v)
            info_lay.addLayout(row)
            setattr(self, var_name, v)
            
        add_info_row("Subject", "lbl_subj")
        add_info_row("Activity", "lbl_act")
        add_info_row("Date", "lbl_date")
        add_info_row("FPS", "lbl_fps")
        add_info_row("Duration", "lbl_dur")
        add_info_row("Frames", "lbl_frames")
        
        d_lay.addWidget(self.info_box)
        
        d_lay.addSpacing(20)
        line = QFrame(); line.setFixedHeight(1); line.setStyleSheet("background-color: #333;")
        d_lay.addWidget(line)
        d_lay.addSpacing(20)
        
        # GRAPHS
        self.g_lean = MetricGraph("Trunk Lean", "#f59e0b", min_v=-30, max_v=30) # Amber
        self.g_lknee = MetricGraph("L.Knee Flexion", "#e11d48", min_v=0, max_v=180) # Rose
        self.g_rknee = MetricGraph("R.Knee Flexion", "#2563eb", min_v=0, max_v=180) # Blue
        
        d_lay.addWidget(self.g_lean)
        d_lay.addWidget(self.g_lknee)
        d_lay.addWidget(self.g_rknee)
        
        d_lay.addStretch()
        
        # FOOTER
        self.lbl_time = QLabel("00:00")
        self.lbl_time.setStyleSheet("color: #888; font-family: Consolas; font-size: 12px;")
        self.lbl_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        d_lay.addWidget(self.lbl_time)
        
        instr = QLabel("[SPACE] Play/Pause")
        instr.setStyleSheet("color: #555; font-size: 10px;")
        instr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        d_lay.addWidget(instr)
        
        d_lay.addSpacing(10)
        
        # Load Button (Bottom)
        self.btn_load_ext = QPushButton("LOAD RECORDING")
        self.btn_load_ext.clicked.connect(self.load_external)
        self.btn_load_ext.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_load_ext.setStyleSheet("""
            QPushButton { background-color: #3a3a3a; color: #ccc; border: 1px solid #444; border-radius: 4px; padding: 10px; font-weight: bold; font-size: 11px; }
            QPushButton:hover { background-color: #444; color: white; }
        """)
        d_lay.addWidget(self.btn_load_ext)
        
        layout.addWidget(self.dash)
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.loop)

    def load_session(self, session, filename=""):
        self.active_session = session
        self.frame_idx = 0
        self.history = {k: [] for k in self.history}
        
        subj, act = "Unknown", "Unknown"
        if filename:
            parts = os.path.basename(filename).split('_')
            if len(parts) >= 2:
                subj, act = parts[0], parts[1]
        
        self.lbl_subj.setText(subj)
        self.lbl_act.setText(act)
        self.lbl_fps.setText(f"{session.fps:.1f}")
        self.lbl_frames.setText(str(len(session.frames)))
        self.lbl_dur.setText(f"{session.duration:.1f}s")
        self.lbl_date.setText(session.date)

        interval = int(1000 / session.fps) if session.fps > 0 else 33
        self.timer.setInterval(interval)
        
        self.playing = True
        self.timer.start()
        
        if session.frames:
            #  Auto Center Camera on Load
            first_frame = session.frames[0]
            hip = first_frame.joints.get(23) or first_frame.joints.get(24) # Left or Right Hip
            if hip:
                self.viz.center_view(hip.metric[0], -hip.metric[1]) # Invert Y for Graph
            self.viz.update_frame(first_frame)

    def load_external(self):
        fn, _ = QFileDialog.getOpenFileName(self, "Open CSV", "", "CSV (*.csv)")
        if fn:
            try:
                df = pd.read_csv(fn)
                session = data.df_to_session(df)
                self.load_session(session, fn)
            except Exception as e: QMessageBox.critical(self, "Error", str(e))

    def toggle_play(self):
        self.playing = not self.playing
        if self.playing: self.timer.start()
        else: self.timer.stop()
        
    def step(self, delta):
        self.playing = False
        self.timer.stop()
        if not self.active_session: return
        self.frame_idx = (self.frame_idx + delta) % len(self.active_session.frames)
        self.loop(update_idx=False)

    def loop(self, update_idx=True):
        if not self.active_session or not self.active_session.frames: return
        f = self.active_session.frames[self.frame_idx]
        self.viz.update_frame(f)
        
        lean = metrics.calculate_lean_angle(f)
        lk = metrics.calculate_joint_angle(f, "left_hip", "left_knee", "left_ankle")
        rk = metrics.calculate_joint_angle(f, "right_hip", "right_knee", "right_ankle")
        
        self._update_graph(self.g_lean, 'lean', lean)
        self._update_graph(self.g_lknee, 'l_knee', lk)
        self._update_graph(self.g_rknee, 'r_knee', rk)
        
        self.lbl_time.setText(f"{f.timestamp:.1f}s")
        if update_idx:
            self.frame_idx = (self.frame_idx + 1) % len(self.active_session.frames)

    def _update_graph(self, graph, key, val):
        self.history[key].append(val)
        if len(self.history[key]) > 100: self.history[key].pop(0)
        graph.update_data(self.history[key])

#   MAIN WINDOW
class UnifiedWorkstation(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OST Studio")
        self.resize(800, 600)
        self.setStyleSheet("QMainWindow { background-color: #2b2b2b; }")
        
        # Main Layout
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central) # Vertical Stack
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # TOP NAVIGATION BAR
        nav_bar = QFrame()
        nav_bar.setFixedHeight(45)
        nav_bar.setStyleSheet("background-color: #212121; border-bottom: 1px solid #333;")
        nav_lay = QHBoxLayout(nav_bar)
        nav_lay.setContentsMargins(20, 0, 20, 0)
        nav_lay.setSpacing(20)
        
        title = QLabel("OST STUDIO")
        title.setStyleSheet("color: #888; font-weight: 900; font-size: 14px; margin-right: 20px;")
        nav_lay.addWidget(title)
        
        self.btn_prep = self._nav_btn("DATA STUDIO")
        self.btn_viz = self._nav_btn("VISUALIZER")
        
        self.btn_prep.clicked.connect(lambda: self.switch_page(0))
        self.btn_viz.clicked.connect(lambda: self.switch_page(1))
        
        nav_lay.addWidget(self.btn_prep)
        nav_lay.addWidget(self.btn_viz)
        nav_lay.addStretch()
        
        main_layout.addWidget(nav_bar)
        
        # CONTENT
        self.stack = QStackedWidget()
        self.page_prep = DataPrepPage(self)
        self.page_viz = VisualizerPage()
        
        self.stack.addWidget(self.page_prep)
        self.stack.addWidget(self.page_viz)
        
        main_layout.addWidget(self.stack)
        self.switch_page(0)

    def _nav_btn(self, text):
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton { color: #666; font-weight: bold; border: none; font-size: 11px; padding: 12px; }
            QPushButton:hover { color: #aaa; }
            QPushButton:checked { color: white; border-bottom: 2px solid #2563eb; }
        """)
        return btn

    def switch_page(self, index):
        self.stack.setCurrentIndex(index)
        self.btn_prep.setChecked(index == 0)
        self.btn_viz.setChecked(index == 1)

    def switch_to_viz(self):
        self.switch_page(1)

    def load_data_into_viz(self, df):
        session = data.df_to_session(df)
        self.page_viz.load_session(session, "Clean_Data.csv")

    def keyPressEvent(self, event):
        if self.stack.currentIndex() == 1: 
            if event.key() == Qt.Key.Key_Space: self.page_viz.toggle_play()
            elif event.key() == Qt.Key.Key_R: 
                self.page_viz.frame_idx = 0; self.page_viz.loop(update_idx=False)
            elif event.key() == Qt.Key.Key_Left: self.page_viz.step(-1)
            elif event.key() == Qt.Key.Key_Right: self.page_viz.step(1)
        super().keyPressEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = UnifiedWorkstation()
    w.show()
    sys.exit(app.exec())