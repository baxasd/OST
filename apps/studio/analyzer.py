from PyQt6.QtWidgets import *
from PyQt6.QtCore import Qt

from core import data, storage, math
from core.config import *

try:
    from core.fatigue import FatigueAnalyzer
except ImportError:
    FatigueAnalyzer = None

class AnalysisPage(QWidget):
    def __init__(self):
        super().__init__()
        self.ts_df = None
        self.fatigue_df = None
        self.stats_df = None
        self.adv_metrics = {}
        self.active_session = None
        self.subj = "Unknown"
        self.act = "Unknown"
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # ==========================================
        # LEFT PANEL: GRAPH CARDS
        # ==========================================
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet(f"background-color: {BG_DARK}; border: none;")
        self.graph_layout = QVBoxLayout(scroll_content)
        self.graph_layout.setContentsMargins(20, 20, 20, 20)
        self.graph_layout.setSpacing(20)
        
        import pyqtgraph as pg
        
        # 1. Systemic Drift
        self.p_mahal = self._create_base_plot("Mahalanobis Distance")
        self.c_mahal = self.p_mahal.plot(pen=pg.mkPen(color=ACCENT_COLOR, width=2))
        self.thresh_line = pg.InfiniteLine(angle=0, pen=pg.mkPen('#ff5555', width=1, style=Qt.PenStyle.DotLine))
        self.p_mahal.addItem(self.thresh_line)
        self.card_mahal = self._make_graph_panel(
            "Multivariate Postural Deviation", 
            "Tracks the multivariate distance of the subject's current posture compared to their baseline state"
            "Significant increases may indicate fatigue-related postural drift.", 
            self.p_mahal, [("Drift", ACCENT_COLOR), ("Critical Threshold", "#ff5555")])
        self.graph_layout.addWidget(self.card_mahal)
        
        # 2. Trunk Lean (Sagittal + Frontal Envelopes)
        self.p_lean = self._create_base_plot("Degrees")
        self.c_lean_z_mean = pg.PlotDataItem(pen=pg.mkPen('#5555ff', width=2))
        self.c_lean_z_upper = pg.PlotDataItem(pen=pg.mkPen(None)); self.c_lean_z_lower = pg.PlotDataItem(pen=pg.mkPen(None))
        self.lean_z_fill = pg.FillBetweenItem(self.c_lean_z_lower, self.c_lean_z_upper, brush=(85, 85, 255, 50))
        
        self.c_lean_x_mean = pg.PlotDataItem(pen=pg.mkPen('#ff5555', width=2))
        self.c_lean_x_upper = pg.PlotDataItem(pen=pg.mkPen(None)); self.c_lean_x_lower = pg.PlotDataItem(pen=pg.mkPen(None))
        self.lean_x_fill = pg.FillBetweenItem(self.c_lean_x_lower, self.c_lean_x_upper, brush=(255, 85, 85, 50))

        self.p_lean.addItem(self.c_lean_z_mean); self.p_lean.addItem(self.c_lean_z_upper); self.p_lean.addItem(self.c_lean_z_lower); self.p_lean.addItem(self.lean_z_fill)
        self.p_lean.addItem(self.c_lean_x_mean); self.p_lean.addItem(self.c_lean_x_upper); self.p_lean.addItem(self.c_lean_x_lower); self.p_lean.addItem(self.lean_x_fill)
        
        self.card_lean = self._make_graph_panel("2. Trunk Lean Dynamics (Mean ± SD Envelope)", "Sagittal (Forward/Back) and Frontal (Side-to-Side) Core Stability.", self.p_lean, [("Sagittal (Z)", "#5555ff"), ("Frontal (X)", "#ff5555")])
        self.graph_layout.addWidget(self.card_lean)
        
        # 3. Knee Flexion
        self.p_knee = self._create_base_plot("Degrees")
        self.c_knee_l = self.p_knee.plot(pen=pg.mkPen('#55ff55', width=1.5))
        self.c_knee_r = self.p_knee.plot(pen=pg.mkPen('#55aaff', width=1.5))
        self.card_knee = self._make_graph_panel("3. Knee Flexion Dynamics", "Left vs Right Knee joint angles.", self.p_knee, [("Left Knee", "#55ff55"), ("Right Knee", "#55aaff")])
        self.graph_layout.addWidget(self.card_knee)

        # 4. Hip / Leg Swing
        self.p_hip = self._create_base_plot("Degrees")
        self.c_hip_l = self.p_hip.plot(pen=pg.mkPen('#ffaa00', width=1.5))
        self.c_hip_r = self.p_hip.plot(pen=pg.mkPen('#aa55ff', width=1.5))
        self.card_hip = self._make_graph_panel("4. Hip Flexion (Foot/Leg Swing)", "Left vs Right Hip drive and leg swing.", self.p_hip, [("Left Hip", "#ffaa00"), ("Right Hip", "#aa55ff")])
        self.graph_layout.addWidget(self.card_hip)

        # 5. Shoulder Dynamics
        self.p_sho = self._create_base_plot("Degrees")
        self.c_sho_l = self.p_sho.plot(pen=pg.mkPen('#ff5555', width=1.5))
        self.c_sho_r = self.p_sho.plot(pen=pg.mkPen('#55ffff', width=1.5))
        self.card_sho = self._make_graph_panel("5. Shoulder Swing Dynamics", "Left vs Right Shoulder extension.", self.p_sho, [("Left Shoulder", "#ff5555"), ("Right Shoulder", "#55ffff")])
        self.graph_layout.addWidget(self.card_sho)

        # 6. Elbow Dynamics
        self.p_elb = self._create_base_plot("Degrees")
        self.c_elb_l = self.p_elb.plot(pen=pg.mkPen('#aaffaa', width=1.5))
        self.c_elb_r = self.p_elb.plot(pen=pg.mkPen('#ffaaaa', width=1.5))
        self.card_elb = self._make_graph_panel("6. Elbow Flexion Dynamics", "Left vs Right Elbow tracking.", self.p_elb, [("Left Elbow", "#aaffaa"), ("Right Elbow", "#ffaaaa")])
        self.graph_layout.addWidget(self.card_elb)

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll, stretch=1)
        
        # ==========================================
        # RIGHT PANEL: CONTROLS & CONSOLE
        # ==========================================
        ctrl_panel = QFrame()
        ctrl_panel.setFixedWidth(PANEL_WIDTH + 140) # Made wider to fit the massive text table
        ctrl_panel.setStyleSheet(CSS_SIDEBAR)
        ctrl_lay = QVBoxLayout(ctrl_panel)
        ctrl_lay.setContentsMargins(20, 20, 20, 20)
        ctrl_lay.setSpacing(15)
        
        ctrl_lay.addWidget(QLabel("1. DATA SOURCE", styleSheet=CSS_HEADER))
        self.btn_load = QPushButton("Load Clean Data")
        self.btn_load.clicked.connect(self.load_external_data)
        self.btn_load.setStyleSheet(CSS_BTN_OUTLINE)
        ctrl_lay.addWidget(self.btn_load)
        
        ctrl_lay.addWidget(QFrame(frameShape=QFrame.Shape.HLine, styleSheet=f"color: {BORDER};"))
        ctrl_lay.addWidget(QLabel("2. PLOT CONTROLS", styleSheet=CSS_HEADER))
        
        self.cmb_grouping = QComboBox()
        self.cmb_grouping.addItems(["Frames (Raw)", "Seconds (Averaged)", "Minutes (Averaged)"])
        self.cmb_grouping.setStyleSheet(CSS_INPUT)
        self.cmb_grouping.currentIndexChanged.connect(self.recalculate_plots)
        ctrl_lay.addWidget(self.cmb_grouping)
        
        self.chk_env = QCheckBox("Show Variance Envelopes (SD)"); self.chk_env.setChecked(True); self.chk_env.setStyleSheet(f"color: {TEXT_DIM};")
        self.chk_env.stateChanged.connect(self.recalculate_plots)
        ctrl_lay.addWidget(self.chk_env)

        ctrl_lay.addWidget(QFrame(frameShape=QFrame.Shape.HLine, styleSheet=f"color: {BORDER};"))
        ctrl_lay.addWidget(QLabel("3. ADVANCED STATISTICAL EXTRACTOR", styleSheet=CSS_HEADER))
        
        # Massive Text Console
        self.txt_console = QTextEdit()
        self.txt_console.setReadOnly(True)
        self.txt_console.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.txt_console.setStyleSheet(f"background-color: #0d0d0f; color: #00ffcc; font-family: Consolas; font-size: 11px; padding: 10px; border: 1px solid {BORDER}; border-radius: 4px;")
        self.txt_console.setMinimumHeight(400)
        ctrl_lay.addWidget(self.txt_console)
        
        ctrl_lay.addStretch()
        self.btn_export = QPushButton("Export Report & Plots")
        self.btn_export.setStyleSheet(CSS_BTN_PRIMARY)
        self.btn_export.clicked.connect(self.export_results)
        self.btn_export.setEnabled(False)
        ctrl_lay.addWidget(self.btn_export)
        
        main_layout.addWidget(ctrl_panel)

    def _create_base_plot(self, y_lbl):
        import pyqtgraph as pg
        p = pg.PlotWidget()
        p.setBackground(BG_DARK)
        p.setLabel('bottom', "Time")
        p.setLabel('left', y_lbl)
        p.showGrid(x=True, y=True, alpha=0.2)
        p.enableAutoRange(axis=pg.ViewBox.XYAxes)
        return p

    def _make_graph_panel(self, title, desc, plot_widget, legend_items=None):
        card = QFrame()
        card.setStyleSheet(f"background-color: {BG_PANEL}; border: 1px solid {BORDER}; border-radius: 6px;")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(15, 15, 15, 15)
        
        header_lay = QHBoxLayout()
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(f"color: {TEXT_MAIN}; font-size: 14px; font-weight: bold; border: none;")
        header_lay.addWidget(lbl_title)
        header_lay.addStretch()
        
        if legend_items:
            leg_lay = QHBoxLayout()
            leg_lay.setSpacing(8)
            for name, color in legend_items:
                indicator = QLabel(); indicator.setFixedSize(12, 12); indicator.setStyleSheet(f"background-color: {color}; border-radius: 2px;")
                lbl = QLabel(name); lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px; border: none;")
                leg_lay.addWidget(indicator); leg_lay.addWidget(lbl)
            header_lay.addLayout(leg_lay)
            
        lay.addLayout(header_lay)
        lbl_desc = QLabel(desc); lbl_desc.setWordWrap(True); lbl_desc.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px; border: none; margin-bottom: 5px;")
        lay.addWidget(lbl_desc)
        plot_widget.setMinimumHeight(200)
        lay.addWidget(plot_widget)
        return card

    def load_external_data(self):
        fn, _ = QFileDialog.getOpenFileName(self, "Open Cleaned Data", "", "Data Files (*.parquet *.csv)")
        if fn:
            try:
                df, subj, act = storage.load_session_data(fn) #
                session = data.df_to_session(df)
                self.process_session(session, subj, act)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load data:\n{str(e)}")

    def process_session(self, session, subj, act):
        if not FatigueAnalyzer: return
        self.active_session = session; self.subj = subj; self.act = act
        try:
            self.ts_df, self.stats_df = math.generate_analysis_report(session) #
            analyzer = FatigueAnalyzer(self.ts_df, fps=session.fps)
            self.fatigue_df, _, _, self.adv_metrics = analyzer.run_pipeline()
            
            self._update_console()
            self.recalculate_plots()
            self.btn_export.setEnabled(True)
        except Exception as e:
            import traceback; traceback.print_exc()

    def _update_console(self):
        """Generates a brutally detailed text table of all stats + slope trends."""
        desc = self.adv_metrics['describe']
        
        text = f"METRICS SUMMARY\n"
        text += f"Subj: {self.subj} | Act: {self.act}\n"
        text += "="*78 + "\n"
        text += f"{'METRIC':<14} | {'MEAN':>7} | {'STD':>7} | {'MIN':>7} | {'MAX':>7} | {'MEDIAN':>7} | {'TREND/MIN':>9}\n"
        text += "-"*78 + "\n"
        
        for idx, row in desc.iterrows():
            col_name = str(idx)
            # Skip non-metrics if they snuck in
            if col_name in ['timestamp', 'frame', 'minute']: continue
            
            mean = row.get('mean', 0)
            std = row.get('std', 0)
            vmin = row.get('min', 0)
            vmax = row.get('max', 0)
            med = row.get('50%', 0)
            trend = self.adv_metrics.get(f'slope_{col_name}', 0.0)
            
            text += f"{col_name:<14} | {mean:>7.2f} | {std:>7.2f} | {vmin:>7.2f} | {vmax:>7.2f} | {med:>7.2f} | {trend:>+9.3f}\n"
            
        text += "="*78 + "\n"
        self.txt_console.setText(text)

    def recalculate_plots(self):
        if self.ts_df is None or self.fatigue_df is None: return
        
        df = self.ts_df.copy()
        df['mahalanobis_dist'] = self.fatigue_df['mahalanobis_dist']
        
        grouping = self.cmb_grouping.currentText()
        x_label = "Frames"
        
        if "Seconds" in grouping:
            df['time_grp'] = df['timestamp'].astype(int)
            df = df.groupby('time_grp').mean().reset_index()
            x_label = "Seconds"
        elif "Minutes" in grouping:
            df['time_grp'] = (df['timestamp'] / 60).astype(int)
            df = df.groupby('time_grp').mean().reset_index()
            x_label = "Minutes"
            
        x_vals = df.index.values
        
        # 1. Mahalanobis
        self.c_mahal.setData(x_vals, df['mahalanobis_dist'].values)
        self.thresh_line.setPos(2.0)
        
        for p in [self.p_mahal, self.p_lean, self.p_knee, self.p_hip, self.p_sho, self.p_elb]: 
            p.setLabel('bottom', x_label)

        # 2. Trunk Lean (Sagittal Z & Frontal X)
        roll_z_mean = df['lean_z'].rolling(max(1, len(df)//20), min_periods=1).mean().values
        roll_z_std = df['lean_z'].rolling(max(1, len(df)//20), min_periods=1).std().fillna(0).values
        roll_x_mean = df['lean_x'].rolling(max(1, len(df)//20), min_periods=1).mean().values
        roll_x_std = df['lean_x'].rolling(max(1, len(df)//20), min_periods=1).std().fillna(0).values
        
        if self.chk_env.isChecked():
            self.c_lean_z_mean.setData(x_vals, roll_z_mean); self.c_lean_z_upper.setData(x_vals, roll_z_mean + roll_z_std); self.c_lean_z_lower.setData(x_vals, roll_z_mean - roll_z_std)
            self.c_lean_x_mean.setData(x_vals, roll_x_mean); self.c_lean_x_upper.setData(x_vals, roll_x_mean + roll_x_std); self.c_lean_x_lower.setData(x_vals, roll_x_mean - roll_x_std)
            self.lean_z_fill.setVisible(True); self.lean_x_fill.setVisible(True)
        else:
            self.c_lean_z_mean.setData(x_vals, df['lean_z'].values); self.c_lean_z_upper.setData([], []); self.c_lean_z_lower.setData([], [])
            self.c_lean_x_mean.setData(x_vals, df['lean_x'].values); self.c_lean_x_upper.setData([], []); self.c_lean_x_lower.setData([], [])
            self.lean_z_fill.setVisible(False); self.lean_x_fill.setVisible(False)

        # 3. Knee Trends
        self.c_knee_l.setData(x_vals, df['l_knee'].values); self.c_knee_r.setData(x_vals, df['r_knee'].values)
        
        # 4. Hip / Leg Swing
        self.c_hip_l.setData(x_vals, df['l_hip'].values); self.c_hip_r.setData(x_vals, df['r_hip'].values)
        
        # 5. Shoulder Dynamics
        self.c_sho_l.setData(x_vals, df['l_sho'].values); self.c_sho_r.setData(x_vals, df['r_sho'].values)
        
        # 6. Elbow Dynamics
        self.c_elb_l.setData(x_vals, df['l_elb'].values); self.c_elb_r.setData(x_vals, df['r_elb'].values)

    def export_results(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Directory to Export Report and Plots")
        if not dir_path: return
        
        try:
            import pyqtgraph.exporters, os
            
            # Export Stats
            self.adv_metrics['describe'].to_csv(os.path.join(dir_path, f"{self.subj}_{self.act}_SummaryStats.csv"), index=True)
            
            # Export Console Text
            with open(os.path.join(dir_path, f"{self.subj}_{self.act}_AdvancedMetrics.txt"), "w") as f:
                f.write(self.txt_console.toPlainText())

            # Export Plots
            plots = [(self.p_mahal, "1_Drift"), (self.p_lean, "2_Lean"), (self.p_knee, "3_Knees"), 
                     (self.p_hip, "4_Hips"), (self.p_sho, "5_Shoulders"), (self.p_elb, "6_Elbows")]
            
            QApplication.processEvents()
            for plot, name in plots:
                exporter = pyqtgraph.exporters.ImageExporter(plot.scene())
                exporter.parameters()['width'] = 1200
                exporter.export(os.path.join(dir_path, f"{self.subj}_{self.act}_{name}.png"))
                
            QMessageBox.information(self, "Export Complete", f"Data exported to {dir_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"An error occurred:\n{str(e)}")
