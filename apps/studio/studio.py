import sys
import os
import traceback

from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton, QStackedWidget
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QIcon

from core.config import *
from core import data

# Import the refactored pages
from prep import DataPrepPage
from visualizer import VisualizerPage
from analyzer import AnalysisPage

class UnifiedWorkstation(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setStyleSheet(CSS_MAIN_WINDOW)
        
        if os.path.exists(ICON): 
            self.setWindowIcon(QIcon(ICON))
        
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Build Navigation
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
        nav_lay.addWidget(l_ver)
        main_layout.addWidget(nav_bar)
        
        # Initialize Stacked Pages
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

    def boot_heavy_systems(self):
        try: 
            self.page_viz.init_graphics()
        except Exception:
            close_splash()
            traceback.print_exc()

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