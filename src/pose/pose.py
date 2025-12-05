"""Mediapipe-based pose estimator wrapper.

This small helper centralizes pose estimation and drawing utilities so
the rest of the application doesn't need to import Mediapipe directly.
"""


import cv2
import mediapipe as mp
import logging


class PoseEstimator:
    """Legacy Mediapipe Pose Estimator."""

    def __init__(self, model=1, static_image_mode=False, min_detection_confidence=0.5, min_tracking_confidence=0.5):
        # Prepare Mediapipe pose solution with the chosen model complexity
        self.mp_pose = mp.solutions.pose

        self.pose = self.mp_pose.Pose(
            static_image_mode=static_image_mode,
            model_complexity=model,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

        # Drawing helpers for rendering landmarks on frames
        self.mp_draw = mp.solutions.drawing_utils
        self.draw_styles = mp.solutions.drawing_styles

    def estimate(self, image):
        """Estimate pose landmarks in a BGR image and return results.

        Returns Mediapipe `results` object or `None` on failure.
        """
        try:
            # Mediapipe expects RGB images
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            results = self.pose.process(image_rgb)
            return results
        except Exception:
            logging.exception("Pose estimation error:")
            return None

    def draw_landmarks(self, image, results):
        """Draw landmarks with connections on the image and return it.

        Drawing is performed in-place on the provided `image` (BGR OpenCV
        array) to keep memory usage low.
        """
        if results and results.pose_landmarks:
            self.mp_draw.draw_landmarks(
                image,
                results.pose_landmarks,
                self.mp_pose.POSE_CONNECTIONS,
                self.draw_styles.get_default_pose_landmarks_style()
            )
        return image
