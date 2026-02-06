import customtkinter as ctk
from PIL import Image, ImageTk
import cv2
import time
import datetime
import os

# Safe Import
try:
    from src.camera.realsense import RealSenseCamera
    from src.pose.pose import PoseEstimator
    from src.utils.depth import get_mean_depth, deproject
    from src.utils.csvWriter import Writer
    MODULES_LOADED = True
except ImportError as e:
    print(f"[ERROR] Could not import modules: {e}")
    MODULES_LOADED = False

class PoseApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- 1. Window Setup ---
        self.title("OSTracker - V1.0")
        self.geometry("820x500")
        ctk.set_appearance_mode("Dark")
        
        # Grid layout: Sidebar (col 0), Main Video (col 1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- 2. Sidebar (Controls) ---
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        # Logo & FPS
        self.logo_label = ctk.CTkLabel(self.sidebar, text="OSTracker", font=ctk.CTkFont(size=22, weight="bold"))
        self.logo_label.pack(padx=20, pady=(20, 5))
        
        self.lbl_subtitle = ctk.CTkLabel(self.sidebar, text="Osteo-Skeletal Pose Tracker", font=ctk.CTkFont(family="Consolas", size=14),)
        self.lbl_subtitle.pack(padx=20, pady=(0, 10), anchor="w")

        # Metadata Section
        self.create_sidebar_separator("SESSION METADATA")

        self.lbl_fps = ctk.CTkLabel(self.sidebar, text="FPS: 00", font=ctk.CTkFont(family="Consolas", size=14), text_color="white")
        self.lbl_fps.pack(padx=20, pady=(5, 0), anchor="w")


        self.lbl_filename = ctk.CTkLabel(self.sidebar, text="Filename / ID:", anchor="w")
        self.lbl_filename.pack(padx=20, pady=(5, 0), fill="x")
        
        default_name = datetime.datetime.now().strftime("%Y-%m-%d_Session")
        self.entry_filename = ctk.CTkEntry(self.sidebar, placeholder_text="Enter ID...")
        self.entry_filename.insert(0, default_name)
        self.entry_filename.pack(padx=20, pady=5, fill="x")

        self.lbl_comments = ctk.CTkLabel(self.sidebar, text="Comments:", anchor="w")
        self.lbl_comments.pack(padx=20, pady=(5, 0), fill="x")
        self.entry_comments = ctk.CTkEntry(self.sidebar, placeholder_text="Optional notes")
        self.entry_comments.pack(padx=20, pady=5, fill="x")

        # Settings Section
        self.create_sidebar_separator("CONFIGURATION")

        self.lbl_model = ctk.CTkLabel(self.sidebar, text="Model Accuracy:", anchor="w")
        self.lbl_model.pack(padx=20, pady=(5, 0), fill="x")
        self.model_opt = ctk.CTkOptionMenu(self.sidebar, 
                                           values=["Light (Fast)", "Medium (Balanced)", "Heavy (Precise)"],
                                           command=self.change_model)
        self.model_opt.set("Medium (Balanced)")
        self.model_opt.pack(padx=20, pady=5, fill="x")

        # Recording Section (Bottom)
        self.sidebar_bottom = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.sidebar_bottom.pack(side="bottom", fill="x", pady=20)

        self.btn_record = ctk.CTkButton(self.sidebar_bottom, text="START RECORDING", 
                                        fg_color="#27AE60", hover_color="#2ECC71",
                                        height=40, font=ctk.CTkFont(weight="bold"),
                                        command=self.toggle_recording)
        self.btn_record.pack(padx=20, pady=5, fill="x")

        self.lbl_status = ctk.CTkLabel(self.sidebar_bottom, text="System Ready", text_color="gray")
        self.lbl_status.pack(padx=20, pady=5)

        # --- 3. Video Display Area ---
        # A container frame that stretches to fill available space
        self.video_container = ctk.CTkFrame(self, corner_radius=0, fg_color="#1a1a1a")
        self.video_container.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        
        # The label that actually holds the image (centered in container)
        self.video_label = ctk.CTkLabel(self.video_container, text="Initializing Camera...", font=ctk.CTkFont(size=16))
        self.video_label.place(relx=0.5, rely=0.5, anchor="center")

        # --- 4. Backend Logic ---
        self.is_recording = False
        self.writer = None
        self.prev_time = 0
        self.cam = None
        self.estimator = None

        if MODULES_LOADED:
            self.init_camera()
        else:
            self.video_label.configure(text="Error: Source modules not found.")

    def create_sidebar_separator(self, text):
        f = ctk.CTkFrame(self.sidebar, height=2, fg_color="gray30")
        f.pack(fill="x", padx=20, pady=(5, 5))
        l = ctk.CTkLabel(self.sidebar, text=text, font=ctk.CTkFont(size=10, weight="bold"), text_color="gray60")
        l.pack(padx=20, pady=0, anchor="w")

    def init_camera(self):
        try:
            self.cam = RealSenseCamera(width=640, height=480, fps=30)
            self.estimator = PoseEstimator(model=1)
            self.update_frame()
        except Exception as e:
            print(f"Camera Error: {e}")
            self.video_label.configure(text=f"Camera Not Found!\n\nCheck connection.\n{e}", text_color="#FF5555")

    def toggle_recording(self):
        if self.cam is None: return

        self.is_recording = not self.is_recording

        if self.is_recording:
            user_name = self.entry_filename.get().strip()
            if not user_name: user_name = "Untitled"
            safe_name = "".join([c for c in user_name if c.isalnum() or c in (' ', '-', '_')]).strip()
            filename = f"records/{safe_name}.csv"
            
            try:
                os.makedirs("records", exist_ok=True)
                # Collect Metadata
                meta_data = {
                    "Filename_ID": safe_name,
                    "Date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Comments": self.entry_comments.get().strip()
                }

                self.writer = Writer(filename=filename, metadata=meta_data)
                
                self.btn_record.configure(text="STOP RECORDING", fg_color="#C0392B", hover_color="#E74C3C")
                self.lbl_status.configure(text=f"Rec: {safe_name}.csv", text_color="#FF5555")
                self.entry_filename.configure(state="disabled") 
                
            except Exception as e:
                self.is_recording = False
                self.lbl_status.configure(text=f"Error: {e}", text_color="red")
                print(f"Writer Error: {e}")

        else:
            if self.writer:
                self.writer.close()
                self.writer = None
            
            self.btn_record.configure(text="START RECORDING", fg_color="#27AE60", hover_color="#2ECC71")
            self.lbl_status.configure(text="Saved successfully", text_color="#2ECC71")
            self.entry_filename.configure(state="normal")

    def change_model(self, choice):
        if not self.estimator: return
        model_map = {"Light (Fast)": 0, "Medium (Balanced)": 1, "Heavy (Precise)": 2}
        self.estimator = PoseEstimator(model=model_map.get(choice, 1))

    def update_frame(self):
        # FPS
        curr_time = time.time()
        fps = 1 / (curr_time - self.prev_time) if (curr_time - self.prev_time) > 0 else 0
        self.prev_time = curr_time
        self.lbl_fps.configure(text=f"FPS: {int(fps)}")

        try:
            color_image, depth_frame = self.cam.get_frames()
        except Exception:
            color_image = None
        
        if color_image is not None:
            # Detection & Recording Logic
            pts = self.estimator.estimate(color_image)
            if pts is not None:
                for x, y, _ in pts:
                    cv2.circle(color_image, (int(x), int(y)), 4, (0, 255, 0), -1)

                if self.is_recording and self.writer and depth_frame:
                    depth_intrin = depth_frame.profile.as_video_stream_profile().intrinsics
                    landmarks_dict = {}
                    h, w, _ = color_image.shape
                    for j, (px, py, _) in enumerate(pts):
                        px, py = int(px), int(py)
                        if 0 <= px < w and 0 <= py < h:
                            depth = get_mean_depth(depth_frame, px, py, w, h)
                            if depth:
                                X, Y, Z = deproject(depth_intrin, px, py, depth)
                                landmarks_dict[j] = {"pixel": (px, py), "metric": (X, Y, Z)}
                    if landmarks_dict:
                        self.writer.log(landmarks_dict)

            # --- DYNAMIC RESIZING LOGIC ---
            # 1. Get current size of the container frame
            # (Note: winfo_width() returns 1 at start, so we use max(1, ...))
            frame_w = max(1, self.video_container.winfo_width())
            frame_h = max(1, self.video_container.winfo_height())

            # 2. Subtract Margin (10px on all sides = 20px total)
            avail_w = frame_w - 20
            avail_h = frame_h - 20

            # 3. Calculate Aspect Ratio Fit (Target is 4:3 = 1.333)
            if avail_w > 0 and avail_h > 0:
                target_ratio = 4 / 3
                container_ratio = avail_w / avail_h

                if container_ratio > target_ratio:
                    # Container is wider than 4:3 -> Constraint by Height
                    new_h = avail_h
                    new_w = int(new_h * target_ratio)
                else:
                    # Container is taller than 4:3 -> Constraint by Width
                    new_w = avail_w
                    new_h = int(new_w / target_ratio)
            else:
                new_w, new_h = 640, 480 # Fallback

            # 4. Display
            img = cv2.cvtColor(color_image, cv2.COLOR_BGR2RGB)
            img_pil = Image.fromarray(img)
            ctk_img = ctk.CTkImage(light_image=img_pil, size=(new_w, new_h))
            
            self.video_label.configure(image=ctk_img, text="")
            self.video_label.image = ctk_img

        self.after(10, self.update_frame)

    def on_close(self):
        if self.writer: self.writer.close()
        if self.cam: self.cam.stop()
        self.destroy()

if __name__ == "__main__":
    app = PoseApp()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()