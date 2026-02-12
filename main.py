import sys
import os
import subprocess
from PyQt6.QtWidgets import *
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor, QIcon

# Ensure we can find core if running as script
if not getattr(sys, 'frozen', False):
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.settings import ICON

class OSTLauncher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OST Suite")
        self.resize(350, 450)
        self.setStyleSheet("QMainWindow { background-color: #2b2b2b; }")
        
        # Icon Setup
        if os.path.exists(ICON):
            self.setWindowIcon(QIcon(ICON))
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(40, 50, 40, 50)
        layout.setSpacing(20)
        
        # HEADER
        title = QLabel("OST")
        title.setStyleSheet("color: #e5e5e5; font-weight: 900; font-size: 48px; letter-spacing: 4px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        sub = QLabel("OSTEO-SKELETAL TRACKER")
        sub.setStyleSheet("color: #777; font-weight: bold; font-size: 10px; letter-spacing: 2px; margin-bottom: 30px;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sub)
        
        # ACTIONS
        self.btn_rec = self._make_card("NEW RECORDING", "Capture data from sensor", "#22c55e")
        self.btn_viz = self._make_card("OPEN STUDIO", "Process & Analyze data", "#3b82f6")
        
        self.btn_rec.clicked.connect(self.launch_recorder)
        self.btn_viz.clicked.connect(self.launch_studio)
        
        layout.addWidget(self.btn_rec)
        layout.addWidget(self.btn_viz)
        
        layout.addStretch()
        
        # FOOTER
        ver = QLabel("v0.1.0")
        ver.setStyleSheet("color: #444; font-size: 10px;")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(ver)

    def _make_card(self, title, subtitle, accent_color):
        btn = QPushButton()
        btn.setFixedHeight(80)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #212121;
                border: 1px solid #333;
                border-radius: 8px;
                text-align: left;
                padding-left: 20px;
            }}
            QPushButton:hover {{
                background-color: #262626;
                border: 1px solid {accent_color};
            }}
            QPushButton:pressed {{
                background-color: #1a1a1a;
            }}
        """)
        
        lay = QVBoxLayout(btn)
        lay.setContentsMargins(20, 15, 20, 15)
        lay.setSpacing(4)
        
        t = QLabel(title)
        t.setStyleSheet(f"color: #eee; font-weight: bold; font-size: 13px; background: transparent; border: none;")
        
        s = QLabel(subtitle)
        s.setStyleSheet("color: #666; font-size: 10px; background: transparent; border: none;")
        
        lay.addWidget(t)
        lay.addWidget(s)
        
        return btn

    def launch_recorder(self):
        self._run_tool("record")

    def launch_studio(self):
        self._run_tool("studio")

    def _run_tool(self, tool_name):
        """Launches tools as Scripts (Dev) or Executables (Release)."""
        is_frozen = getattr(sys, 'frozen', False)
        
        if is_frozen:
            # --- RELEASE MODE ---
            # Use sys.executable to find the folder where the .exe lives
            base_dir = os.path.dirname(sys.executable)
            exe_path = os.path.join(base_dir, f"{tool_name}.exe")
            
            if os.path.exists(exe_path):
                # Detach process so Launcher can close without killing tool
                subprocess.Popen([exe_path])
            else:
                QMessageBox.critical(self, "Error", f"Missing executable:\n{exe_path}")
        
        else:
            # --- DEV MODE ---
            base_dir = os.path.dirname(os.path.abspath(__file__))
            script_path = os.path.join(base_dir, "tools", f"{tool_name}.py")
            
            # Setup path so tools can find 'core'
            env = os.environ.copy()
            env["PYTHONPATH"] = base_dir + os.pathsep + env.get("PYTHONPATH", "")
            
            if os.path.exists(script_path):
                subprocess.Popen([sys.executable, script_path], env=env)
            else:
                print(f"Error: Missing script at {script_path}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = OSTLauncher()
    w.show()
    sys.exit(app.exec())