# System Imports
import sys
import os
import time
import datetime

# Core Library Imports
from sensors.realsense import RealSenseCamera
from core.transforms import get_mean_depth, deproject_pixel_to_point
from core.io import SessionWriter
from core.pose import PoseEstimator
from core.settings import *

# External Libraries
import cv2
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QImage, QPixmap, QFont, QIcon
from PyQt6.QtWidgets import *


class RecorderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OST Recorder")

        if os.path.exists(ICON):
            self.setWindowIcon(QIcon(ICON))
            
        # Window Sizes defined in settings.py
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        
        # State
        self.is_recording = False
        self.writer = None
        self.frame_count = 0
        self.prev_time = 0
        self.cam = None
        
        # UI Setup
        self._init_ui()
        self.setStyleSheet(STYLESHEET)

        # Initialize Hardware
        if not self.connect_camera():
            sys.exit(0) # Exit if user cancelled connection

        self.pose = PoseEstimator(model_complexity=1)

        # Timer loop
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_loop)
        self.timer.start(30) # ~30 FPS

    def connect_camera(self):
        """Attempts to connect to RealSense. Shows Dialog if failed."""
        while True:
            try:
                self.cam = RealSenseCamera(width=640, height=480, fps=30)

                # Check if pipeline actually started
                color, _ = self.cam.get_frames()
                if color is not None:
                    return True
                else:
                    raise Exception("No frames received")
            except Exception as e:

                # Show Retry Dialog
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Icon.Critical)
                msg.setWindowTitle("Camera Error")
                msg.setText("RealSense Camera not detected.")
                msg.setInformativeText(f"Error: {str(e)}\n\nPlease connect the camera and click Retry.")
                msg.setStandardButtons(QMessageBox.StandardButton.Retry | QMessageBox.StandardButton.Cancel)
                ret = msg.exec()
                
                if ret == QMessageBox.StandardButton.Cancel:
                    return False

    def _init_ui(self):
        # Main Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # SIDEBAR 
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(220)
        side_layout = QVBoxLayout(self.sidebar)
        side_layout.setContentsMargins(15, 20, 15, 30)
        side_layout.setSpacing(5)

        # Title
        title = QLabel("OST Recorder")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        side_layout.addWidget(title)
        side_layout.addSpacing(10)

        # Inputs
        self.inp_subject = self._add_input(side_layout, "Subject ID *", "e.g. S01")
        self.inp_activity = self._add_input(side_layout, "Activity *", "e.g. Walking")
        self.inp_temp = self._add_input(side_layout, "Room Temp (°C) *", "24.0")

        # Date
        side_layout.addWidget(QLabel("Date"))
        self.lbl_date = QLabel(datetime.datetime.now().strftime("%Y-%m-%d"))
        self.lbl_date.setStyleSheet("color: gray;")
        side_layout.addWidget(self.lbl_date)

        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #444;")
        side_layout.addWidget(line)

        # Model Select
        side_layout.addWidget(QLabel("Pose Model"))
        self.cmb_model = QComboBox()
        self.cmb_model.addItems(["Lite", "Full", "Heavy"])
        self.cmb_model.setCurrentIndex(1)
        self.cmb_model.currentIndexChanged.connect(self.change_model)
        side_layout.addWidget(self.cmb_model)

        # Stats
        side_layout.addSpacing(10)
        self.lbl_fps = QLabel("FPS: 00.0")
        self.lbl_fps.setFont(QFont("Consolas", 12))
        side_layout.addWidget(self.lbl_fps)
        
        self.lbl_frames = QLabel("Frames: 0")
        self.lbl_frames.setFont(QFont("Consolas", 10))
        self.lbl_frames.setStyleSheet("color: gray;")
        side_layout.addWidget(self.lbl_frames)

        # Error Label
        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet("color: #ff5555; font-size: 10px;")
        side_layout.addWidget(self.lbl_error)

        # Record Button
        self.btn_record = QPushButton("Record")
        self.btn_record.setObjectName("RecBtn")
        self.btn_record.setFixedHeight(40)
        self.btn_record.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_record.clicked.connect(self.toggle_recording)
        side_layout.addWidget(self.btn_record)

        l_ver = QLabel(VERSION)
        l_ver.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px; border: none; margin-top: 15px;")
        l_ver.setAlignment(Qt.AlignmentFlag.AlignLeft)
        side_layout.addWidget(l_ver)

        main_layout.addWidget(self.sidebar)

        # VIDEO AREA
        self.video_container = QWidget()
        self.video_container.setStyleSheet("background-color: black;")
        video_layout = QVBoxLayout(self.video_container)
        video_layout.setContentsMargins(0, 0, 0, 0)
        
        self.lbl_video = QLabel("Waiting for Camera...")
        self.lbl_video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_video.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        video_layout.addWidget(self.lbl_video)

        main_layout.addWidget(self.video_container)

    def _add_input(self, layout, label, placeholder):
        layout.addWidget(QLabel(label))
        inp = QLineEdit()
        inp.setPlaceholderText(placeholder)
        layout.addWidget(inp)
        return inp

    def change_model(self, index):
        self.pose = PoseEstimator(model_complexity=index)

    def toggle_recording(self):
        if not self.is_recording:
            # Validate
            s = self.inp_subject.text().strip()
            a = self.inp_activity.text().strip()
            t = self.inp_temp.text().strip()

            if not all([s, a, t]):
                self.lbl_error.setText("⚠ MISSING FIELDS")
                return
            self.lbl_error.setText("")

            # Start
            meta = {"Subject": s, "Activity": a, "Temp": t, "Date": datetime.datetime.now().isoformat()}
            
            try:
                self.writer = SessionWriter(s, a, metadata=meta)
                self.is_recording = True
                self.frame_count = 0
                
                # Lock UI
                self._set_inputs_enabled(False)
                
                # Update Button Style
                self.btn_record.setText("STOP")
                self.btn_record.setProperty("recording", True)
                self.btn_record.style().unpolish(self.btn_record) # Refresh style
                self.btn_record.style().polish(self.btn_record)
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to start writer: {e}")
        else:
            # Stop
            self.is_recording = False
            if self.writer: self.writer.close(); self.writer = None
            
            # Unlock UI
            self._set_inputs_enabled(True)
            self.lbl_frames.setStyleSheet("color: gray;")
            
            # Reset Button Style
            self.btn_record.setText("RECORD")
            self.btn_record.setProperty("recording", False)
            self.btn_record.style().unpolish(self.btn_record)
            self.btn_record.style().polish(self.btn_record)

    def _set_inputs_enabled(self, enabled):
        for w in [self.inp_subject, self.inp_activity, self.inp_temp, self.cmb_model]:
            w.setEnabled(enabled)

    def update_loop(self):
            # FPS Calculation
            t = time.time()
            dt = t - self.prev_time
            fps = 1.0 / dt if dt > 0 else 0
            self.prev_time = t
            self.lbl_fps.setText(f"FPS: {fps:.1f}")

            # Camera Safety
            if not self.cam: return

            color_img, depth_frame = self.cam.get_frames()

            # Reconnection Logic
            if color_img is None:
                self.timer.stop()
                if self.is_recording: self.toggle_recording()
                if self.connect_camera():
                    self.timer.start(30)
                    return
                else:
                    self.close()
                    return

            h, w, _ = color_img.shape
            landmarks = self.pose.estimate(color_img)
            
            # Initialize frame_data if we are recording
            frame_data = {}
            depth_intrin = None
            
            if self.is_recording and self.writer:
                # Create the base row with timestamp
                frame_data = {"timestamp": datetime.datetime.now().isoformat()}
                
                # Get intrinsics only if we need them later
                if depth_frame:
                    depth_intrin = depth_frame.profile.as_video_stream_profile().intrinsics

            # Add the data to the row
            if landmarks:
                for i, (lx, ly, lz) in enumerate(landmarks):
                    cx, cy = int(lx), int(ly)
                    if 0 <= cx < w and 0 <= cy < h:
                        cv2.circle(color_img, (cx, cy), 3, (0, 255, 0), -1)
                        
                        # Only calculate depth if we are actually recording
                        if self.is_recording and self.writer and depth_intrin:
                            dist = get_mean_depth(depth_frame, cx, cy, w, h)
                            if dist:
                                p = deproject_pixel_to_point(depth_intrin, cx, cy, dist)
                                frame_data[f"j{i}_x"] = p[0]
                                frame_data[f"j{i}_y"] = p[1]
                                frame_data[f"j{i}_z"] = p[2]

            # Write to disk if recording
            if self.is_recording and self.writer:
                self.writer.write_frame(frame_data)
                self.frame_count += 1
                self.lbl_frames.setText(f"Frames: {self.frame_count}")
                self.lbl_frames.setStyleSheet("color: #ff5555; font-weight: bold;")

            # DISPLAY LOGIC
            rgb_image = cv2.cvtColor(color_img, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_img)

            lbl_w = self.lbl_video.width()
            lbl_h = self.lbl_video.height()
        
            if lbl_w > 0 and lbl_h > 0:
                scaled_pixmap = pixmap.scaled(lbl_w, lbl_h, Qt.AspectRatioMode.KeepAspectRatio)
                self.lbl_video.setPixmap(scaled_pixmap)

    def closeEvent(self, event):
            """Safely shuts down hardware before closing."""
            # Stop the timer
            if hasattr(self, 'timer') and self.timer.isActive():
                self.timer.stop()
            
            # Stop the camera
            if hasattr(self, 'cam') and self.cam is not None:
                try:
                    self.cam.stop()
                except Exception as e:
                    print(f"Camera stop error: {e}")

            # Close any open recording sessions
            if self.writer:
                self.writer.close()
                
            event.accept()

if __name__ == "__main__":
    try:
        import pyi_splash # type: ignore
        pyi_splash.close()
    except ImportError:
        pass
    app = QApplication(sys.argv)
    window = RecorderApp()
    window.show()
    sys.exit(app.exec())