# ost/sensors/realsense.py
import pyrealsense2 as rs
import numpy as np

class RealSenseCamera:
    def __init__(self, width=640, height=480, fps=30):
        try:
            self.pipeline = rs.pipeline()
            self.config = rs.config()
            self.config.enable_stream(rs.stream.color, width, height, rs.format.bgr8, fps)
            self.config.enable_stream(rs.stream.depth, width, height, rs.format.z16, fps)
            
            self.profile = self.pipeline.start(self.config)
            self.align = rs.align(rs.stream.color)
            
            # Filters
            self.spatial = rs.spatial_filter()
            self.temporal = rs.temporal_filter()
            
            print(f"[INFO] RealSense started {width}x{height}")
        except Exception as e:
            print(f"[ERROR] Camera init failed: {e}")
            self.pipeline = None

    def get_frames(self):
        if not self.pipeline: return None, None
        try:
            frames = self.pipeline.wait_for_frames(timeout_ms=1000)
            aligned = self.align.process(frames)
            
            color_frame = aligned.get_color_frame()
            depth_frame = aligned.get_depth_frame()
            
            if not color_frame or not depth_frame: return None, None
            
            # Apply filters
            depth_frame = self.spatial.process(depth_frame)
            depth_frame = self.temporal.process(depth_frame)
            
            return np.asanyarray(color_frame.get_data()), depth_frame
            
        except Exception as e:
            print(f"Frame error: {e}")
            return None, None

    def stop(self):
        if self.pipeline:
            self.pipeline.stop()