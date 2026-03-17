# OST Suite 

<p align="left"><img src="assets/logo-main-transp.png" alt="OST Suite Logo" width="250"></p>

#### Osteo-Skeletal Tracker & Telemetry

A high-performance, distributed workstation for recording, processing, and visualizing multi-modal skeletal and micro-Doppler motion data

![Version](https://img.shields.io/badge/version-0.3.0-blue)
![Python](https://img.shields.io/badge/python-3.11-green)
![ZeroMQ](https://img.shields.io/badge/ZeroMQ-Curve25519-red)
![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10.21-teal)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

---

## System Architecture

OST Suite now utilizes a **Secure Publisher/Subscriber** model via ZeroMQ, allowing the hardware capture node and the visualization node to run independently—either on the same machine or across a local network. 
All network telemetry is secured via **Curve25519 Elliptic Curve Encryption**.
---

## Features

### OST Publisher (`stream.py`)
The hardware-interfacing node. Captures and broadcasts data in real-time.
* **TI mmWave Radar Support:** Auto-detects COM ports and parses raw byte streams into Range-Doppler Heatmaps.
* **RealSense & MediaPipe:** Captures depth-aligned video and computes 3D skeletal joint coordinates (33 landmarks).
* **Disk Recording:** Saves synchronized, headless data streams locally (Parquet/JSON + JPEG) while broadcasting.

### OST Viewer (`view.py`)
The visualization node. Receives and renders telemetry securely.
* **Live Micro-Doppler Heatmap:** PyQtGraph-powered radar visualization with dynamic noise-floor scaling and custom Jet colormaps.
* **Live Camera Feed:** Real-time video playback with skeleton overlays.
* **Network Flexible:** Connects to localhost or external IPs seamlessly.

---

## 📥 Installation & Setup

### 1. Clone the Repository

### 2. Create a Virtual Environment

### 3. Install Dependencies

### 4. Generate Security Keys (First-Time Setup)
Because OST uses CurveZMQ for encryption, you must generate a pair of cryptographic keys before streaming data.
```bash
python keygen.py
```
Copy the terminal output and paste it at the bottom of your `settings.ini` file under the `[Security]` block.

---

## 🚀 Usage

The suite is driven by a central `settings.ini` file. Ensure your radar configuration files and network ports are correctly defined there before running.

### Start the Hardware Node (Publisher)
Plug in your RealSense camera and TI Radar, then run:
```bash
python stream.py
```
### Start the Telemetry Dashboard (Viewer)
Open a new terminal window (or run on a different computer on the same network) and run:
```bash
python view.py
```
---