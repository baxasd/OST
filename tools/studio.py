import sys
import os
import traceback

from PyQt6.QtWidgets import *
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QIcon

from core import storage
from core.config import *
from core import data
from core.widgets import MetricGraph, SkeletonLegend


class DataPrepPage(QWidget):
    def __init__(self, parent_app):
        super().__init__()
        self.parent_app = parent_app
        self.raw_df = None
        self.clean_df = None
        self.current_subj = "Unknown"
        self.current_act = "Unknown"
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        left_panel = QSplitter(Qt.Orientation.Vertical)
        
        self.graph_container = QFrame()
        self.graph_container.setStyleSheet(f"background-color: {BG_DARK}; border: none;")
        self.graph_layout = QVBoxLayout(self.graph_container)
        self.graph_layout.setContentsMargins(0, 0, 0, 0)
        
        self.plot_widget = None
        self.raw_curve = None
        self.clean_curve = None

        left_panel.addWidget(self.graph_container)

        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setStyleSheet(f"background-color: #0d0d0f; color: {TEXT_DIM}; border: none; border-top: 1px solid {BORDER}; border-right: 1px solid {BORDER}; font-family: Consolas; font-size: 11px; padding: 10px;")
        
        left_panel.addWidget(self.txt_log)
        left_panel.setSizes([600, 200])
        layout.addWidget(left_panel, stretch=1)

        ctrl_panel = QFrame()
        ctrl_panel.setFixedWidth(PANEL_WIDTH + 40)
        ctrl_panel.setStyleSheet(CSS_SIDEBAR)
        ctrl_lay = QVBoxLayout(ctrl_panel)
        ctrl_lay.setContentsMargins(20, 20, 20, 20)
        ctrl_lay.setSpacing(15)
        ctrl_lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        ctrl_lay.addWidget(QLabel("1. DATA SOURCE", styleSheet=CSS_HEADER))
        self.btn_load = QPushButton("Select File")
        self.btn_load.clicked.connect(self.load_file)
        self.btn_load.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_load.setStyleSheet(CSS_BTN_PRIMARY)
        ctrl_lay.addWidget(self.btn_load)
        
        self.lbl_file = QLabel("No file selected")
        self.lbl_file.setStyleSheet(f"color: {ACCENT_COLOR}; font-size: 10px; font-style: italic; border: none;")
        ctrl_lay.addWidget(self.lbl_file)
        
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background-color: {BORDER};")
        ctrl_lay.addWidget(line)

        ctrl_lay.addWidget(QLabel("2. PLOT PREVIEW", styleSheet=CSS_HEADER))
        self.cmb_joint = QComboBox()
        self.cmb_joint.setStyleSheet(CSS_INPUT)
        self.cmb_joint.currentIndexChanged.connect(self.update_graph)
        ctrl_lay.addWidget(self.cmb_joint)
        
        legend_lay = QHBoxLayout()
        legend_lay.setContentsMargins(0, 0, 0, 0)
        
        def add_legend_item(text, color, dotted=False):
            box = QLabel()
            box.setFixedSize(14, 4)
            if dotted: 
                box.setStyleSheet(f"border-top: 2px dotted {color}; background: transparent;")
            else: 
                box.setStyleSheet(f"background-color: {color};")
            lbl = QLabel(text)
            lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px; border: none;")
            legend_lay.addWidget(box)
            legend_lay.addWidget(lbl)

        add_legend_item("Raw", "#ff5555", dotted=True)
        legend_lay.addStretch()
        add_legend_item("Clean", "#55ff55")
        ctrl_lay.addLayout(legend_lay)

        line2 = QFrame()
        line2.setFixedHeight(1)
        line2.setStyleSheet(f"background-color: {BORDER};")
        ctrl_lay.addWidget(line2)

        ctrl_lay.addWidget(QLabel("3. CLEANING PIPELINE", styleSheet=CSS_HEADER))
        
        self.chk_teleport = QCheckBox("Remove Joint Teleportation")
        self.chk_teleport.setChecked(True)
        self.chk_teleport.setStyleSheet(f"color: {TEXT_DIM}; border: none;")
        ctrl_lay.addWidget(self.chk_teleport)
        
        tele_lay = QHBoxLayout()
        tele_lay.addWidget(QLabel("Distance Threshold:", styleSheet=f"color: {TEXT_DIM}; border: none;"))
        self.spn_tele_thresh = QDoubleSpinBox()
        self.spn_tele_thresh.setRange(0.01, 10.0)
        self.spn_tele_thresh.setValue(0.5)
        self.spn_tele_thresh.setSingleStep(0.1)
        self.spn_tele_thresh.setStyleSheet(CSS_INPUT)
        tele_lay.addWidget(self.spn_tele_thresh)
        ctrl_lay.addLayout(tele_lay)

        self.chk_repair = QCheckBox("Interpolate Missing/Dropped Data")
        self.chk_repair.setChecked(True)
        self.chk_repair.setStyleSheet(f"color: {TEXT_DIM}; border: none; margin-top: 5px;")
        ctrl_lay.addWidget(self.chk_repair)

        self.chk_smooth = QCheckBox("Apply Moving Average")
        self.chk_smooth.setChecked(True)
        self.chk_smooth.setStyleSheet(f"color: {TEXT_DIM}; border: none; margin-top: 5px;")
        ctrl_lay.addWidget(self.chk_smooth)

        smooth_lay = QHBoxLayout()
        smooth_lay.addWidget(QLabel("Window Size:", styleSheet=f"color: {TEXT_DIM}; border: none;"))
        self.spn_win = QSpinBox()
        self.spn_win.setRange(3, 101)
        self.spn_win.setValue(5)
        self.spn_win.setSingleStep(2)
        self.spn_win.setStyleSheet(CSS_INPUT)
        smooth_lay.addWidget(self.spn_win)
        ctrl_lay.addLayout(smooth_lay)

        ctrl_lay.addSpacing(15)
        self.btn_preview = QPushButton("RUN PREVIEW")
        self.btn_preview.clicked.connect(self.run_preview)
        self.btn_preview.setStyleSheet(CSS_BTN_OUTLINE)
        self.btn_preview.setEnabled(False)
        ctrl_lay.addWidget(self.btn_preview)

        self.btn_process = QPushButton("COMMIT TO VISUALIZER")
        self.btn_process.clicked.connect(self.commit_to_viz)
        self.btn_process.setStyleSheet(CSS_BTN_PRIMARY)
        self.btn_process.setEnabled(False)
        ctrl_lay.addWidget(self.btn_process)
        
        ctrl_lay.addStretch()
        
        self.btn_export = QPushButton("EXPORT CSV")
        self.btn_export.clicked.connect(self.export_file)
        self.btn_export.setStyleSheet(CSS_BTN_OUTLINE)
        self.btn_export.setEnabled(False)
        ctrl_lay.addWidget(self.btn_export)
        
        layout.addWidget(ctrl_panel)

    def log(self, text): 
        self.txt_log.append(str(text))

    def init_graph(self):
        if self.plot_widget is None:
            import pyqtgraph as pg
            self.plot_widget = pg.PlotWidget()
            self.plot_widget.setBackground(None)
            self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
            
            self.raw_curve = self.plot_widget.plot(pen=pg.mkPen('#ff5555', width=1.5, style=Qt.PenStyle.DotLine))
            self.clean_curve = self.plot_widget.plot(pen=pg.mkPen('#55ff55', width=2))
            self.graph_layout.addWidget(self.plot_widget)

    def load_file(self):
        fn, _ = QFileDialog.getOpenFileName(self, "Open Data", "", "Data Files (*.parquet *.csv)")
        if fn:
            self.txt_log.clear()
            self.log(f"> Loaded: {os.path.basename(fn)}")
            try:
                self.log("...Initializing Data Engine...")
                self.init_graph()
                
                df, subj, act = storage.load_session_data(fn)
                
                self.raw_df = df
                self.current_subj = subj
                self.current_act = act
                self.log(f">> Metadata Found: Subject {subj}, Activity {act}")

                self.cmb_joint.blockSignals(True)
                self.cmb_joint.clear()
                joint_cols = [col for col in self.raw_df.columns if col.startswith('j')]
                self.cmb_joint.addItems(joint_cols)
                self.cmb_joint.blockSignals(False)

                from core import filters
                report, needs_repair = filters.PipelineProcessor.validate(self.raw_df)
                self.log(report)
                
                if needs_repair: 
                    self.log(">> Auto-repair highly recommended.")
                
                self.lbl_file.setText(os.path.basename(fn))
                self.btn_preview.setEnabled(True)
                self.btn_process.setEnabled(True)
                
                self.run_preview()
            except Exception as e: 
                self.log(f"Error: {e}")

    def run_preview(self):
        if self.raw_df is None: 
            return
        
        from core import filters
        df = self.raw_df.copy()
        self.log("\n> Generating Pipeline Preview...")
        
        if self.chk_teleport.isChecked():
            thresh = self.spn_tele_thresh.value()
            df, count = filters.PipelineProcessor.remove_teleportation(df, threshold=thresh)
            if count > 0:
                self.log(f"• Removed {count} teleported joint instances (> {thresh})")
        
        if self.chk_repair.isChecked(): 
            df = filters.PipelineProcessor.repair(df)
            self.log("• Applied stable Gap & NaN Interpolation")
            
        if self.chk_smooth.isChecked():
            w = self.spn_win.value()
            if w % 2 == 0: 
                w += 1
            df = filters.PipelineProcessor.smooth(df, window=w)
            self.log(f"• Applied Moving Average (w={w})")
            
        self.clean_df = df
        self.btn_export.setEnabled(True)
        self.update_graph()

    def update_graph(self):
        if self.raw_df is None or self.clean_df is None or self.plot_widget is None: 
            return
        
        joint = self.cmb_joint.currentText()
        if joint and joint in self.raw_df.columns:
            self.raw_curve.setData(self.raw_df[joint].values)
            self.clean_curve.setData(self.clean_df[joint].values)

    def commit_to_viz(self):
        if self.clean_df is None:
            self.run_preview()
        self.parent_app.load_data_into_viz(self.clean_df, self.current_subj, self.current_act)
        self.parent_app.switch_to_viz()

    def export_file(self):
        if self.clean_df is None: 
            return
        fn, _ = QFileDialog.getSaveFileName(self, "Save", "clean.csv", "CSV (*.csv)")
        if fn:
            success, msg = storage.export_clean_csv(self.clean_df, fn)
            self.log(f"> {msg}")


