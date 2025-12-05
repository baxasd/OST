import numpy as np
import pyrealsense2 as rs
import logging

logger = logging.getLogger(__name__)


# Helper utilities for working with Intel RealSense depth frames.
# These functions provide small, well-documented wrappers around common
# RealSense operations used throughout the project (sampling and
# deprojection). They intentionally return `None` when an operation
# fails so callers can handle missing data gracefully.


def get_mean_depth(depth_frame, px, py, w, h, patch=1):
    """Compute the mean depth (in meters) from a small neighborhood.

    Parameters
    - depth_frame: RealSense depth frame with method `get_distance(x, y)`.
    - px, py: Center pixel coordinates (ints) to sample around.
    - w, h: Valid image width and height used for bounds checking.
    - patch: Radius (in pixels) around the center to sample. For example,
      patch=1 samples a (2*1+1)x(2*1+1) = 3x3 patch.

    Returns
    - Mean depth in meters across valid samples, or `None` if no valid
      depth values are found or an error occurs.

    Notes
    - RealSense returns 0.0 for invalid/no-depth pixels; these are
      ignored when computing the mean.
    """
    try:
        values = []

        # Iterate over the square patch centered at (px, py)
        for dx in range(-patch, patch + 1):
            for dy in range(-patch, patch + 1):
                x, y = px + dx, py + dy

                # Skip coordinates that fall outside the image
                if 0 <= x < w and 0 <= y < h:
                    # `get_distance` returns depth in meters (0.0 if invalid)
                    d = depth_frame.get_distance(x, y)

                    # Only keep positive (valid) depths
                    if d > 0:
                        values.append(d)

        # Return the mean of collected valid depths, or None if empty
        return np.mean(values) if values else None

    except Exception:
        # Log a helpful message for debugging, but don't raise here
        logger.exception("Error getting mean depth:")
        return None


def deproject(depth_intrin, px, py, depth):
    """Convert a pixel + depth to a 3D point in camera coordinates.

    Parameters
    - depth_intrin: an `rs.intrinsics` object describing the depth camera
      intrinsics (typically obtained via `profile.as_video_stream_profile().get_intrinsics()`).
    - px, py: Pixel coordinates.
    - depth: Depth value in meters at the pixel.

    Returns
    - A 3-element list [X, Y, Z] giving the 3D point in the camera frame,
      or `None` if deprojection fails.

    This is a thin wrapper around `rs.rs2_deproject_pixel_to_point` that
    centralizes error handling for callers.
    """
    try:
        # rs2_deproject_pixel_to_point expects the pixel as a two-element
        # sequence and the depth in meters.
        return rs.rs2_deproject_pixel_to_point(depth_intrin, [px, py], depth)


    except Exception:
      logger.exception("Error in deprojection:")
      return None


