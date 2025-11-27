import cv2
from src.camera.realsense import RealSenseCamera
from src.pose.pose import PoseEstimator
from src.filters.kalmanFilter import KalmanFilter
from src.utils.depth import get_mean_depth, deproject
from src.utils.writer import Writer

def run_system(kalman=True, model=1):
    """Main function to run the system, logging raw joint coordinates only."""

    print("[INFO] Initializing camera...")

    # Initialize objects
    cam = RealSenseCamera(verbose=True)
    pose_est = PoseEstimator(model)
    kalman = KalmanFilter() if kalman else None
    logger = Writer()

    print(f"[INFO] Kalman filter {'ENABLED' if kalman else 'DISABLED'}")

    try:
        while True:
            color_image, depth_frame = cam.get_frames()
            if color_image is None:
                continue

            h, w, _ = color_image.shape
            depth_intrin = depth_frame.profile.as_video_stream_profile().intrinsics

            # Pose estimation
            results = pose_est.estimate(color_image)
            annotated_image = pose_est.draw_landmarks(color_image, results)

            landmarks_dict = {}
            if results.pose_landmarks:
                for id, lm in enumerate(results.pose_landmarks.landmark):
                    px, py = int(lm.x * w), int(lm.y * h)
                    if not (0 <= px < w and 0 <= py < h):
                        continue

                    depth = get_mean_depth(depth_frame, px, py, w, h)
                    if depth is None:
                        continue

                    X, Y, Z = deproject(depth_intrin, px, py, depth)

                    if kalman:
                        X, Y, Z = kalman.update(id, X, Y, Z)

                    landmarks_dict[id] = (X, Y, Z)

                # Log raw joint coordinates to CSV
                logger.log(landmarks_dict)

            # Display skeleton
            cv2.imshow("3D Pose Skeleton", annotated_image)

            # Exit on ESC
            if cv2.waitKey(1) & 0xFF == 27:
                break

    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user. Shutting down.")

    finally:
        logger.close()
        cam.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    run_system()
