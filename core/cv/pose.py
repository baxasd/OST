import cv2
import mediapipe as mp

class PoseEstimator:
    """
    Mediapipe Pose Estimator with aspect-ratio preserving resize.
    Essential for consistent detection across different camera resolutions.
    """
    def __init__(self, model_complexity=1, min_conf=0.5, target_size=512):
        self.target_size = target_size
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=model_complexity,
            min_detection_confidence=min_conf,
            min_tracking_confidence=min_conf
        )

    def _resize_with_pad(self, img):
        """Resizes image to target_size square while maintaining aspect ratio."""
        h, w = img.shape[:2]
        scale = self.target_size / max(h, w)
        nh, nw = int(h * scale), int(w * scale)

        resized = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LINEAR)

        # Calculate padding to make it square
        top = (self.target_size - nh) // 2
        bottom = self.target_size - nh - top
        left = (self.target_size - nw) // 2
        right = self.target_size - nw - left

        padded = cv2.copyMakeBorder(resized, top, bottom, left, right,
                                    borderType=cv2.BORDER_CONSTANT, value=(0,0,0))

        return padded, scale, left, top, (w, h)

    def _restore_coords(self, landmarks, scale, pad_x, pad_y):
        """Maps normalized landmarks back to the original image coordinates."""
        restored = []
        for lm in landmarks:
            # Reverse the padding and scaling
            x = (lm.x * self.target_size - pad_x) / scale
            y = (lm.y * self.target_size - pad_y) / scale
            # Z is relative, but we scale it to match X/Y scale roughly
            z = lm.z / scale     
            restored.append((x, y, z))
        return restored

    def estimate(self, image):
        """
        Returns list of (x, y, z) tuples in ORIGINAL image pixels/scale.
        Returns None if no pose detected.
        """
        try:
            # 1. Pre-process (Resize & Pad)
            img_padded, scale, pad_x, pad_y, _ = self._resize_with_pad(image)
            img_rgb = cv2.cvtColor(img_padded, cv2.COLOR_BGR2RGB)
            
            # 2. Inference
            results = self.pose.process(img_rgb)
            if not results.pose_landmarks:
                return None

            # 3. Post-process (Restore Coordinates)
            return self._restore_coords(
                results.pose_landmarks.landmark, 
                scale, pad_x, pad_y
            )

        except Exception as e:
            print(f"[Pose Error] {e}")
            return None