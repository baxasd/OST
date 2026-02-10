# ost/tools/record.py
import customtkinter as ctk
from PIL import Image
import cv2
import time
import datetime
import os

# --- NEW IMPORTS ---
from ost.sensors.realsense import RealSenseCamera
from ost.core.pose import PoseEstimator
from ost.core.transforms import get_mean_depth, deproject_pixel_to_point
from ost.core.io import SessionWriter

class RecorderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("OST Recorder")
        self.geometry("900x600")
        
        # GUI Setup (Simplified for brevity, keep your original styling!)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.sidebar = ctk.CTkFrame(self, width=200)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        self.btn_record = ctk.CTkButton(self.sidebar, text="START RECORDING", 
                                        fg_color="green", command=self.toggle_recording)
        self.btn_record.pack(pady=50, padx=20)
        
        self.video_label = ctk.CTkLabel(self, text="Waiting for Camera...")
        self.video_label.grid(row=0, column=1)

        # State
        self.is_recording = False
        self.writer = None
        self.cam = RealSenseCamera()
        self.pose = PoseEstimator()
        
        self.update_loop()

    def toggle_recording(self):
        self.is_recording = not self.is_recording
        if self.is_recording:
            self.btn_record.configure(text="STOP", fg_color="red")
            
            # Start Writer
            fname = f"records/ost_{int(time.time())}.csv"
            self.writer = SessionWriter(filename=fname)
            print(f"Recording to {fname}")
        else:
            self.btn_record.configure(text="RECORD", fg_color="green")
            if self.writer:
                self.writer.close()
                self.writer = None

    def update_loop(self):
        color_img, depth_frame = self.cam.get_frames()
        
        if color_img is not None:
            # 1. Pose Estimation
            landmarks = self.pose.estimate(color_img)
            
            h, w, _ = color_img.shape
            frame_data = {"timestamp": datetime.datetime.now().isoformat()}
            
            if landmarks:
                # Draw and Record
                depth_intrin = depth_frame.profile.as_video_stream_profile().intrinsics
                
                for i, lm in enumerate(landmarks):
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    cv2.circle(color_img, (cx, cy), 5, (0, 255, 0), -1)
                    
                    # Log Data if recording
                    if self.is_recording and self.writer:
                        dist = get_mean_depth(depth_frame, cx, cy, w, h)
                        if dist:
                            rw_point = deproject_pixel_to_point(depth_intrin, cx, cy, dist)
                            # Populate dictionary for Writer
                            frame_data[f"j{i}_px"] = cx
                            frame_data[f"j{i}_py"] = cy
                            frame_data[f"j{i}_x"] = rw_point[0]
                            frame_data[f"j{i}_y"] = rw_point[1]
                            frame_data[f"j{i}_z"] = rw_point[2]

                if self.is_recording and self.writer:
                    self.writer.write_frame(frame_data)

            # 2. Display
            img_pil = Image.fromarray(cv2.cvtColor(color_img, cv2.COLOR_BGR2RGB))
            ctk_img = ctk.CTkImage(light_image=img_pil, size=(640, 480))
            self.video_label.configure(image=ctk_img, text="")
        
        self.after(30, self.update_loop)

    def on_close(self):
        self.cam.stop()
        if self.writer: self.writer.close()
        self.destroy()

if __name__ == "__main__":
    app = RecorderApp()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()