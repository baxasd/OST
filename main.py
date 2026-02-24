import sys
import os
import subprocess
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton, QApplication, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor, QIcon, QPixmap

# Ensure we can find core if running as script
if not getattr(sys, 'frozen', False):
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.config import ICON, VERSION, LOGO, BG_DARK, close_splash, ACCENT_COLOR

class OSTLauncher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OST Suite")
        self.setFixedSize(350, 500)
        self.setStyleSheet(f"QMainWindow {{ background-color: {BG_DARK}; }}")
        
        if os.path.exists(ICON):
            self.setWindowIcon(QIcon(ICON))
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(30, 40, 30, 30)
        layout.setSpacing(15)
        
        logo_lbl = QLabel()
        logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        if os.path.exists(LOGO):
            pix = QPixmap(LOGO)
            scaled_pix = pix.scaled(300, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_lbl.setPixmap(scaled_pix)
        else:
            logo_lbl.setText("OST")
            logo_lbl.setStyleSheet("color: #e5e5e5; font-weight: 900; font-size: 56px;")

        layout.addWidget(logo_lbl)
        
        sub = QLabel("OSTEO-SKELETAL TRACKER")
        sub.setStyleSheet(f"color: {ACCENT_COLOR}; font-weight: bold; font-size: 11px; letter-spacing: 3px; margin-bottom: 20px;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sub)
        
        self.btn_rec = self._make_card("NEW RECORDING", "Capture data from sensor", ACCENT_COLOR)
        self.btn_rec.clicked.connect(lambda: self._run_tool("record"))
        layout.addWidget(self.btn_rec)

        self.btn_viz = self._make_card("OPEN STUDIO", "Process & Analyze data", ACCENT_COLOR)
        self.btn_viz.clicked.connect(lambda: self._run_tool("studio"))
        layout.addWidget(self.btn_viz)
        
        layout.addStretch()
        
        ver = QLabel(f"{VERSION}")
        ver.setStyleSheet("color: #444; font-size: 10px; font-family: Consolas;")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(ver)

    def _make_card(self, title, subtitle, accent_color):
        btn = QPushButton()
        btn.setFixedHeight(90)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        btn.setStyleSheet(f"""
            QPushButton {{ background-color: #252525; border: 1px solid #333; border-radius: 10px; text-align: left; padding-left: 20px; }}
            QPushButton:hover {{ background-color: #2a2a2a; border: 1px solid {accent_color}; }}
            QPushButton:pressed {{ background-color: #151515; }}
        """)
        
        lay = QVBoxLayout(btn)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(4)
        
        t = QLabel(title)
        t.setStyleSheet("color: #eee; font-weight: bold; font-size: 14px; background: transparent; border: none;")
        t.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        s = QLabel(subtitle)
        s.setStyleSheet("color: #888; font-size: 11px; background: transparent; border: none;")
        s.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        lay.addWidget(t)
        lay.addWidget(s)
        return btn

    def _run_tool(self, tool_name):
        is_frozen = getattr(sys, 'frozen', False)
        env = os.environ.copy()
        
        if is_frozen:
            env.pop('_MEIPASS2', None)
            env.pop('_MEIPASS', None)
            
            base_dir = os.path.dirname(sys.executable)
            exe_path = os.path.join(base_dir, f"{tool_name}.exe")
            
            if os.path.exists(exe_path):
                subprocess.Popen([exe_path], env=env)
                QApplication.quit() 
            else:
                QMessageBox.critical(self, "Error", f"Missing component:\n{exe_path}")
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            script_path = os.path.join(base_dir, "apps", f"{tool_name}.py")
            env["PYTHONPATH"] = base_dir + os.pathsep + env.get("PYTHONPATH", "")
            
            if os.path.exists(script_path):
                subprocess.Popen([sys.executable, script_path], env=env)
                QApplication.quit()
            else:
                print(f"Error: Missing script at {script_path}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    close_splash()
    w = OSTLauncher()
    w.show()
    sys.exit(app.exec())