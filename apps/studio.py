import sys
import os
import traceback

from PyQt6.QtWidgets import *
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QIcon

from core import data, storage, math, filters
from core.config import *
from core.widgets import MetricGraph, SkeletonLegend

try:
    from core.fatigue import FatigueAnalyzer
except ImportError:
    FatigueAnalyzer = None


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
        
        line = QFrame(); line.setFixedHeight(1); line.setStyleSheet(f"background-color: {BORDER};")
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
            if dotted: box.setStyleSheet(f"border-top: 2px dotted {color}; background: transparent;")
            else: box.setStyleSheet(f"background-color: {color};")
            lbl = QLabel(text)
            lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px; border: none;")
            legend_lay.addWidget(box); legend_lay.addWidget(lbl)

        add_legend_item("Raw", "#ff5555", dotted=True)
        legend_lay.addStretch()
        add_legend_item("Clean", "#55ff55")
        ctrl_lay.addLayout(legend_lay)

        line2 = QFrame(); line2.setFixedHeight(1); line2.setStyleSheet(f"background-color: {BORDER};")
        ctrl_lay.addWidget(line2)

        ctrl_lay.addWidget(QLabel("3. CLEANING PIPELINE", styleSheet=CSS_HEADER))
        
        self.chk_teleport = QCheckBox("Remove Joint Teleportation")
        self.chk_teleport.setChecked(True)
        self.chk_teleport.setStyleSheet(f"color: {TEXT_DIM}; border: none;")
        ctrl_lay.addWidget(self.chk_teleport)
        
        tele_lay = QHBoxLayout()
        tele_lay.addWidget(QLabel("Distance Threshold:", styleSheet=f"color: {TEXT_DIM}; border: none;"))
        self.spn_tele_thresh = QDoubleSpinBox()
        self.spn_tele_thresh.setRange(0.01, 10.0); self.spn_tele_thresh.setValue(0.5); self.spn_tele_thresh.setSingleStep(0.1)
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
        self.spn_win.setRange(3, 101); self.spn_win.setValue(5); self.spn_win.setSingleStep(2)
        self.spn_win.setStyleSheet(CSS_INPUT)
        smooth_lay.addWidget(self.spn_win)
        ctrl_lay.addLayout(smooth_lay)

        ctrl_lay.addSpacing(15)
        self.btn_preview = QPushButton("RUN PREVIEW")
        self.btn_preview.clicked.connect(self.run_preview)
        self.btn_preview.setStyleSheet(CSS_BTN_OUTLINE)
        self.btn_preview.setEnabled(False)
        ctrl_lay.addWidget(self.btn_preview)
        
        ctrl_lay.addStretch()
        
        self.btn_send_viz = QPushButton("SEND TO VISUALIZER")
        self.btn_send_viz.clicked.connect(self.send_to_viz)
        self.btn_send_viz.setStyleSheet(CSS_BTN_PRIMARY)
        self.btn_send_viz.setEnabled(False)
        ctrl_lay.addWidget(self.btn_send_viz)
        
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

                report, needs_repair = filters.PipelineProcessor.validate(self.raw_df)
                self.log(report)
                if needs_repair: 
                    self.log(">> Auto-repair highly recommended.")
                
                self.lbl_file.setText(os.path.basename(fn))
                self.btn_preview.setEnabled(True)
                
                self.run_preview()
            except Exception as e: 
                self.log(f"Error: {e}")

    def run_preview(self):
        if self.raw_df is None: return
        
        df = self.raw_df.copy()
        self.log("\n> Generating Pipeline Preview...")
        
        if self.chk_teleport.isChecked():
            thresh = self.spn_tele_thresh.value()
            df, count = filters.PipelineProcessor.remove_teleportation(df, threshold=thresh)
            if count > 0: self.log(f"• Removed {count} teleported joint instances (> {thresh})")
        
        if self.chk_repair.isChecked(): 
            df = filters.PipelineProcessor.repair(df)
            self.log("• Applied stable Gap & NaN Interpolation")
            
        if self.chk_smooth.isChecked():
            w = self.spn_win.value()
            if w % 2 == 0: w += 1
            df = filters.PipelineProcessor.smooth(df, window=w)
            self.log(f"• Applied Moving Average (w={w})")
            
        self.clean_df = df
        self.btn_send_viz.setEnabled(True)
        self.update_graph()

    def update_graph(self):
        if self.raw_df is None or self.clean_df is None or self.plot_widget is None: return
        
        joint = self.cmb_joint.currentText()
        if joint and joint in self.raw_df.columns:
            self.raw_curve.setData(self.raw_df[joint].values)
            self.clean_curve.setData(self.clean_df[joint].values)

    def send_to_viz(self):
        if self.clean_df is None: return
        self.parent_app.load_data_into_viz(self.clean_df, self.current_subj, self.current_act)


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
        
        btn_row = QHBoxLayout()
        self.btn_load_ext = QPushButton("LOAD DATA")
        self.btn_load_ext.clicked.connect(self.load_external)
        self.btn_load_ext.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_load_ext.setStyleSheet(CSS_BTN_OUTLINE)
        
        self.btn_analyze = QPushButton("RUN FATIGUE ANALYSIS")
        self.btn_analyze.clicked.connect(self.trigger_analysis)
        self.btn_analyze.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_analyze.setStyleSheet(CSS_BTN_PRIMARY)
        self.btn_analyze.setEnabled(False) 
        
        btn_row.addWidget(self.btn_load_ext)
        btn_row.addWidget(self.btn_analyze)
        f_lay.addLayout(btn_row)
        
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
        
        self.btn_analyze.setEnabled(True)
        
        if session.frames:
            first_frame = session.frames[0]
            hip = math.get_point(first_frame, "hip_mid")
            if hip: self.viz.center_view(hip[0], -hip[1]) 
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
        
        self.lbl_time.setText(f"{f.timestamp:.1f}s")
        if update_idx: 
            self.frame_idx = (self.frame_idx + 1) % len(self.active_session.frames)


