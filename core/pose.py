# ost/core/pose.py
import cv2
import mediapipe as mp
import numpy as np

class PoseEstimator:
    """Mediapipe Pose Estimator wrapper."""
    def __init__(self, model_complexity=1, min_conf=0.5):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=model_complexity,
            min_detection_confidence=min_conf,
            min_tracking_confidence=min_conf
        )

    def estimate(self, image):
        """Returns normalized landmarks or None."""
        try:
            img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            results = self.pose.process(img_rgb)
            if not results.pose_landmarks:
                return None
            return results.pose_landmarks.landmark
        except Exception as e:
            print(f"Pose estimation error: {e}")
            return None
    
    # Note: I removed the resizing logic for brevity, 
    # but you can add it back if you find detection unstable without it.