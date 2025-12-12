import pyrealsense2 as rs
import numpy as np
import time
import sys
import cv2

class RealSenseCamera:
    """
    Class to initialize Intel Realsense Cameras
    Tested with Intel Realsense D435i camera with depth sensor
    Only with camera with depth sensor is supported
    """

    def __init__(self, width=640, height=480, fps=30, verbose=False ):
        """Initializes camera pipeline"""
        self.verbose = verbose
        try:
            self.pipeline = rs.pipeline()
            self.config = rs.config()
            self.config.enable_stream(rs.stream.color, width, height, rs.format.bgr8, fps)
            self.config.enable_stream(rs.stream.depth, width, height, rs.format.z16, fps)
            self.profile = self.pipeline.start(self.config)
            self.align = rs.align(rs.stream.color)
            self.spatial = rs.spatial_filter()
            self.spatial.set_option(rs.option.filter_magnitude, 2)
            self.spatial.set_option(rs.option.filter_smooth_alpha, 0.5)
            self.spatial.set_option(rs.option.filter_smooth_delta, 20)
            self.temporal = rs.temporal_filter()
            self.temporal.set_option(rs.option.filter_smooth_alpha, 0.35)
            self.temporal.set_option(rs.option.filter_smooth_delta, 20)


            if self.verbose:
                print(f"[INFO] RealSense camera started ({width}x{height}@{fps})")
        except Exception as e:
            print("Error initializing RealSense camera:", e)
            sys.exit(1)

    def get_frames(self):
        
        """Get color and depth frames"""

        try:
            frames = self.pipeline.wait_for_frames(timeout_ms=1000)

            # Align Pixels with color and depth frames for accurate measurement.
            aligned = self.align.process(frames)
            color_frame = aligned.get_color_frame()
            depth_frame = aligned.get_depth_frame()

            # Return None if either of frames not present
            if not color_frame or not depth_frame:
                return None, None
            
            depth_frame = self.spatial.process(depth_frame)
            depth_frame = self.temporal.process(depth_frame)
            depth_frame = depth_frame.as_depth_frame()

            
            # Converts color frame data to np.array
            color_image = np.asanyarray(color_frame.get_data())

            # For Debugging
            #colorizer = rs.colorizer()
            #depth_vis = np.asanyarray(colorizer.colorize(depth_frame).get_data())
            #cv2.imshow("Depth", depth_vis)

            
            # Delay a bit for stable framee retrieving
            #time.sleep(0.01)

            return color_image, depth_frame
        
        except Exception as e:
            print("Error getting frames from RealSense camera:", e)
            return None, None

    def stop(self):
        """Stops pipeline when called"""
        try:
            self.pipeline.stop()
            if self.verbose:
                print("[INFO] RealSense pipeline stopped.")
        except Exception as e:
            print("Error stopping RealSense pipeline:", e)