class AnalysisPage(QWidget):
    def __init__(self):
        super().__init__()
        self.full_df = None
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Header
        self.lbl_title = QLabel("Post-Trial Biomechanical Analysis")
        self.lbl_title.setStyleSheet("font-size: 20px; font-weight: bold; color: white;")
        layout.addWidget(self.lbl_title)
        
        # Create a scroll area so the graphs aren't squished
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet(f"background-color: {BG_DARK}; border: none;")
        self.grid = QGridLayout(scroll_content)
        self.grid.setSpacing(15)
        
        import pyqtgraph as pg
        
        # 1. Mahalanobis Distance
        self.p_mahal = self._setup_plot("1. Overall Body Drift (Mahalanobis)", "Frames", "Distance")
        self.c_mahal = self.p_mahal.plot(pen=pg.mkPen(color=ACCENT_COLOR, width=2))
        
        # 2. Trunk Lean & Trend
        self.p_lean = self._setup_plot("2. Trunk Leans with Regression Trend", "Frames", "Degrees")
        self.p_lean.addLegend(offset=(10, 10))
        self.c_lean_x = self.p_lean.plot(pen=pg.mkPen('#ff5555', width=1.5), name="Lean Fwd/Back (X)")
        self.c_lean_z = self.p_lean.plot(pen=pg.mkPen('#5555ff', width=1.5), name="Lean Sideways (Z)")
        self.c_trend_x = self.p_lean.plot(pen=pg.mkPen('#ffaaaa', width=2, style=Qt.PenStyle.DashLine), name="Trend X")
        self.c_trend_z = self.p_lean.plot(pen=pg.mkPen('#aaaaff', width=2, style=Qt.PenStyle.DashLine), name="Trend Z")
        
        # 3. Shoulder Swings
        self.p_swings = self._setup_plot("3. Shoulder Swings (Smoothed)", "Frames", "Degrees")
        self.p_swings.addLegend(offset=(10, 10))
        self.c_sho_l = self.p_swings.plot(pen=pg.mkPen('#55ff55', width=1.5), name="Left Shoulder")
        self.c_sho_r = self.p_swings.plot(pen=pg.mkPen('#ffff55', width=1.5), name="Right Shoulder")
        
        # 4. Knee & Elbow Angles
        self.p_joints = self._setup_plot("4. Knee & Elbow Ranges", "Frames", "Degrees")
        self.p_joints.addLegend(offset=(10, 10))
        self.c_knee_l = self.p_joints.plot(pen=pg.mkPen('#ff5555', width=1), name="Left Knee")
        self.c_knee_r = self.p_joints.plot(pen=pg.mkPen('#aa0000', width=1), name="Right Knee")
        self.c_elb_l = self.p_joints.plot(pen=pg.mkPen('#55ff55', width=1), name="Left Elbow")
        self.c_elb_r = self.p_joints.plot(pen=pg.mkPen('#00aa00', width=1), name="Right Elbow")

        # 5. Symmetry (L vs R Difference)
        self.p_sym = self._setup_plot("5. L-R Symmetry (Above 0 = Left Dominant)", "Frames", "Delta Degrees")
        self.p_sym.addLegend(offset=(10, 10))
        self.p_sym.addLine(y=0, pen=pg.mkPen('#ffffff', width=1, style=Qt.PenStyle.DotLine))
        self.c_sym_sho = self.p_sym.plot(pen=pg.mkPen('#ff55ff', width=1.5), name="Shoulder Symmetry")
        self.c_sym_hip = self.p_sym.plot(pen=pg.mkPen('#55ffff', width=1.5), name="Hip Symmetry")
        
        # Place them in a 2-column Grid
        self.grid.addWidget(self.p_mahal, 0, 0)
        self.grid.addWidget(self.p_lean, 0, 1)
        self.grid.addWidget(self.p_swings, 1, 0)
        self.grid.addWidget(self.p_joints, 1, 1)
        self.grid.addWidget(self.p_sym, 2, 0)

        # 6. Text Summary & Export Box
        sum_widget = QWidget()
        sum_lay = QVBoxLayout(sum_widget)
        sum_lay.setContentsMargins(0, 0, 0, 0)
        
        self.txt_summary = QTextEdit()
        self.txt_summary.setReadOnly(True)
        self.txt_summary.setStyleSheet(f"background: {BG_PANEL}; border: 1px solid {BORDER}; color: {TEXT_MAIN}; padding: 10px; font-size: 13px;")
        sum_lay.addWidget(self.txt_summary)
        
        self.btn_export = QPushButton("SAVE ANALYSIS REPORT (.CSV)")
        self.btn_export.setStyleSheet(CSS_BTN_PRIMARY)
        self.btn_export.clicked.connect(self.export_data)
        self.btn_export.setEnabled(False)
        self.btn_export.setMinimumHeight(40)
        sum_lay.addWidget(self.btn_export)
        
        self.grid.addWidget(sum_widget, 2, 1)

        # Apply grid heights to look even
        for row in range(3):
            self.grid.setRowMinimumHeight(row, 280)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

    def _setup_plot(self, title, x_lbl, y_lbl):
        import pyqtgraph as pg
        p = pg.PlotWidget(title=title)
        p.setBackground(BG_PANEL)
        p.setLabel('bottom', x_lbl)
        p.setLabel('left', y_lbl)
        p.showGrid(x=True, y=True, alpha=0.2)
        return p

    def process_session(self, session, subj, act):
        if not FatigueAnalyzer:
            self.txt_summary.setText("❌ Error: core/fatigue.py not found.")
            return
            
        self.txt_summary.setText(f"Crunching full timeseries math for Subject {subj}...")
        QApplication.processEvents()
        
        try:
            # 1. Math engine crunches numbers
            ts_df, _ = math.generate_analysis_report(session)
            
            # 2. Fatigue engine creates trends & smoothing
            analyzer = FatigueAnalyzer(ts_df, fps=session.fps)
            self.full_df, trends, dom = analyzer.analyze()
            
            # 3. Update the Graphs
            self.c_mahal.setData(self.full_df['mahalanobis'].values)
            
            self.c_lean_x.setData(self.full_df['lean_x_smooth'].values)
            self.c_lean_z.setData(self.full_df['lean_z_smooth'].values)
            self.c_trend_x.setData(trends['lean_x'])
            self.c_trend_z.setData(trends['lean_z'])
            
            self.c_sho_l.setData(self.full_df['l_sho_smooth'].values)
            self.c_sho_r.setData(self.full_df['r_sho_smooth'].values)
            
            self.c_knee_l.setData(self.full_df['l_knee_smooth'].values)
            self.c_knee_r.setData(self.full_df['r_knee_smooth'].values)
            self.c_elb_l.setData(self.full_df['l_elb_smooth'].values)
            self.c_elb_r.setData(self.full_df['r_elb_smooth'].values)
            
            self.c_sym_sho.setData(self.full_df['shoulder_sym'].values)
            self.c_sym_hip.setData(self.full_df['hip_sym'].values)
            
            # 4. Generate Plain-English Medical Summary
            summary = f"<b>SUBJECT {subj} ({act})</b><br><br>"
            summary += f"<b>Dominance:</b><br>"
            summary += f"• Shoulder Swing: {dom['shoulder']} Dominant<br>"
            summary += f"• Hip Drive: {dom['hip']} Dominant<br><br>"
            
            summary += f"<b>Fatigue Trends (Trunk Lean):</b><br>"
            # Multiply slope by total frames to get the total degrees shifted
            total_x_shift = trends['lean_x_slope'] * len(self.full_df)
            total_z_shift = trends['lean_z_slope'] * len(self.full_df)
            
            summary += f"• Fwd/Back Lean shifted by {total_x_shift:+.2f}° over trial.<br>"
            summary += f"• Sideways Lean shifted by {total_z_shift:+.2f}° over trial."
            
            self.txt_summary.setHtml(summary)
            self.btn_export.setEnabled(True)
            
        except Exception as e:
            self.txt_summary.setText(f"❌ Error during analysis: {str(e)}")
            traceback.print_exc()

    def export_data(self):
        if self.full_df is None: return
        fn, _ = QFileDialog.getSaveFileName(self, "Save Analysis Data", "Analysis_Trends.csv", "CSV (*.csv)")
        if fn:
            try:
                self.full_df.to_csv(fn, index=False)
                QMessageBox.information(self, "Export Success", "Detailed analysis saved.")
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", str(e))


