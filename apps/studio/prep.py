from PyQt6.QtWidgets import *
from PyQt6.QtCore import Qt
import os 

from core import storage, filters
from core.config import *

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
        
        self.graph_container = QFrame()
        self.graph_container.setStyleSheet(f"background-color: {BG_DARK}; border: none;")
        self.graph_layout = QVBoxLayout(self.graph_container)
        self.graph_layout.setContentsMargins(0, 0, 0, 0)
        
        self.plot_widget = None
        self.raw_curve = None
        self.clean_curve = None

        self.init_graph()

        layout.addWidget(self.graph_container)

        ctrl_panel = QFrame()
        ctrl_panel.setFixedWidth(PANEL_WIDTH)
        ctrl_panel.setStyleSheet(CSS_SIDEBAR)
        ctrl_lay = QVBoxLayout(ctrl_panel)
        ctrl_lay.setContentsMargins(20, 20, 20, 20)
        ctrl_lay.setSpacing(10)
        ctrl_lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        ctrl_lay.addWidget(QLabel("DATA SOURCE", styleSheet=CSS_HEADER))
        self.btn_load = QPushButton("Select File")
        self.btn_load.clicked.connect(self.load_file)
        self.btn_load.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_load.setStyleSheet(CSS_BTN_PRIMARY)
        ctrl_lay.addWidget(self.btn_load)
        
        self.lbl_file = QLabel("No file selected")
        self.lbl_file.setStyleSheet(f"color: {ACCENT_COLOR}; font-size: 10px; border: none;")
        ctrl_lay.addWidget(self.lbl_file)
        
        line = QFrame(); line.setFixedHeight(1); line.setStyleSheet(f"background-color: {BORDER};")
        ctrl_lay.addWidget(line)

        ctrl_lay.addWidget(QLabel("PLOT PREVIEW", styleSheet=CSS_HEADER))
        self.cmb_joint = QComboBox()
        self.cmb_joint.setStyleSheet(CSS_INPUT)
        self.cmb_joint.currentIndexChanged.connect(self.update_graph)
        ctrl_lay.addWidget(self.cmb_joint)
        
        line2 = QFrame(); line2.setFixedHeight(1); line2.setStyleSheet(f"background-color: {BORDER};")
        ctrl_lay.addWidget(line2)

        ctrl_lay.addWidget(QLabel("CLEANING PIPELINE", styleSheet=CSS_HEADER))
        
        self.chk_teleport = QCheckBox("Remove Joint Teleportation")
        self.chk_teleport.setChecked(True)
        self.chk_teleport.setStyleSheet(CSS_CHECKBOX)
        ctrl_lay.addWidget(self.chk_teleport)
        
        tele_lay = QHBoxLayout()
        tele_lay.addWidget(QLabel("Distance Threshold:", styleSheet=f"color: {TEXT_DIM}; border: none;"))
        self.spn_tele_thresh = QDoubleSpinBox()
        self.spn_tele_thresh.setRange(0.01, 10.0); self.spn_tele_thresh.setValue(0.5); self.spn_tele_thresh.setSingleStep(0.1)
        self.spn_tele_thresh.setStyleSheet(CSS_INPUT)
        tele_lay.addWidget(self.spn_tele_thresh)
        ctrl_lay.addLayout(tele_lay)

        self.chk_repair = QCheckBox("Interpolate Missing Data")
        self.chk_repair.setChecked(True)
        self.chk_repair.setStyleSheet(CSS_CHECKBOX)
        ctrl_lay.addWidget(self.chk_repair)

        self.chk_smooth = QCheckBox("Apply Moving Average")
        self.chk_smooth.setChecked(True)
        self.chk_smooth.setStyleSheet(CSS_CHECKBOX)
        ctrl_lay.addWidget(self.chk_smooth)

        smooth_lay = QHBoxLayout()
        smooth_lay.addWidget(QLabel("Window Size:", styleSheet=f"color: {TEXT_DIM}; border: none;"))
        self.spn_win = QSpinBox()
        self.spn_win.setRange(3, 101); self.spn_win.setValue(3); self.spn_win.setSingleStep(2)
        self.spn_win.setStyleSheet(CSS_INPUT)
        smooth_lay.addWidget(self.spn_win)
        ctrl_lay.addLayout(smooth_lay)

        ctrl_lay.addSpacing(15)
        self.btn_preview = QPushButton("PREVIEW")
        self.btn_preview.clicked.connect(self.run_preview)
        self.btn_preview.setStyleSheet(CSS_BTN_OUTLINE)
        self.btn_preview.setEnabled(False)
        ctrl_lay.addWidget(self.btn_preview)

        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setStyleSheet(f"background-color: {COLOR_CONSOLE_BG}; color: {TEXT_DIM}; border: 1px solid {BORDER}; font-family: Consolas; font-size: 11px; padding: 10px;")
        ctrl_lay.addWidget(self.txt_log)
        
        ctrl_lay.addStretch()
        
        self.btn_export_clean = QPushButton("EXPORT")
        self.btn_export_clean.clicked.connect(self.export_clean_data)
        self.btn_export_clean.setStyleSheet(CSS_BTN_OUTLINE)
        self.btn_export_clean.setEnabled(False)
        ctrl_lay.addWidget(self.btn_export_clean)
        
        layout.addWidget(ctrl_panel)

    def log(self, text): 
        self.txt_log.append(str(text))

    # Draws Gridliness
    def init_graph(self):
        if self.plot_widget is None:
            import pyqtgraph as pg
            self.plot_widget = pg.PlotWidget()
            self.plot_widget.setBackground(None)
            self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
            
            self.raw_curve = self.plot_widget.plot(pen=pg.mkPen(COLOR_ERROR, width=1.5, style=Qt.PenStyle.DotLine))
            self.clean_curve = self.plot_widget.plot(pen=pg.mkPen(COLOR_SUCCESS, width=2))
            self.graph_layout.addWidget(self.plot_widget)

    def load_file(self):
        fn, _ = QFileDialog.getOpenFileName(self, "Open Data", "", "Data Files (*.parquet *.csv)")
        if fn:
            self.txt_log.clear()
            self.log(f"> Loaded: {os.path.basename(fn)}")
            try:
                self.log("...Initializing Data Engine...")
                
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
        self.btn_export_clean.setEnabled(True)
        self.update_graph()

    def update_graph(self):
        if self.raw_df is None or self.clean_df is None or self.plot_widget is None: return
        
        joint = self.cmb_joint.currentText()
        if joint and joint in self.raw_df.columns:
            self.raw_curve.setData(self.raw_df[joint].values)
            self.clean_curve.setData(self.clean_df[joint].values)

    def export_clean_data(self):
        if self.clean_df is None: return
        fn, _ = QFileDialog.getSaveFileName(self, "Export Cleaned Data", f"cleaned_{self.current_subj}_{self.current_act}.csv", "CSV (*.csv)")
        if fn:
            try:
                storage.export_clean_csv(self.clean_df, fn) 
                self.log(f">> Exported clean data to {os.path.basename(fn)}")
                QMessageBox.information(self, "Export Success", "Clean data saved successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", str(e))