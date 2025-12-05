"""RealSense camera integration helpers.

This module wraps the RealSense pipeline and exposes a small
convenience class used by the application. The wrapper focuses on
providing synchronized color and depth frames (aligned) and hides the
RealSense setup/teardown details.
"""

import pyrealsense2 as rs
import numpy as np
import time
import sys
import logging

logger = logging.getLogger(__name__)


class RealSenseCamera:
    """
    Class to initialize Intel Realsense Cameras
    Tested with Intel Realsense D435i camera with depth sensor
    Only cameras with a depth sensor are supported.
    """

    def __init__(self, width=640, height=480, fps=30, verbose=False):
        """Initializes camera pipeline and starts streaming."""
        self.verbose = verbose
        try:
            # Create pipeline and enable color+depth streams
            self.pipeline = rs.pipeline()
            self.config = rs.config()
            self.config.enable_stream(rs.stream.color, width, height, rs.format.bgr8, fps)
            self.config.enable_stream(rs.stream.depth, width, height, rs.format.z16, fps)
            self.profile = self.pipeline.start(self.config)

            # Align depth frames to the color frames for pixel-accurate depth
            self.align = rs.align(rs.stream.color)
            if self.verbose:
                logger.info(f"RealSense camera started ({width}x{height}@{fps})")
        except Exception:
            # Fatal error during initialization — log and exit to keep
            # behavior unchanged from original code.
            logger.exception("Error initializing RealSense camera:")
            sys.exit(1)

    def get_frames(self):
        """Return a tuple (color_image, depth_frame).

        - `color_image` is a NumPy BGR image suitable for OpenCV.
        - `depth_frame` is the raw RealSense depth frame used for depth queries.

        Returns `(None, None)` on error or when frames are unavailable.
        """

        try:
            frames = self.pipeline.wait_for_frames(timeout_ms=1000)

            # Align pixels between color and depth frames for consistent sampling
            aligned = self.align.process(frames)
            color_frame = aligned.get_color_frame()
            depth_frame = aligned.get_depth_frame()

            # Return None if either frame is missing
            if not color_frame or not depth_frame:
                return None, None

            # Convert the color frame to a NumPy array for OpenCV operations
            color_image = np.asanyarray(color_frame.get_data())

            # Small sleep to stabilize frame retrieval in some camera setups
            time.sleep(0.01)

            return color_image, depth_frame

        except Exception:
            # Non-fatal: log and return None so caller can decide what to do
            logger.exception("Error getting frames from RealSense camera:")
            return None, None

    def stop(self):
        """Stop the RealSense pipeline and release resources."""
        try:
            self.pipeline.stop()
            if self.verbose:
                logger.info("RealSense pipeline stopped.")
        except Exception:
            logger.exception("Error stopping RealSense pipeline:")
