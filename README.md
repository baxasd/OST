# OST (Open Source Tracker) V1.0

**Scientific Motion Analysis Suite**

OST is a modular Python-based workstation designed for capturing, processing, and analyzing biomechanical motion data. It leverages Intel RealSense depth technology and MediaPipe Pose estimation to provide precise, real-time 3D skeletal tracking and scientific metrics.

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.8%2B-green)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

---

## 🚀 Key Features

### 1. Data Capture (Recorder)
* **Hardware Support:** Native integration with Intel RealSense cameras (D400 Series).
* **Real-time Tracking:** 33-point skeletal tracking using MediaPipe Pose (Lite/Full/Heavy models).
* **3D Metric Data:** Converts 2D pixel coordinates into real-world 3D metric (meters) using depth deprojection.
* **Robust Logging:** Saves Session Metadata (Subject ID, Activity, Temperature) automatically.

### 2. Data Studio (Processing)
* **Automated Diagnostics:** Detects frame drops, tracking loss (zeros), and tracking gaps.
* **Repair Pipeline:** Smart gap filling using Linear or Spline interpolation.
* **Signal Smoothing:** Savitzky-Golay filtering to remove jitter while preserving peak magnitudes.

### 3. Visualizer (Analysis)
* **Scientific Dashboard:** Frame-by-frame analysis with synchronized graphs.
* **Biomechanics Metrics:** Real-time calculation of:
    * Trunk Lean (Vertical Reference)
    * Knee Flexion (Left/Right)
* **Professional UI:** Dark-themed, high-contrast visualization designed for lab environments.

---

## 🛠️ Installation

### Prerequisites
* Python 3.8 or higher
* Intel RealSense SDK 2.0 (`librealsense`)