import sys
import os
import time
import datetime
import mediapipe
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap, QFont, QIcon
from PyQt6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QFrame, 
                             QLabel, QLineEdit, QComboBox, QPushButton, QMessageBox, 
                             QSizePolicy, QApplication)

from core.config import *

class CaptureThread(QThread):
    frame_ready = pyqtSignal(QImage)
    stats_updated = pyqtSignal(float, int)
    error_occurred = pyqtSignal(str)
    ready = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.running = True
        self.recording = False
        self.writer = None
        self.model_complexity = 1
        
        self.meta = {}
        self.subject = ""
        self.activity = ""

    def start_recording(self, subject, activity, meta):
        self.subject = subject
        self.activity = activity
        self.meta = meta
        self.recording = True

    def stop_recording(self):
        self.recording = False

    def run(self):
        try:
            import cv2
            from sensors.realsense import RealSenseCamera
            from core.depth import get_mean_depth, deproject_pixel_to_point
            from core.storage import SessionWriter
            from core.pose import PoseEstimator
            
            cam = RealSenseCamera(width=640, height=480, fps=30)
            pose = PoseEstimator(model_complexity=self.model_complexity)
            
            self.ready.emit()
            
            prev_time = time.time()
            frame_count = 0

            while self.running:
                t = time.time()
                dt = t - prev_time
                fps = 1.0 / dt if dt > 0 else 0
                prev_time = t

                color_img, depth_frame = cam.get_frames()
                
                if color_img is None:
                    continue

                h, w, _ = color_img.shape
                landmarks = pose.estimate(color_img)
                
                frame_data = {}
                depth_intrin = None
                
                if self.recording and self.writer is None:
                    self.writer = SessionWriter(self.subject, self.activity, metadata=self.meta)
                    frame_count = 0

                if self.recording and depth_frame:
                    frame_data = {"timestamp": datetime.datetime.now().isoformat()}
                    depth_intrin = depth_frame.profile.as_video_stream_profile().intrinsics

                if landmarks:
                    for i, (lx, ly, lz) in enumerate(landmarks):
                        cx, cy = int(lx), int(ly)
                        if 0 <= cx < w and 0 <= cy < h:
                            cv2.circle(color_img, (cx, cy), 3, (0, 255, 0), -1)
                            
                            if self.recording and depth_intrin:
                                dist = get_mean_depth(depth_frame, cx, cy, w, h)
                                if dist:
                                    p = deproject_pixel_to_point(depth_intrin, cx, cy, dist)
                                    frame_data[f"j{i}_x"] = p[0]
                                    frame_data[f"j{i}_y"] = p[1]
                                    frame_data[f"j{i}_z"] = p[2]

                if self.recording:
                    self.writer.write_frame(frame_data)
                    frame_count += 1
                    self.stats_updated.emit(fps, frame_count)
                else:
                    self.stats_updated.emit(fps, 0)
                    if self.writer:
                        self.writer.close()
                        self.writer = None

                rgb_image = cv2.cvtColor(color_img, cv2.COLOR_BGR2RGB)
                bytes_per_line = 3 * w
                qt_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                self.frame_ready.emit(qt_img.copy())

        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            if 'cam' in locals(): cam.stop()
            if self.writer: self.writer.close()

    def stop_worker(self):
        self.running = False
        self.wait()


class RecorderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OST Recorder")

        if os.path.exists(ICON):
            self.setWindowIcon(QIcon(ICON))
            
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        self.setStyleSheet(CSS_MAIN_WINDOW)
        
        self.is_recording = False
        self._init_ui()
        
        self.worker = CaptureThread()
        self.worker.frame_ready.connect(self.update_video)
        self.worker.stats_updated.connect(self.update_stats)
        self.worker.error_occurred.connect(self.handle_error)
        self.worker.ready.connect(self.hardware_ready)
        self.worker.start()

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(220)
        self.sidebar.setStyleSheet(CSS_SIDEBAR)
        
        side_layout = QVBoxLayout(self.sidebar)
        side_layout.setContentsMargins(15, 20, 15, 30)
        side_layout.setSpacing(5)

        title = QLabel("OST Recorder")
        title.setStyleSheet(CSS_HEADER)
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        side_layout.addWidget(title)
        side_layout.addSpacing(10)

        self.inp_subject = self._add_input(side_layout, "Subject ID *", "e.g. S01")
        self.inp_activity = self._add_input(side_layout, "Activity *", "e.g. Walking")
        self.inp_temp = self._add_input(side_layout, "Room Temp (°C) *", "24.0")

        side_layout.addWidget(QLabel("Date", styleSheet=CSS_HEADER))
        self.lbl_date = QLabel(datetime.datetime.now().strftime("%Y-%m-%d"))
        self.lbl_date.setStyleSheet(f"color: {TEXT_DIM};")
        side_layout.addWidget(self.lbl_date)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"color: {BORDER};")
        side_layout.addWidget(line)

        side_layout.addWidget(QLabel("Pose Model", styleSheet=CSS_HEADER))
        self.cmb_model = QComboBox()
        self.cmb_model.addItems(["Lite", "Full", "Heavy"])
        self.cmb_model.setCurrentIndex(1)
        self.cmb_model.setStyleSheet(CSS_INPUT)
        self.cmb_model.currentIndexChanged.connect(self.change_model)
        side_layout.addWidget(self.cmb_model)

        side_layout.addSpacing(10)
        self.lbl_fps = QLabel("FPS: 00.0")
        self.lbl_fps.setFont(QFont("Consolas", 12))
        self.lbl_fps.setStyleSheet(f"color: {TEXT_MAIN};")
        side_layout.addWidget(self.lbl_fps)
        
        self.lbl_frames = QLabel("Frames: 0")
        self.lbl_frames.setFont(QFont("Consolas", 10))
        self.lbl_frames.setStyleSheet(f"color: {TEXT_DIM};")
        side_layout.addWidget(self.lbl_frames)

        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet(f"color: {COLOR_ERROR}; font-size: 10px;")
        side_layout.addWidget(self.lbl_error)

        self.btn_record = QPushButton("RECORD")
        self.btn_record.setFixedHeight(40)
        self.btn_record.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_record.clicked.connect(self.toggle_recording)
        self.btn_record.setEnabled(False)
        self.btn_record.setStyleSheet(CSS_BTN_PRIMARY)
        side_layout.addWidget(self.btn_record)

        l_ver = QLabel(VERSION)
        l_ver.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px; border: none; margin-top: 15px;")
        l_ver.setAlignment(Qt.AlignmentFlag.AlignLeft)
        side_layout.addWidget(l_ver)

        main_layout.addWidget(self.sidebar)

        self.video_container = QWidget()
        self.video_container.setStyleSheet("background-color: black;")
        video_layout = QVBoxLayout(self.video_container)
        video_layout.setContentsMargins(0, 0, 0, 0)
        
        self.lbl_video = QLabel("Booting hardware and AI models...")
        self.lbl_video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_video.setStyleSheet(f"color: {TEXT_DIM};")
        self.lbl_video.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        video_layout.addWidget(self.lbl_video)

        main_layout.addWidget(self.video_container)

    def _add_input(self, layout, label, placeholder):
        layout.addWidget(QLabel(label, styleSheet=CSS_HEADER))
        inp = QLineEdit()
        inp.setPlaceholderText(placeholder)
        inp.setStyleSheet(CSS_INPUT)
        layout.addWidget(inp)
        return inp

    def hardware_ready(self):
        self.lbl_video.setText("")
        self.btn_record.setEnabled(True)

    def change_model(self, index):
        self.worker.model_complexity = index

    def update_video(self, qt_img):
        pixmap = QPixmap.fromImage(qt_img)
        lbl_w = self.lbl_video.width()
        lbl_h = self.lbl_video.height()
        
        if lbl_w > 0 and lbl_h > 0:
            scaled_pixmap = pixmap.scaled(lbl_w, lbl_h, Qt.AspectRatioMode.KeepAspectRatio)
            self.lbl_video.setPixmap(scaled_pixmap)

    def update_stats(self, fps, frame_count):
        self.lbl_fps.setText(f"FPS: {fps:.1f}")
        if self.is_recording:
            self.lbl_frames.setText(f"Frames: {frame_count}")
            self.lbl_frames.setStyleSheet(f"color: {COLOR_ERROR}; font-weight: bold;")

    def handle_error(self, err_msg):
        QMessageBox.critical(self, "Hardware Error", f"The background worker crashed:\n{err_msg}")
        self.close()

    def toggle_recording(self):
        if not self.is_recording:
            s = self.inp_subject.text().strip()
            a = self.inp_activity.text().strip()
            t = self.inp_temp.text().strip()

            if not all([s, a, t]):
                self.lbl_error.setText("⚠ MISSING FIELDS")
                return
            self.lbl_error.setText("")

            meta = {"Subject": s, "Activity": a, "Temp": t, "Date": datetime.datetime.now().isoformat()}
            
            self.worker.start_recording(s, a, meta)
            self.is_recording = True
            self._set_inputs_enabled(False)
            
            self.btn_record.setText("STOP")
            self.btn_record.setStyleSheet(CSS_BTN_STOP)
        else:
            self.worker.stop_recording()
            self.is_recording = False
            self._set_inputs_enabled(True)
            
            self.lbl_frames.setStyleSheet(f"color: {TEXT_DIM};")
            self.btn_record.setText("RECORD")
            self.btn_record.setStyleSheet(CSS_BTN_PRIMARY)

    def _set_inputs_enabled(self, enabled):
        for w in [self.inp_subject, self.inp_activity, self.inp_temp, self.cmb_model]:
            w.setEnabled(enabled)

    def closeEvent(self, event):
        self.worker.stop_worker()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    close_splash()   
    window = RecorderApp() 
    window.show()
    sys.exit(app.exec())