class UnifiedWorkstation(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OST Studio")
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setStyleSheet(CSS_MAIN_WINDOW)
        
        if os.path.exists(ICON): self.setWindowIcon(QIcon(ICON))
        
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
        self.btn_analysis = self._nav_btn("ANALYSIS")
        
        self.btn_prep.clicked.connect(lambda: self.switch_page(0))
        self.btn_viz.clicked.connect(lambda: self.switch_page(1))
        self.btn_analysis.clicked.connect(lambda: self.switch_page(2))
        
        nav_lay.addWidget(self.btn_prep)
        nav_lay.addWidget(self.btn_viz)
        nav_lay.addWidget(self.btn_analysis)
        nav_lay.addStretch()
        
        l_ver = QLabel(VERSION)
        l_ver.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px; border: none; margin-top: 15px;")
        l_ver.setAlignment(Qt.AlignmentFlag.AlignRight)
        nav_lay.addWidget(l_ver)
        main_layout.addWidget(nav_bar)
        
        self.stack = QStackedWidget()
        self.page_prep = DataPrepPage(self)
        self.page_viz = VisualizerPage(self) 
        self.page_analysis = AnalysisPage()
        
        self.stack.addWidget(self.page_prep)
        self.stack.addWidget(self.page_viz)
        self.stack.addWidget(self.page_analysis)
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
        self.btn_analysis.setChecked(index == 2)
        
    def load_data_into_viz(self, df, subj="Unknown", act="Unknown"):
        session = data.df_to_session(df)
        self.page_viz.load_session(session, "Cleaned_Data_In_Memory", subj, act)
        self.switch_page(1)
        
    def run_fatigue_analysis(self):
        session = self.page_viz.active_session
        if session:
            subj = self.page_viz.info_vals['lbl_subj'].text()
            act = self.page_viz.info_vals['lbl_act'].text()
            self.switch_page(2)
            QTimer.singleShot(50, lambda: self.page_analysis.process_session(session, subj, act))

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