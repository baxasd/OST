import sys
import os
import subprocess
from PyQt6.QtWidgets import *
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor, QIcon, QPixmap

# Ensure we can find core if running as script
if not getattr(sys, 'frozen', False):
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.settings import ICON, VERSION, LOGO

class OSTLauncher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OST Suite")
        self.resize(350, 500) # Increased height slightly for logo space
        self.setFixedSize(350, 500)
        self.setStyleSheet("QMainWindow { background-color: #1e1e1e; }")
        
        # Icon Setup
        if os.path.exists(ICON):
            self.setWindowIcon(QIcon(ICON))
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(30, 40, 30, 30)
        layout.setSpacing(15)
        
        # --- HEADER (LOGO IMAGE) ---
        logo_lbl = QLabel()
        logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        if os.path.exists(LOGO):
            pix = QPixmap(LOGO)
            # Scale to fit width (e.g., 200px wide, keep aspect ratio)
            scaled_pix = pix.scaled(300, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_lbl.setPixmap(scaled_pix)
        else:
            # Fallback if image missing
            logo_lbl.setText("OST")
            logo_lbl.setStyleSheet("color: #e5e5e5; font-weight: 900; font-size: 56px;")

        layout.addWidget(logo_lbl)
        
        sub = QLabel("OSTEO-SKELETAL TRACKER")
        sub.setStyleSheet("color: #666; font-weight: bold; font-size: 11px; letter-spacing: 3px; margin-bottom: 20px;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sub)
        
        # --- ACTIONS ---
        self.btn_rec = self._make_card("NEW RECORDING", "Capture data from sensor", "#167B87")
        self.btn_rec.clicked.connect(self.launch_recorder)
        layout.addWidget(self.btn_rec)

        self.btn_viz = self._make_card("OPEN STUDIO", "Process & Analyze data", "#0FA6C1")
        self.btn_viz.clicked.connect(self.launch_studio)
        layout.addWidget(self.btn_viz)
        
        layout.addStretch()
        
        # --- FOOTER ---
        ver = QLabel(f"{VERSION}")
        ver.setStyleSheet("color: #444; font-size: 10px; font-family: Consolas;")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(ver)

    def _get_asset_path(self, filename):
        """Helper to find assets in Dev (root/assets) or Prod (dist/assets)"""
        if getattr(sys, 'frozen', False):
            # Running as EXE
            base_dir = os.path.dirname(sys.executable)
            return os.path.join(base_dir, 'assets', filename)
        else:
            # Running as Script
            base_dir = os.path.dirname(os.path.abspath(__file__))
            return os.path.join(base_dir, 'assets', filename)

    def _make_card(self, title, subtitle, accent_color):
        btn = QPushButton()
        btn.setFixedHeight(90)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #252525;
                border: 1px solid #333;
                border-radius: 10px;
                text-align: left;
                padding-left: 20px;
            }}
            QPushButton:hover {{
                background-color: #2a2a2a;
                border: 1px solid {accent_color};
            }}
            QPushButton:pressed {{
                background-color: #151515;
            }}
        """)
        
        lay = QVBoxLayout(btn)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(4)
        
        t = QLabel(title)
        t.setStyleSheet(f"color: #eee; font-weight: bold; font-size: 14px; background: transparent; border: none;")
        t.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        s = QLabel(subtitle)
        s.setStyleSheet("color: #888; font-size: 11px; background: transparent; border: none;")
        s.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        lay.addWidget(t)
        lay.addWidget(s)
        
        return btn

    def launch_recorder(self):
        # Removed self.hide() to prevent ghost-processes
        self._run_tool("record")

    def launch_studio(self):
        self._run_tool("studio")

    def _run_tool(self, tool_name):
        is_frozen = getattr(sys, 'frozen', False)
        
        # 1. Grab the current environment variables
        env = os.environ.copy()
        
        if is_frozen:
            # CRITICAL FIX: Strip PyInstaller variables so the child EXE 
            # doesn't get confused and crash silently.
            env.pop('_MEIPASS2', None)
            env.pop('_MEIPASS', None)
            
            # EXE Mode
            base_dir = os.path.dirname(sys.executable)
            exe_path = os.path.join(base_dir, f"{tool_name}.exe")
            
            if os.path.exists(exe_path):
                # Pass the cleaned environment to the child process
                subprocess.Popen([exe_path], env=env)
                # Force the launcher to completely quit
                QApplication.quit() 
            else:
                QMessageBox.critical(self, "Error", f"Missing component:\n{exe_path}")
        else:
            # Script Mode
            base_dir = os.path.dirname(os.path.abspath(__file__))
            script_path = os.path.join(base_dir, "tools", f"{tool_name}.py")
            
            env["PYTHONPATH"] = base_dir + os.pathsep + env.get("PYTHONPATH", "")
            
            if os.path.exists(script_path):
                subprocess.Popen([sys.executable, script_path], env=env)
                QApplication.quit()
            else:
                print(f"Error: Missing script at {script_path}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = OSTLauncher()
    w.show()
    sys.exit(app.exec())