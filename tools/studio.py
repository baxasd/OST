import sys
import os
import pandas as pd
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QPushButton, QLabel, QStackedWidget,
                             QSpinBox, QCheckBox, QFileDialog, QMessageBox, QFrame, QTextEdit, QScrollArea)
from PyQt6.QtCore import QTimer, Qt
import pyqtgraph as pg 

# Core Imports
from core import data, metrics, processing, io
from core.visuals import SkeletonDisplay
# Import Settings (Colors, Dimensions)
from core.settings import *

# =============================================================================
#   PAGE 1: DATA STUDIO (Import, Clean, Export)
# =============================================================================
class DataPrepPage(QWidget):
    def __init__(self, parent_app):
        super().__init__()
        self.parent_app = parent_app
        self.raw_df = None
        self.clean_df = None
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # --- LEFT PANEL: Processing Log ---
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setStyleSheet(f"""
            QTextEdit {{
                background-color: {BG_DARK}; 
                color: {TEXT_DIM}; 
                border: none;
                border-right: 1px solid {BORDER};
                font-family: Consolas; 
                font-size: 11px; 
                padding: 20px;
            }}""")
        
        layout.addWidget(self.txt_log, stretch=1)

        # --- RIGHT PANEL: Controls ---
        ctrl_panel = QFrame()
        ctrl_panel.setFixedWidth(PANEL_WIDTH)
        ctrl_panel.setStyleSheet(f"background-color: {BG_PANEL}; border-left: 1px solid {BORDER};")
        ctrl_lay = QVBoxLayout(ctrl_panel)
        ctrl_lay.setContentsMargins(20, 20, 20, 20)
        ctrl_lay.setSpacing(15)
        ctrl_lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Label Style
        lbl_h = f"color: {TEXT_MAIN}; font-weight: bold; font-size: 11px; margin-bottom: 2px; border: none;"
        
        # 1. Source Data Section
        ctrl_lay.addWidget(QLabel("SOURCE DATA", styleSheet=lbl_h))
        self.btn_load = QPushButton("Select File")
        self.btn_load.clicked.connect(self.load_file)
        self.btn_load.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_load.setStyleSheet(f"""
            QPushButton {{ background-color: {ACCENT_COLOR}; color: white; padding: 10px; border: 1px solid {BORDER}; border-radius: 4px; }}
            QPushButton:hover {{ background-color: {ACCENT_HOVER}; border-color: {TEXT_DIM}; }}
        """)
        ctrl_lay.addWidget(self.btn_load)
        
        self.lbl_file = QLabel("No file selected")
        self.lbl_file.setStyleSheet(f"color: {ACCENT_COLOR}; font-size: 10px; font-style: italic; border: none;")
        ctrl_lay.addWidget(self.lbl_file)
        
        ctrl_lay.addSpacing(15)
        line = QFrame(); line.setFixedHeight(1); line.setStyleSheet(f"background-color: {BORDER}; border: none;")
        ctrl_lay.addWidget(line)
        ctrl_lay.addSpacing(15)

        # 2. Pipeline Section
        ctrl_lay.addWidget(QLabel("PROCESSING OPTIONS", styleSheet=lbl_h))
        
        # Checkbox: Repair
        self.chk_repair = QCheckBox("Interpolate Gaps")
        self.chk_repair.setChecked(True)
        self.chk_repair.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_repair.setStyleSheet(f"""
            QCheckBox {{ color: {TEXT_DIM}; spacing: 8px; border: none; }}
            QCheckBox::indicator {{ width: 14px; height: 14px; border: 1px solid #666; border-radius: 2px; background: transparent; }}
            QCheckBox::indicator:checked {{ background-color: {ACCENT_COLOR}; border-color: {ACCENT_COLOR}; }}
        """)
        ctrl_lay.addWidget(self.chk_repair)
        
        # Smoothing Window Control
        smooth_row = QHBoxLayout()
        lbl_smooth = QLabel("Smoothing Window:")
        lbl_smooth.setStyleSheet(f"color: {TEXT_DIM}; border: none;")
        
        self.spn_win = QSpinBox()
        self.spn_win.setRange(3, 51); self.spn_win.setValue(5); self.spn_win.setSingleStep(2)
        self.spn_win.setStyleSheet(f"""
            QSpinBox {{ background-color: #18181b; color: white; border: 1px solid {BORDER}; padding: 4px; border-radius: 4px; }}
            QSpinBox:focus {{ border: 1px solid {ACCENT_COLOR}; }}
        """)
        
        smooth_row.addWidget(lbl_smooth)
        smooth_row.addWidget(self.spn_win)
        ctrl_lay.addLayout(smooth_row)
        
        ctrl_lay.addSpacing(10)
        
        # Run Button
        self.btn_process = QPushButton("Cleanup")
        self.btn_process.clicked.connect(self.run_pipeline)
        self.btn_process.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_process.setStyleSheet(f"""
            QPushButton {{ background-color: {ACCENT_COLOR}; color: {BG_DARK}; font-weight: bold; padding: 12px; border: none; border-radius: 4px; }}
            QPushButton:hover {{ background-color: {ACCENT_HOVER}; }}
            QPushButton:disabled {{ background-color: #3f3f46; color: #71717a; }}
        """)
        self.btn_process.setEnabled(False)
        ctrl_lay.addWidget(self.btn_process)
        
        ctrl_lay.addStretch()
        
        # Export Button
        self.btn_export = QPushButton("EXPORT CSV")
        self.btn_export.clicked.connect(self.export_file)
        self.btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export.setStyleSheet(f"""
            QPushButton {{ background-color: transparent; color: {TEXT_DIM}; border: 1px solid {BORDER}; padding: 10px; border-radius: 4px; }}
            QPushButton:hover {{ border-color: {ACCENT_COLOR}; color: {ACCENT_COLOR}; }}
            QPushButton:disabled {{ border-color: #333; color: #333; }}
        """)
        self.btn_export.setEnabled(False)
        ctrl_lay.addWidget(self.btn_export)
        
        layout.addWidget(ctrl_panel)

    def log(self, text): self.txt_log.append(str(text))

    def load_file(self):
        fn, _ = QFileDialog.getOpenFileName(self, "Open CSV", "", "CSV (*.csv)")
        if fn:
            self.txt_log.clear()
            self.log(f"> Loaded: {os.path.basename(fn)}")
            try:
                self.raw_df = pd.read_csv(fn)
                report, needs_repair = processing.PipelineProcessor.validate(self.raw_df)
                self.log(report)
                
                if needs_repair:
                    self.chk_repair.setChecked(True)
                    self.log(">> Auto-enabled repair based on validation.")
                
                self.lbl_file.setText(os.path.basename(fn))
                self.btn_process.setEnabled(True)
            except Exception as e: self.log(f"Error: {e}")

    def run_pipeline(self):
        if self.raw_df is None: return
        df = self.raw_df.copy()
        self.log("\n> Processing...")
        
        # 1. Repair Gaps
        if self.chk_repair.isChecked(): 
            df = processing.PipelineProcessor.repair(df)
            self.log("• Gaps interpolated")
            
        # 2. Smooth Data
        w = self.spn_win.value()
        if w%2==0: w+=1
        df = processing.PipelineProcessor.smooth(df, window=w)
        self.log(f"• Smoothed (window={w})")
        
        self.clean_df = df
        self.log(f"> Done. Frames: {len(df)}")
        self.btn_export.setEnabled(True)
        self.parent_app.load_data_into_viz(self.clean_df)
        
        # Ask to switch tabs
        reply = QMessageBox.question(self, "Processing Complete", 
                                     "Data processed successfully.\nSwitch to Visualizer tab?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.parent_app.switch_to_viz()

    def export_file(self):
        if self.clean_df is None: return
        fn, _ = QFileDialog.getSaveFileName(self, "Save", "clean.csv", "CSV (*.csv)")
        if fn:
            success, msg = io.export_clean_csv(self.clean_df, fn)
            self.log(f"> {msg}")


# =============================================================================
#   CUSTOM UI WIDGETS (Graphs & Legends)
# =============================================================================

class MetricGraph(QWidget):
    """
    Compact line graph with fixed scale, no axis numbers, and clean aesthetic.
    """
    def __init__(self, title, color, min_v=0, max_v=180):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 15) # Spacing below widget
        layout.setSpacing(4)
        
        # Header Row (Title & Value)
        header = QHBoxLayout()
        t_lbl = QLabel(title.upper())
        t_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 9px; font-weight: bold; border: none;")
        self.v_lbl = QLabel("--")
        self.v_lbl.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: bold; border: none;")
        
        header.addWidget(t_lbl)
        header.addStretch()
        header.addWidget(self.v_lbl)
        layout.addLayout(header)
        
        # Graph Container
        self.box = QFrame()
        self.box.setFixedHeight(80) 
        self.box.setStyleSheet(f"background-color: {BG_DARK}; border: 1px solid {BORDER}; border-radius: 4px;")
        box_lay = QVBoxLayout(self.box)
        box_lay.setContentsMargins(0, 0, 0, 0)
        
        self.plot = pg.PlotWidget()
        self.plot.setBackground(None)
        
        # Clean up Plot: Hide axes, show faint grid
        self.plot.hideAxis('bottom')
        self.plot.hideAxis('left')
        self.plot.showGrid(x=True, y=True, alpha=0.2)
        self.plot.setMouseEnabled(x=False, y=False)
        
        # Fixed Range (No Auto-Scaling)
        self.plot.setYRange(min_v, max_v, padding=0.1)
        
        # Line Curve
        self.curve = self.plot.plot(pen=pg.mkPen(color, width=2))
        
        box_lay.addWidget(self.plot)
        layout.addWidget(self.box)

    def update_data(self, data_list):
        if not data_list: return
        self.curve.setData(data_list)
        self.v_lbl.setText(f"{int(data_list[-1])}°")

