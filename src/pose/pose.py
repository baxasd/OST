import cv2
import mediapipe as mp
import numpy as np

class PoseEstimator:
    """Mediapipe Pose Estimator with optional resizing to stabilize detection."""

    def __init__(self, model=1,
                 target_size=512,  # <<< resize target (square, stable)
                 static_image_mode=False,
                 min_detection_confidence=0.5,
                 min_tracking_confidence=0.5):

        self.target_size = target_size

        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=static_image_mode,
            model_complexity=model,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

        self.mp_draw = mp.solutions.drawing_utils
        self.draw_styles = mp.solutions.drawing_styles


    # -------------------------------------------
    # Resize while keeping aspect ratio
    # -------------------------------------------
    def _resize_with_pad(self, img):
        h, w = img.shape[:2]
        scale = self.target_size / max(h, w)

        nh = int(h * scale)
        nw = int(w * scale)

        resized = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LINEAR)

        # pad to target_size x target_size
        top = (self.target_size - nh) // 2
        bottom = self.target_size - nh - top
        left = (self.target_size - nw) // 2
        right = self.target_size - nw - left

        padded = cv2.copyMakeBorder(resized, top, bottom, left, right,
                                    borderType=cv2.BORDER_CONSTANT, value=(0,0,0))

        return padded, scale, left, top, (w, h)


    # -------------------------------------------
    # Convert resized-landmarks back to original image space
    # -------------------------------------------
    def _restore_coords(self, landmarks, scale, pad_x, pad_y, orig_size):
        orig_w, orig_h = orig_size

        restored = []
        for lm in landmarks:
            x = (lm.x * self.target_size - pad_x) / scale
            y = (lm.y * self.target_size - pad_y) / scale
            z = lm.z / scale     # z is also scaled consistently

            restored.append([x, y, z])
        return np.array(restored)


    # -------------------------------------------
    # Pose estimation
    # -------------------------------------------
    def estimate(self, image):
        try:
            img_resized, scale, pad_x, pad_y, orig_size = self._resize_with_pad(image)
            img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
            results = self.pose.process(img_rgb)

            if not results.pose_landmarks:
                return None

            # Convert MP landmarks to array
            lm = results.pose_landmarks.landmark

            pts = self._restore_coords(lm, scale, pad_x, pad_y, orig_size)

            return pts   # <--- return Nx3 numpy array in original coordinates

        except Exception as e:
            print("Pose estimation error:", e)
            return None


    # -------------------------------------------
    # Draw landmarks properly on original image
    # -------------------------------------------
    def draw_landmarks(self, image, pts):
        if pts is None:
            return image

        for x, y, _ in pts:
            cv2.circle(image, (int(x), int(y)), 3, (0,255,0), -1)

        return image
