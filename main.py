import cv2
from src.camera.realsense import RealSenseCamera
from src.pose.pose import PoseEstimator
from src.utils.depth import get_mean_depth, deproject
from src.utils.writer import Writer

def main(model=1):
    print("[INFO] Initializing camera...")

    cam = RealSenseCamera(verbose=True)
    pose_estimator = PoseEstimator(model=model)
    logger = Writer()

    try:
        while True:
            color_image, depth_frame = cam.get_frames()
            
            if color_image is None:
                continue

            h, w, _ = color_image.shape
            depth_intrin = depth_frame.profile.as_video_stream_profile().intrinsics

            # Pose estimation (returns Nx3 array of pixel-space coords)
            pts = pose_estimator.estimate(color_image)
            if pts is None:
                continue

            # Build dictionary of 3D joints from depth
            landmarks_dict = {}
            for j, (px, py, _) in enumerate(pts):
                px = int(px)
                py = int(py)

                if px < 0 or px >= w or py < 0 or py >= h:
                    continue

                depth = get_mean_depth(depth_frame, px, py, w, h)
                if depth is None:
                    continue

                X, Y, Z = deproject(depth_intrin, px, py, depth)

                landmarks_dict[j] ={
                    "pixel": (px, py),
                    "metric": (X, Y, Z)
                }

                cv2.circle(color_image, (px, py), 3, (0,255,0), -1)

            # Save frame joints to CSV
            logger.log(landmarks_dict)

            # Display
            cv2.imshow("3D Pose Skeleton", color_image)
            cv2.waitKey(1)

    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user.")

    finally:
        logger.close()
        cam.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