class SkeletonLegend(QFrame):
    """
    Simple legend to explain the bone colors.
    """
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


# =============================================================================
#   PAGE 2: VISUALIZER (Playback & Metrics)
# =============================================================================
class VisualizerPage(QWidget):
    def __init__(self):
        super().__init__()
        self.active_session = None
        self.frame_idx = 0
        self.playing = False
        
        # Metrics History
        self.keys = ['lean_x', 'lean_z', 
                     'l_knee', 'r_knee', 
                     'l_hip', 'r_hip', 
                     'l_sho', 'r_sho', 
                     'l_elb', 'r_elb']
        self.history = {k: [] for k in self.keys}
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # --- LEFT: 3D Skeleton Viewport ---
        self.viz = SkeletonDisplay()
        layout.addWidget(self.viz, stretch=1)
        
        # --- RIGHT: Dashboard ---
        dash_container = QWidget()
        dash_container.setFixedWidth(PANEL_WIDTH)
        # Only Left Border
        dash_container.setStyleSheet(f"background-color: {BG_PANEL}; border: none; border-left: 1px solid {BORDER};")
        
        dash_layout = QVBoxLayout(dash_container)
        dash_layout.setContentsMargins(0, 0, 0, 0)
        
        # Scrollable Content Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; } QScrollBar { width: 8px; background: #222; }")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet(f"background-color: {BG_PANEL}; border: none;")
        
        self.grid = QGridLayout(scroll_content)
        self.grid.setContentsMargins(15, 20, 15, 20)
        self.grid.setSpacing(10)
        
        # 1. Info Header
        self.info_box_widget = QWidget()
        info_lay = QVBoxLayout(self.info_box_widget)
        info_lay.setContentsMargins(0,0,0,10)
        info_lay.addWidget(QLabel("SESSION INFO", styleSheet=f"color: {ACCENT_COLOR}; font-size: 11px; font-weight: bold; margin-bottom: 5px; border: none;"))
        
        self.info_vals = {}
        def add_info(lbl, key):
            row = QHBoxLayout()
            l = QLabel(lbl)
            l.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px; border: none; background: transparent;")
            v = QLabel("--")
            v.setStyleSheet(f"color: {TEXT_MAIN}; font-size: 11px; font-weight: bold; border: none; background: transparent;")
            row.addWidget(l); row.addStretch(); row.addWidget(v)
            info_lay.addLayout(row)
            self.info_vals[key] = v
            
        add_info("Subject", "lbl_subj")
        add_info("Activity", "lbl_act")
        add_info("FPS", "lbl_fps")
        add_info("Frames", "lbl_frames")
        
        self.grid.addWidget(self.info_box_widget, 0, 0, 1, 2)
        
        # 2. Legend
        self.grid.addWidget(SkeletonLegend(), 1, 0, 1, 2)
        
        # 3. Graphs (Grid Layout)
        
        # Row 2: Trunk Leans
        self.g_lean_x = MetricGraph("Trunk Lat.", GRAPH_CENTER, -45, 45)
        self.g_lean_z = MetricGraph("Trunk Depth", GRAPH_Z_AXIS, -45, 45)
        self.grid.addWidget(self.g_lean_x, 2, 0)
        self.grid.addWidget(self.g_lean_z, 2, 1)
        
        # Row 3: Knees
        self.g_lknee = MetricGraph("L.Knee Flex", GRAPH_LEFT, 0, 180)
        self.g_rknee = MetricGraph("R.Knee Flex", GRAPH_RIGHT, 0, 180)
        self.grid.addWidget(self.g_lknee, 3, 0)
        self.grid.addWidget(self.g_rknee, 3, 1)
        
        # Row 4: Hips
        self.g_lhip = MetricGraph("L.Hip Flex", GRAPH_LEFT, 0, 180)
        self.g_rhip = MetricGraph("R.Hip Flex", GRAPH_RIGHT, 0, 180)
        self.grid.addWidget(self.g_lhip, 4, 0)
        self.grid.addWidget(self.g_rhip, 4, 1)
        
        # Row 5: Shoulders
        self.g_lsho = MetricGraph("L.Shoulder Flex", GRAPH_LEFT, 0, 180)
        self.g_rsho = MetricGraph("R.Shoulder Flex", GRAPH_RIGHT, 0, 180)
        self.grid.addWidget(self.g_lsho, 5, 0)
        self.grid.addWidget(self.g_rsho, 5, 1)
        
        # Row 6: Elbows
        self.g_lelb = MetricGraph("L.Elbow Flex", GRAPH_LEFT, 0, 180)
        self.g_relb = MetricGraph("R.Elbow Flex", GRAPH_RIGHT, 0, 180)
        self.grid.addWidget(self.g_lelb, 6, 0)
        self.grid.addWidget(self.g_relb, 6, 1)
        
        # Spacer
        self.grid.setRowStretch(7, 1)

        scroll.setWidget(scroll_content)
        dash_layout.addWidget(scroll)
        
        # --- FOOTER ---
        footer = QFrame()
        footer.setStyleSheet(f"background-color: {BG_PANEL}; border-top: 1px solid {BORDER}; border-left: none; border-right: none; border-bottom: none;")
        f_lay = QVBoxLayout(footer)
        f_lay.setContentsMargins(10, 10, 10, 10)
        
        self.lbl_time = QLabel("00:00")
        self.lbl_time.setStyleSheet(f"color: {TEXT_MAIN}; font-family: Consolas; font-size: 14px; font-weight: bold; border: none;")
        self.lbl_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        f_lay.addWidget(self.lbl_time)
        
        instr = QLabel("[SPACE] Play/Pause")
        instr.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px; border: none;")
        instr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        f_lay.addWidget(instr)
        
        # Load Recording Button (Accent Color)
        self.btn_load_ext = QPushButton("LOAD RECORDING")
        self.btn_load_ext.clicked.connect(self.load_external)
        self.btn_load_ext.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_load_ext.setStyleSheet(f"""
            QPushButton {{ background-color: {ACCENT_COLOR}; color: {BG_DARK}; border: none; border-radius: 4px; padding: 12px; font-weight: bold; font-size: 11px; }}
            QPushButton:hover {{ background-color: {ACCENT_HOVER}; }}
        """)
        f_lay.addWidget(self.btn_load_ext)
        
        dash_layout.addWidget(footer)
        layout.addWidget(dash_container)
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.loop)

    def load_session(self, session, filename=""):
        self.active_session = session
        self.frame_idx = 0
        self.history = {k: [] for k in self.keys}
        
        subj, act = "Unknown", "Unknown"
        if filename:
            parts = os.path.basename(filename).split('_')
            if len(parts) >= 2:
                subj, act = parts[0], parts[1]
        
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
            hip = metrics.get_point(first_frame, "hip_mid")
            if hip:
                self.viz.center_view(hip[0], -hip[1]) 
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
        
        # Calculate all metrics using centralized logic
        vals = metrics.compute_all_metrics(f)

        # Update Graphs
        self._update_graph(self.g_lean_x, 'lean_x', vals['lean_x'])
        self._update_graph(self.g_lean_z, 'lean_z', vals['lean_z'])
        
        self._update_graph(self.g_lknee, 'l_knee', vals['l_knee'])
        self._update_graph(self.g_rknee, 'r_knee', vals['r_knee'])
        
        self._update_graph(self.g_lhip, 'l_hip', vals['l_hip'])
        self._update_graph(self.g_rhip, 'r_hip', vals['r_hip'])
        
        self._update_graph(self.g_lsho, 'l_sho', vals['l_sho'])
        self._update_graph(self.g_rsho, 'r_sho', vals['r_sho'])
        
        self._update_graph(self.g_lelb, 'l_elb', vals['l_elb'])
        self._update_graph(self.g_relb, 'r_elb', vals['r_elb'])
        
        self.lbl_time.setText(f"{f.timestamp:.1f}s")
        if update_idx:
            self.frame_idx = (self.frame_idx + 1) % len(self.active_session.frames)

    def _update_graph(self, graph, key, val):
        self.history[key].append(val)
        if len(self.history[key]) > 100: self.history[key].pop(0)
        graph.update_data(self.history[key])