class VisualizerPage(QWidget):
    def __init__(self):
        super().__init__()
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
        if self.is_initialized: 
            return
            
        from core.render import SkeletonDisplay
        
        self.loading_lbl.setParent(None)
        self.viz = SkeletonDisplay()
        self.layout.addWidget(self.viz, stretch=1)
        
        dash_container = QWidget()
        dash_container.setFixedWidth(PANEL_WIDTH)
        dash_container.setStyleSheet(CSS_SIDEBAR)
        dash_layout = QVBoxLayout(dash_container)
        dash_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; } QScrollBar { width: 8px; background: #222; }")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet(f"background-color: {BG_PANEL}; border: none;")
        self.grid = QGridLayout(scroll_content)
        self.grid.setContentsMargins(15, 20, 15, 20)
        self.grid.setSpacing(10)
        
        self.info_box_widget = QWidget()
        info_lay = QVBoxLayout(self.info_box_widget)
        info_lay.setContentsMargins(0, 0, 0, 10)
        info_lay.addWidget(QLabel("SESSION INFO", styleSheet=CSS_HEADER))
        self.info_vals = {}
        
        def add_info(lbl, key):
            row = QHBoxLayout()
            l = QLabel(lbl)
            l.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px; border: none; background: transparent;")
            v = QLabel("--")
            v.setStyleSheet(f"color: {TEXT_MAIN}; font-size: 11px; font-weight: bold; border: none; background: transparent;")
            row.addWidget(l)
            row.addStretch()
            row.addWidget(v)
            info_lay.addLayout(row)
            self.info_vals[key] = v
            
        add_info("Subject", "lbl_subj")
        add_info("Activity", "lbl_act")
        add_info("FPS", "lbl_fps")
        add_info("Frames", "lbl_frames")
        
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
        
        self.btn_load_ext = QPushButton("LOAD RECORDING")
        self.btn_load_ext.clicked.connect(self.load_external)
        self.btn_load_ext.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_load_ext.setStyleSheet(CSS_BTN_PRIMARY)
        f_lay.addWidget(self.btn_load_ext)
        
        dash_layout.addWidget(footer)
        self.layout.addWidget(dash_container)
        self.is_initialized = True

    def load_session(self, session, filename="", subj="Unknown", act="Unknown"):
        if not self.is_initialized: 
            return
        
        from core import math 
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
            hip = math.get_point(first_frame, "hip_mid")
            if hip: 
                self.viz.center_view(hip[0], -hip[1]) 
            self.viz.update_frame(first_frame)

    def load_external(self):
        fn, _ = QFileDialog.getOpenFileName(self, "Open Data", "", "Data Files (*.parquet *.csv)")
        if fn:
            try:
                df, subj, act = storage.load_session_data(fn)
                session = data.df_to_session(df)
                self.load_session(session, fn, subj, act)
            except Exception as e: 
                QMessageBox.critical(self, "Error", str(e))

    def toggle_play(self):
        if not self.is_initialized: 
            return
        self.playing = not self.playing
        if self.playing: 
            self.timer.start()
        else: 
            self.timer.stop()
        
    def step(self, delta):
        if not self.is_initialized: 
            return
        self.playing = False
        self.timer.stop()
        if not self.active_session: 
            return
        self.frame_idx = (self.frame_idx + delta) % len(self.active_session.frames)
        self.loop(update_idx=False)

    def loop(self, update_idx=True):
        if not self.active_session or not self.active_session.frames: 
            return
            
        from core import math 
        f = self.active_session.frames[self.frame_idx]
        self.viz.update_frame(f)
        vals = math.compute_all_metrics(f)

        for key in self.keys:
            if key in vals and key in self.graphs:
                self.history[key].append(vals[key])
                if len(self.history[key]) > MAX_HISTORY_LENGTH: 
                    self.history[key].pop(0)
                self.graphs[key].update_data(self.history[key])
        
        self.lbl_time.setText(f"{f.timestamp:.1f}s")
        if update_idx: 
            self.frame_idx = (self.frame_idx + 1) % len(self.active_session.frames)


class UnifiedWorkstation(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OST Studio")
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setStyleSheet(CSS_MAIN_WINDOW)
        
        if os.path.exists(ICON): 
            self.setWindowIcon(QIcon(ICON))
        
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
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
        
        l_ver = QLabel(VERSION)
        l_ver.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px; border: none; margin-top: 15px;")
        l_ver.setAlignment(Qt.AlignmentFlag.AlignRight)
        nav_lay.addWidget(l_ver)
        main_layout.addWidget(nav_bar)
        
        self.stack = QStackedWidget()
        self.page_prep = DataPrepPage(self)
        self.page_viz = VisualizerPage() 
        
        self.stack.addWidget(self.page_prep)
        self.stack.addWidget(self.page_viz)
        main_layout.addWidget(self.stack)
        
        self.switch_page(0)
        QTimer.singleShot(100, self.boot_heavy_systems)

    def boot_heavy_systems(self):
        try: 
            self.page_viz.init_graphics()
        except Exception as e:
            close_splash()
            traceback.print_exc()

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
        
    def load_data_into_viz(self, df, subj="Unknown", act="Unknown"):
        from core import data
        session = data.df_to_session(df)
        self.page_viz.load_session(session, "Clean_Data.csv", subj, act)

    def keyPressEvent(self, event):
        if self.stack.currentIndex() == 1: 
            if event.key() == Qt.Key.Key_Space: 
                self.page_viz.toggle_play()
            elif event.key() == Qt.Key.Key_R: 
                self.page_viz.frame_idx = 0
                self.page_viz.loop(update_idx=False)
            elif event.key() == Qt.Key.Key_Left: 
                self.page_viz.step(-1)
            elif event.key() == Qt.Key.Key_Right: 
                self.page_viz.step(1)
        super().keyPressEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    close_splash()
    w = UnifiedWorkstation()
    w.show()
    sys.exit(app.exec())