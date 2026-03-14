import os
import numpy as np
import pyqtgraph as pg
import pyqtgraph.exporters # Required for saving plots to PNG
from PyQt6.QtWidgets import *
from PyQt6.QtCore import Qt

from core.math import kinematics
from core.ui.theme import *
from core.io import storage, structs
from core.ui.widgets import HeavyTaskWorker

class AnalysisPage(QWidget):
    """
    The Postural Breakdown and Gait Analysis Dashboard.
    Calculates basic joint angles, systemic drift, and exports professional per-second reports.
    """
    def __init__(self):
        super().__init__()
        # ── State Variables ──
        self.ts_df = None           # Raw Timeseries DataFrame (Angles over time)
        self.df_per_sec = None      # Aggregated second-by-second DataFrame
        self.stats_df = None        # Summary statistics (Mean, Min, Max)
        self.trend_metrics = {}     # Dictionary holding trendlines and slopes
        self.active_session = None
        self.subj = "Unknown"
        self.act = "Unknown"
        
        # ── Layout Setup ──
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Left Side: A Scrollable Area for the 5 Graphs
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet(f"background-color: {BG_PANEL}; border: none;") 
        self.graph_layout = QVBoxLayout(scroll_content)
        self.graph_layout.setContentsMargins(10, 10, 10, 10)
        self.graph_layout.setSpacing(10)
        
        # ── Graph 1: Trunk Lean (with Variance Envelopes) ──
        self.p_lean = self._create_base_plot("Degrees")
        
        # Z-Axis (Side-to-Side Lean)
        self.c_lean_z_mean = pg.PlotDataItem(pen=pg.mkPen(PLOT_LEAN_Z, width=2), autoDownsample=True, clipToView=True)
        self.c_lean_z_upper = pg.PlotDataItem(pen=pg.mkPen(None), autoDownsample=True, clipToView=True) 
        self.c_lean_z_lower = pg.PlotDataItem(pen=pg.mkPen(None), autoDownsample=True, clipToView=True) 
        self.lean_z_fill = pg.FillBetweenItem(self.c_lean_z_lower, self.c_lean_z_upper, brush=(85, 85, 255, 50)) 
        
        # X-Axis (Forward/Backward Lean)
        self.c_lean_x_mean = pg.PlotDataItem(pen=pg.mkPen(PLOT_LEAN_X, width=2), autoDownsample=True, clipToView=True)
        self.c_lean_x_upper = pg.PlotDataItem(pen=pg.mkPen(None), autoDownsample=True, clipToView=True)
        self.c_lean_x_lower = pg.PlotDataItem(pen=pg.mkPen(None), autoDownsample=True, clipToView=True)
        self.lean_x_fill = pg.FillBetweenItem(self.c_lean_x_lower, self.c_lean_x_upper, brush=(255, 85, 85, 50)) 

        # Add all items to the plot
        self.p_lean.addItem(self.c_lean_z_mean); self.p_lean.addItem(self.c_lean_z_upper); self.p_lean.addItem(self.c_lean_z_lower); self.p_lean.addItem(self.lean_z_fill)
        self.p_lean.addItem(self.c_lean_x_mean); self.p_lean.addItem(self.c_lean_x_upper); self.p_lean.addItem(self.c_lean_x_lower); self.p_lean.addItem(self.lean_x_fill)
        
        self.card_lean = self._make_graph_panel("1. Trunk Lean Dynamics", "Sagittal (Forward/Back) and Frontal (Side-to-Side) Core Stability.", self.p_lean, [("Frontal (Z)", PLOT_LEAN_Z), ("Sagittal (X)", PLOT_LEAN_X)])
        self.graph_layout.addWidget(self.card_lean)
        
        # ── Graphs 2-5: Standard Joint Angles ──
        self.p_knee = self._create_base_plot("Degrees")
        self.c_knee_l = self.p_knee.plot(pen=pg.mkPen(PLOT_KNEE_L, width=1.5), autoDownsample=True, clipToView=True)
        self.c_knee_r = self.p_knee.plot(pen=pg.mkPen(PLOT_KNEE_R, width=1.5), autoDownsample=True, clipToView=True)
        self.card_knee = self._make_graph_panel("2. Knee Flexion Dynamics", "Left vs Right Knee joint angles.", self.p_knee, [("Left Knee", PLOT_KNEE_L), ("Right Knee", PLOT_KNEE_R)])
        self.graph_layout.addWidget(self.card_knee)

        self.p_hip = self._create_base_plot("Degrees")
        self.c_hip_l = self.p_hip.plot(pen=pg.mkPen(PLOT_HIP_L, width=1.5), autoDownsample=True, clipToView=True)
        self.c_hip_r = self.p_hip.plot(pen=pg.mkPen(PLOT_HIP_R, width=1.5), autoDownsample=True, clipToView=True)
        self.card_hip = self._make_graph_panel("3. Hip Flexion", "Left vs Right Hip drive.", self.p_hip, [("Left Hip", PLOT_HIP_L), ("Right Hip", PLOT_HIP_R)])
        self.graph_layout.addWidget(self.card_hip)

        self.p_sho = self._create_base_plot("Degrees")
        self.c_sho_l = self.p_sho.plot(pen=pg.mkPen(PLOT_SHO_L, width=1.5), autoDownsample=True, clipToView=True)
        self.c_sho_r = self.p_sho.plot(pen=pg.mkPen(PLOT_SHO_R, width=1.5), autoDownsample=True, clipToView=True)
        self.card_sho = self._make_graph_panel("4. Shoulder Swing Dynamics", "Left vs Right Shoulder extension.", self.p_sho, [("Left Shoulder", PLOT_SHO_L), ("Right Shoulder", PLOT_SHO_R)])
        self.graph_layout.addWidget(self.card_sho)

        self.p_elb = self._create_base_plot("Degrees")
        self.c_elb_l = self.p_elb.plot(pen=pg.mkPen(PLOT_ELB_L, width=1.5), autoDownsample=True, clipToView=True)
        self.c_elb_r = self.p_elb.plot(pen=pg.mkPen(PLOT_ELB_R, width=1.5), autoDownsample=True, clipToView=True)
        self.card_elb = self._make_graph_panel("5. Elbow Flexion Dynamics", "Left vs Right Elbow tracking.", self.p_elb, [("Left Elbow", PLOT_ELB_L), ("Right Elbow", PLOT_ELB_R)])
        self.graph_layout.addWidget(self.card_elb)

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll, stretch=1)
        
        # ── Right Side: Controls & Console ──
        ctrl_panel = QFrame()
        ctrl_panel.setFixedWidth(PANEL_WIDTH)
        ctrl_panel.setStyleSheet(CSS_SIDEBAR)
        ctrl_lay = QVBoxLayout(ctrl_panel)
        ctrl_lay.setContentsMargins(20, 20, 20, 20)
        ctrl_lay.setSpacing(10)
        
        ctrl_lay.addWidget(QLabel("DATA SOURCE", styleSheet=CSS_HEADER))
        self.btn_load = QPushButton("Load Clean Data")
        self.btn_load.clicked.connect(self.load_external_data)
        self.btn_load.setStyleSheet(CSS_BTN_OUTLINE)
        ctrl_lay.addWidget(self.btn_load)

        line = QFrame(); line.setFixedHeight(1); line.setStyleSheet(f"background-color: {BORDER};")
        ctrl_lay.addWidget(line)
        
        ctrl_lay.addWidget(QLabel("PLOT CONTROLS", styleSheet=CSS_HEADER))
        
        # Resampling dropdown
        self.cmb_grouping = QComboBox()
        self.cmb_grouping.addItems(["Frames (Raw)", "Seconds (Averaged)", "Minutes (Averaged)"])
        self.cmb_grouping.setCurrentIndex(1) # Default to seconds
        self.cmb_grouping.setStyleSheet(CSS_INPUT)
        self.cmb_grouping.currentIndexChanged.connect(self.recalculate_plots)
        ctrl_lay.addWidget(self.cmb_grouping)
        
        # Variance Envelope Toggle
        self.chk_env = QCheckBox("Show Variance Envelopes (SD)"); self.chk_env.setChecked(True); self.chk_env.setStyleSheet(CSS_CHECKBOX)
        self.chk_env.stateChanged.connect(self.recalculate_plots)
        ctrl_lay.addWidget(self.chk_env)

        line2 = QFrame(); line2.setFixedHeight(1); line2.setStyleSheet(f"background-color: {BORDER};")
        ctrl_lay.addWidget(line2)
        
        ctrl_lay.addWidget(QLabel("CONSOLE OUTPUT", styleSheet=CSS_HEADER))
        
        # Output Log
        self.txt_console = QTextEdit()
        self.txt_console.setReadOnly(True)
        self.txt_console.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.txt_console.setStyleSheet(f"background-color: {COLOR_CONSOLE_BG}; color: {COLOR_CONSOLE_TXT}; font-family: Consolas; font-size: 11px; padding: 10px; border: 1px solid {BORDER}; border-radius: 4px;")
        self.txt_console.setMinimumHeight(400)
        ctrl_lay.addWidget(self.txt_console)
        
        ctrl_lay.addStretch()
        self.btn_export = QPushButton("Export Report & Plots")
        self.btn_export.setStyleSheet(CSS_BTN_PRIMARY)
        self.btn_export.clicked.connect(self.export_results)
        self.btn_export.setEnabled(False)
        ctrl_lay.addWidget(self.btn_export)
        
        main_layout.addWidget(ctrl_panel)

    # ── UI Construction Helpers ──
    def _create_base_plot(self, y_lbl):
        """Creates a standardized, styled PyqtGraph plot widget."""
        p = pg.PlotWidget()
        p.setBackground(BG_PANEL) 
        p.setLabel('bottom', "Time", color=TEXT_DIM)
        p.setLabel('left', y_lbl, color=TEXT_DIM)
        p.showGrid(x=True, y=True, alpha=0.3) 
        p.getAxis('bottom').setPen(pg.mkPen(color=TEXT_DIM))
        p.getAxis('left').setPen(pg.mkPen(color=TEXT_DIM))
        p.enableAutoRange(axis=pg.ViewBox.XYAxes)
        return p

    def _make_graph_panel(self, title, desc, plot_widget, legend_items=None):
        """Wraps a PyqtGraph plot inside a styled QFrame card with a title and legend."""
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

    # ── Pipeline Logic ──
    def load_external_data(self):
        """Triggered by the Load button. Reads the Parquet file into memory."""
        fn, _ = QFileDialog.getOpenFileName(self, "Open Cleaned Data", "", "Data Files (*.parquet *.csv)")
        if fn:
            try:
                df, subj, act = storage.load_session_data(fn)
                session = structs.df_to_session(df)
                self.process_session(session, subj, act)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load data:\n{str(e)}")

    def process_session(self, session, subj, act):
        """Starts the basic math engine on a background thread so the UI doesn't freeze."""
        self.active_session = session; self.subj = subj; self.act = act
        
        self.txt_console.setText("Running basic kinematics analysis...\nAggregating to seconds...")
        self.btn_load.setEnabled(False)
        self.btn_load.setText("Processing...")
        
        # Fire off the background worker
        self.worker = HeavyTaskWorker(self._run_math_pipeline, session)
        self.worker.finished.connect(self._on_pipeline_complete)
        self.worker.error.connect(self._on_pipeline_error)
        self.worker.start()

    def _run_math_pipeline(self, session):
        """Runs the basic kinematics math and per-second aggregations."""
        ts_df, _ = kinematics.generate_analysis_report(session)
        
        # 1. Convert to integer seconds
        ts_df['time_sec'] = np.floor(ts_df['timestamp']).astype(int)
        numeric_cols = [c for c in ts_df.columns if c not in ['frame', 'time_sec', 'timestamp']]
        
        # 2. Aggregate per second
        df_per_sec = ts_df.groupby('time_sec')[numeric_cols].mean().reset_index()
        # Ensure timestamp exists for UI plotting logic
        df_per_sec['timestamp'] = df_per_sec['time_sec']
        
        # 3. Calculate basic drift (linear regression slope per minute)
        trend_metrics = {}
        if len(df_per_sec) > 1:
            x_mins = df_per_sec['time_sec'] / 60.0
            
            for col in numeric_cols:
                mask = ~np.isnan(df_per_sec[col])
                if mask.sum() > 1:
                    # np.polyfit(X, Y, 1) returns [slope, intercept]
                    slope, _ = np.polyfit(x_mins[mask], df_per_sec[col][mask], 1)
                    trend_metrics[f"slope_{col}"] = slope

        # 4. Generate Summary Stats. 
        # .T transposes it so metrics are the rows and stats (mean, min, max) are the columns
        stats_df = df_per_sec.drop(columns=['time_sec', 'timestamp'], errors='ignore').describe().T

        return ts_df, df_per_sec, stats_df, trend_metrics

    def _on_pipeline_complete(self, result):
        """Callback when the math finishes."""
        self.ts_df, self.df_per_sec, self.stats_df, self.trend_metrics = result
        self._update_console()
        self.recalculate_plots()
        self.btn_export.setEnabled(True)
        self.btn_load.setEnabled(True)
        self.btn_load.setText("Load Clean Data")

    def _on_pipeline_error(self, err):
        """Callback if the math crashes."""
        self.txt_console.setText(f"Error during analysis:\n{err}")
        self.btn_load.setEnabled(True)
        self.btn_load.setText("Load Clean Data")

    def _update_console(self):
        """Prints a clean ASCII table of the runner's joint statistics."""
        text = f"METRICS SUMMARY (Per Second Avg)\n"
        text += f"Subj: {self.subj} | Act: {self.act}\n"
        text += "="*78 + "\n"
        text += f"{'METRIC':<14} | {'MEAN':>7} | {'STD':>7} | {'MIN':>7} | {'MAX':>7} | {'MEDIAN':>7} | {'TREND/MIN':>9}\n"
        text += "-"*78 + "\n"
        
        for idx, row in self.stats_df.iterrows():
            col_name = str(idx)
            
            mean = row.get('mean', 0)
            std = row.get('std', 0)
            vmin = row.get('min', 0)
            vmax = row.get('max', 0)
            med = row.get('50%', 0)
            trend = self.trend_metrics.get(f'slope_{col_name}', 0.0)
            text += f"{col_name:<14} | {mean:>7.2f} | {std:>7.2f} | {vmin:>7.2f} | {vmax:>7.2f} | {med:>7.2f} | {trend:>+9.3f}\n"
            
        text += "="*78 + "\n"
        self.txt_console.setText(text)

    def recalculate_plots(self):
        """Updates the visual graphs. Resamples data if requested by the ComboBox."""
        if self.ts_df is None or self.df_per_sec is None: return
        
        grouping = self.cmb_grouping.currentText()
        x_label = "Frames"
        
        # Resample data dynamically for the UI 
        if "Frames" in grouping:
            df = self.ts_df.copy()
            x_label = "Frames"
        elif "Seconds" in grouping:
            # Using our pre-calculated second data!
            df = self.df_per_sec.copy()
            x_label = "Seconds"
        elif "Minutes" in grouping:
            df = self.ts_df.copy()
            df['time_grp'] = (df['timestamp'] / 60).astype(int)
            df = df.groupby('time_grp').mean().reset_index()
            x_label = "Minutes"
            
        # 1. SAVE THE EXACT DATAFRAME FOR THE EXPORTER
        self.current_export_df = df.copy() 
        self.current_export_label = x_label

        # 2. UI ANTI-LAG OPTIMIZATION
        # If we have thousands of points, rendering the variance shadow during scroll is laggy.
        # We downsample the data *purely* for the visuals.
        MAX_UI_POINTS = 1500
        if len(df) > MAX_UI_POINTS:
            step = len(df) // MAX_UI_POINTS
            plot_df = df.iloc[::step]
        else:
            plot_df = df
            
        x_vals = plot_df.index.values
        
        # Update X-Axis labels across all plots
        for p in [self.p_lean, self.p_knee, self.p_hip, self.p_sho, self.p_elb]: 
            p.setLabel('bottom', x_label)

        # 3. Update Lean Plot (Using plot_df to prevent lag)
        if self.chk_env.isChecked():
            # OPTIMIZATION: Only run rolling calculations if the checkbox is actively checked.
            window_size = max(1, len(plot_df)//20)
            roll_z_mean = plot_df['lean_z'].rolling(window_size, min_periods=1).mean().values
            roll_z_std = plot_df['lean_z'].rolling(window_size, min_periods=1).std().fillna(0).values
            roll_x_mean = plot_df['lean_x'].rolling(window_size, min_periods=1).mean().values
            roll_x_std = plot_df['lean_x'].rolling(window_size, min_periods=1).std().fillna(0).values
            
            self.c_lean_z_mean.setData(x_vals, roll_z_mean)
            self.c_lean_z_upper.setData(x_vals, roll_z_mean + roll_z_std)
            self.c_lean_z_lower.setData(x_vals, roll_z_mean - roll_z_std)
            
            self.c_lean_x_mean.setData(x_vals, roll_x_mean)
            self.c_lean_x_upper.setData(x_vals, roll_x_mean + roll_x_std)
            self.c_lean_x_lower.setData(x_vals, roll_x_mean - roll_x_std)
            
            self.lean_z_fill.setVisible(True)
            self.lean_x_fill.setVisible(True)
        else:
            # If envelopes are off, just plot the raw mean line and clear the upper/lower bounds
            self.c_lean_z_mean.setData(x_vals, plot_df['lean_z'].values)
            self.c_lean_z_upper.setData([], [])
            self.c_lean_z_lower.setData([], [])
            
            self.c_lean_x_mean.setData(x_vals, plot_df['lean_x'].values)
            self.c_lean_x_upper.setData([], [])
            self.c_lean_x_lower.setData([], [])
            
            self.lean_z_fill.setVisible(False)
            self.lean_x_fill.setVisible(False)

        # 4. Update Standard Angle Plots
        self.c_knee_l.setData(x_vals, plot_df['l_knee'].values)
        self.c_knee_r.setData(x_vals, plot_df['r_knee'].values)
        self.c_hip_l.setData(x_vals, plot_df['l_hip'].values)
        self.c_hip_r.setData(x_vals, plot_df['r_hip'].values)
        self.c_sho_l.setData(x_vals, plot_df['l_sho'].values)
        self.c_sho_r.setData(x_vals, plot_df['r_sho'].values)
        self.c_elb_l.setData(x_vals, plot_df['l_elb'].values)
        self.c_elb_r.setData(x_vals, plot_df['r_elb'].values)

    def export_results(self):
        """Exports the aggregated CSV data, summary stats, and PNG screenshots of all graphs."""
        dir_path = QFileDialog.getExistingDirectory(self, "Select Directory to Export Report and Plots")
        if not dir_path: return
        
        try:
            # 1. Save the timeseries data matching what the user currently selected (Frames, Seconds, Mins)
            if hasattr(self, 'current_export_df'):
                file_label = getattr(self, 'current_export_label', 'Data')
                self.current_export_df.to_csv(os.path.join(dir_path, f"{self.subj}_{self.act}_{file_label}.csv"), index=False)
            
            # 2. Save ONLY the proper Summary Stats
            self.stats_df.to_csv(os.path.join(dir_path, f"{self.subj}_{self.act}_SummaryStats.csv"), index=True)

            # Define the specific plots we want to take a picture of
            plots = [
                (self.p_lean, "1_Lean"), 
                (self.p_knee, "2_Knees"), 
                (self.p_hip, "3_Hips"), 
                (self.p_sho, "4_Shoulders"), 
                (self.p_elb, "5_Elbows")
            ]
            
            # processEvents forces the UI to fully draw the graphs before taking the screenshot
            QApplication.processEvents()
            
            for plot, name in plots:
                exporter = pyqtgraph.exporters.ImageExporter(plot.scene())
                exporter.parameters()['width'] = 1200 
                exporter.export(os.path.join(dir_path, f"{self.subj}_{self.act}_{name}.png"))
                
            QMessageBox.information(self, "Export Complete", f"CSV, summary, and plots exported to:\n{dir_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"An error occurred:\n{str(e)}")