# =============================================================================
#   MAIN APPLICATION WINDOW
# =============================================================================
class UnifiedWorkstation(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OST Studio")
        # Compact Window Dimensions from Settings
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setStyleSheet(f"QMainWindow {{ background-color: {BG_DARK}; }}")
        
        # Main Layout
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central) 
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # TOP NAVIGATION BAR
        nav_bar = QFrame()
        nav_bar.setFixedHeight(50)
        nav_bar.setStyleSheet(f"background-color: {BG_DARK}; border-bottom: 1px solid {BORDER}; padding-bottom: 2px;")
        nav_lay = QHBoxLayout(nav_bar)
        nav_lay.setContentsMargins(20, 0, 20, 0)
        nav_lay.setSpacing(20)
        
        title = QLabel("OST STUDIO")
        title.setStyleSheet(f"color: {ACCENT_COLOR}; font-weight: 900; font-size: 16px; margin-right: 20px; border: none;")
        nav_lay.addWidget(title)
        
        self.btn_prep = self._nav_btn("DATA STUDIO")
        self.btn_viz = self._nav_btn("VISUALIZER")
        
        self.btn_prep.clicked.connect(lambda: self.switch_page(0))
        self.btn_viz.clicked.connect(lambda: self.switch_page(1))
        
        nav_lay.addWidget(self.btn_prep)
        nav_lay.addWidget(self.btn_viz)
        nav_lay.addStretch()
        
        main_layout.addWidget(nav_bar)
        
        # STACKED PAGES
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
        btn.setStyleSheet(f"""
            QPushButton {{ color: {TEXT_DIM}; font-weight: bold; border: none; font-size: 12px; padding: 0 10px; height: 48px; }}
            QPushButton:hover {{ color: {TEXT_MAIN}; }}
            QPushButton:checked {{ color: {ACCENT_COLOR}; border-bottom: 2px solid {ACCENT_COLOR}; }}
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