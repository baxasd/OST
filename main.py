import cv2
import time
from src.camera.realsense import RealSenseCamera
from src.pose.pose import PoseEstimator
from src.utils.depth import get_mean_depth, deproject
from src.utils.csvWriter import Writer

def main(model=1):
    """Main function to run the system, logging raw joint coordinates only."""

    print("[INFO] Initializing camera...")

    # Initialize objects
    cam = RealSenseCamera(verbose=True)
    pose_est = PoseEstimator(model)
    write = Writer()

    # Initialize variables
    prev_time = time.time()
    frame_count = 0
    filters = {}

    try:
        while True:
    
            color_image, depth_frame = cam.get_frames()
            if color_image is None:
                continue

            h, w, _ = color_image.shape
            depth_intrin = depth_frame.profile.as_video_stream_profile().intrinsics

            # Pose estimation
            results = pose_est.estimate(color_image)

            # If commented out, disables skeleton display
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

                    landmarks_dict[id] = (X, Y, Z)

                    cv2.putText(color_image,
                                    f"{id}: ({X:.2f},{Y:.2f},{Z:.2f})",
                                    (px, py - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX,
                                    0.4, (0, 255, 255), 1, cv2.LINE_AA)
                                        
                # Log raw joint coordinates to CSV
                write.log(landmarks_dict)


            curr_time = time.time()
            frame_count += 1
            
            # Calculate and display FPS
            fps = 1.0 / (curr_time - prev_time)
            prev_time = curr_time
            
            # Display FPS on screen
            cv2.putText(annotated_image, 
                        f"FPS: {fps:.1f}", 
                        (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 
                        0.4, (0, 255, 255), 1, cv2.LINE_AA) 
            
            # Display skeleton, uncomment to enable. Additionally remove comment from annotated_image line above.
            cv2.imshow("3D Pose Skeleton", annotated_image)
            cv2.waitKey(1)           

    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user. Shutting down.")

    finally:
        write.close()
        cam.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
