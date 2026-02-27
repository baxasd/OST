import time
import datetime
import mediapipe
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage


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
