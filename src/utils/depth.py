import numpy as np
import pyrealsense2 as rs

def get_mean_depth(depth_frame, px, py, w, h, patch=1):
    try:
        
        values = []
        for dx in range(-patch,patch+1):
            for dy in range(-patch,patch+1):
                x,y = px+dx,py+dy
                if 0 <= x < w and 0 <= y < h:
                    d = depth_frame.get_distance(x, y)
                    if d > 0:
                        values.append(d)
        return np.mean(values) if values else None
    except Exception as e:
        print("Error getting mean depth:", e)
        return None

def deproject(depth_intrin, px, py, depth):
    try:
        return rs.rs2_deproject_pixel_to_point(depth_intrin, [px, py], depth)
    except Exception as e:
        print("Error in deprojection:", e)
        return None

