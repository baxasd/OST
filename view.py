import sys
import logging
import zmq
import json
import numpy as np
import scipy.ndimage as ndimage
import pyqtgraph as pg
import configparser

from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QLabel
from PyQt6.QtGui import QPixmap

from core.radar.parser import RadarConfig
from core.ui.theme import COLOR_MAIN_BG, COLOR_TEXT 

# Basic logger for terminal feedback
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("Viewer")

# Pull settings from the ini file so we don't hardcode network/hardware details
config = configparser.ConfigParser()
config.read('settings.ini')

HW_CFG_FILE     = config['Hardware']['radar_cfg_file']
ZMQ_RADAR_PORT  = config['Network'].get('zmq_radar_port', '5555')
ZMQ_CAM_PORT    = config['Network'].get('zmq_camera_port', '5556')

VIEW_IP         = config['Viewer']['default_ip']
MAX_RANGE       = float(config['Viewer']['max_range_m'])
CMAP            = config['Viewer']['cmap']
DISP_LOW_PCT    = float(config['Viewer']['low_pct'])
DISP_HIGH_PCT   = float(config['Viewer']['high_pct'])
SMOOTH_GRID     = int(config['Viewer']['smooth_grid_size'])

class ZmqRadarWorker(QThread):
    """Listens to the radar ZMQ socket and pre-processes the raw bytes before sending to UI."""
    new_frame = pyqtSignal(np.ndarray, float, float) 
    error     = pyqtSignal(str)

    def __init__(self, cfg: RadarConfig, publisher_ip: str, zoom_y: float, zoom_x: float):
        super().__init__()
        self.cfg = cfg
        self.running = True
        self.zoom_y = zoom_y
        self.zoom_x = zoom_x
        
        # Calc the expected payload size based on the radar profile
        self.num_range_bins = cfg.numRangeBins
        self.num_vel_bins   = cfg.numLoops
        self.max_bin = min(int(MAX_RANGE / cfg.rangeRes), cfg.numRangeBins)
        self._expected_size = self.num_range_bins * self.num_vel_bins

        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect(f"tcp://{publisher_ip}:{ZMQ_RADAR_PORT}")
        self.socket.setsockopt_string(zmq.SUBSCRIBE, "")

    def run(self):
        while self.running:
            try:
                # Sleep briefly if no data is available to prevent maxing out the CPU
                if self.socket.poll(100) == 0:
                    continue 

                msg = self.socket.recv(flags=zmq.NOBLOCK)
                raw = np.frombuffer(msg, dtype=np.uint16)
                
                # Drop malformed packets
                if raw.size != self._expected_size: continue

                # Reshape, clip to max range, and convert to dB
                rd = raw.astype(np.float32).reshape(self.num_range_bins, self.num_vel_bins)
                rd = rd[:self.max_bin, :]
                display = 20.0 * np.log10(np.abs(np.fft.fftshift(rd, axes=1)) + 1e-6)
                
                # Upscale the image for a smoother heatmap
                smooth = ndimage.zoom(display, (self.zoom_y, self.zoom_x), order=1)
                
                # Calc dynamic color limits based on percentiles
                lo = float(np.percentile(smooth, DISP_LOW_PCT))
                hi = float(np.percentile(smooth, DISP_HIGH_PCT))
                if lo >= hi: hi = lo + 0.1

                self.new_frame.emit(smooth, lo, hi)
                
            except Exception as e:
                self.error.emit(str(e))

    def stop(self):
        """Cleanly kill the ZMQ context on exit."""
        self.running = False
        self.wait()
        self.socket.close()
        self.context.term()

class ZmqCameraWorker(QThread):
    """Listens to the camera ZMQ socket for JSON metadata and JPEG bytes."""
    new_frame = pyqtSignal(dict, bytes)
    error     = pyqtSignal(str)

    def __init__(self, publisher_ip: str):
        super().__init__()
        self.running = True
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect(f"tcp://{publisher_ip}:{ZMQ_CAM_PORT}")
        self.socket.setsockopt_string(zmq.SUBSCRIBE, "")

    def run(self):
        while self.running:
            try:
                if self.socket.poll(100) == 0:
                    continue

                # Unpack the multipart message
                msg_parts = self.socket.recv_multipart(flags=zmq.NOBLOCK)
                if len(msg_parts) == 2:
                    meta_dict = json.loads(msg_parts[0].decode('utf-8'))
                    img_bytes = msg_parts[1]
                    self.new_frame.emit(meta_dict, img_bytes)
                    
            except Exception as e:
                self.error.emit(str(e))

    def stop(self):
        self.running = False
        self.wait()
        self.socket.close()
        self.context.term()

class LiveViewerWindow(QMainWindow):
    """Main UI Window."""
    def __init__(self, cfg: RadarConfig, publisher_ip: str):
        super().__init__()
        self.cfg = cfg
        self.publisher_ip = publisher_ip
        
        self.zoom_y = 1.0
        self.zoom_x = 1.0

        self.setWindowTitle(f"OST Live Telemetry | {self.publisher_ip}")
        self.setFixedSize(960, 400) # Lock size to maintain aspect ratios

        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {COLOR_MAIN_BG};
            }}
            #CamFeed {{
                background-color: transparent; 
                border: none;
            }}
        """)

        # Cache axis limits
        self.max_range_val = min(int(MAX_RANGE / self.cfg.rangeRes), self.cfg.numRangeBins) * self.cfg.rangeRes
        self.dop_max = self.cfg.dopMax
        
        self._precompute_zoom() 
        self._build_ui()
        self._start_workers()

    def _precompute_zoom(self):
        """Calc scaling factors based on target grid size."""
        src_rows = min(int(MAX_RANGE / self.cfg.rangeRes), self.cfg.numRangeBins)
        src_cols = self.cfg.numLoops
        self.zoom_y = max(SMOOTH_GRID, src_rows) / src_rows
        self.zoom_x = max(SMOOTH_GRID, src_cols) / src_cols

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10) 
        main_layout.setSpacing(10) 
        
        # ── Left Side: Radar Plot ──
        self.plot_radar = pg.PlotWidget()
        self.plot_radar.setBackground(COLOR_MAIN_BG)
        self.plot_radar.setTitle(None)
        
        # Style Axes
        styles = {'color': COLOR_TEXT, 'font-size': '12px', 'font-family': 'Segoe UI'}
        self.plot_radar.setLabel("left", "Range", units="m", **styles)
        self.plot_radar.setLabel("bottom", "Velocity", units="m/s", **styles)
        
        # Open up the graph by dropping top/right bounds
        self.plot_radar.getPlotItem().hideAxis('top')
        self.plot_radar.getPlotItem().hideAxis('right')
        
        pen = pg.mkPen(color=COLOR_TEXT, width=1)
        self.plot_radar.getAxis('left').setPen(pen)
        self.plot_radar.getAxis('left').setTextPen(COLOR_TEXT)
        self.plot_radar.getAxis('bottom').setPen(pen)
        self.plot_radar.getAxis('bottom').setTextPen(COLOR_TEXT)
        
        self.plot_radar.showGrid(x=True, y=True, alpha=0.2) 
        
        # Radar Image Layer
        self.img_radar = pg.ImageItem()
        self.img_radar.setColorMap(pg.colormap.get(CMAP))
        self.plot_radar.addItem(self.img_radar)
        
        # Lock axes down
        self.plot_radar.setXRange(-self.dop_max, self.dop_max, padding=0)
        self.plot_radar.setYRange(0, self.max_range_val, padding=0)
        
        main_layout.addWidget(self.plot_radar, stretch=1)

        # ── Right Side: Camera Feed ──
        self.lbl_cam_feed = QLabel()
        self.lbl_cam_feed.setObjectName("CamFeed") 
        # Pin to top to prevent vertical floating
        self.lbl_cam_feed.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        
        main_layout.addWidget(self.lbl_cam_feed, stretch=1)

    def _start_workers(self):
        self.w_radar = ZmqRadarWorker(self.cfg, self.publisher_ip, self.zoom_y, self.zoom_x)
        self.w_radar.new_frame.connect(self._on_radar_frame)
        self.w_radar.start()

        self.w_cam = ZmqCameraWorker(self.publisher_ip)
        self.w_cam.new_frame.connect(self._on_cam_frame)
        self.w_cam.start()

    def _on_radar_frame(self, smooth_matrix: np.ndarray, lo: float, hi: float):
        """Update heatmap pixels and force axis re-alignment."""
        self.img_radar.setImage(smooth_matrix, autoLevels=False, levels=(lo, hi))
        align_rect = pg.QtCore.QRectF(
            -self.dop_max,         
            0,                     
            self.dop_max * 2.0,    
            self.max_range_val     
        )
        self.img_radar.setRect(align_rect)

    def _on_cam_frame(self, meta: dict, img_bytes: bytes):
        """Convert jpeg bytes to Pixmap and scale to fit label."""
        pixmap = QPixmap()
        pixmap.loadFromData(img_bytes)
        
        lbl_w = self.lbl_cam_feed.width()
        lbl_h = self.lbl_cam_feed.height()
        if lbl_w > 0 and lbl_h > 0:
            self.lbl_cam_feed.setPixmap(pixmap.scaled(lbl_w, lbl_h, Qt.AspectRatioMode.KeepAspectRatio))

    def closeEvent(self, event):
        log.info("SHUTTING DOWN...")
        self.w_radar.stop()
        self.w_cam.stop()
        event.accept()

def main():
    ip_input = input(f"\nEnter Stream IP. Leave blank for localhost: ").strip()
    ip = VIEW_IP if not ip_input else ip_input
            
    app = QApplication.instance() or QApplication(sys.argv)
    pg.setConfigOptions(imageAxisOrder="row-major", antialias=True)
    
    try:
        cfg = RadarConfig(HW_CFG_FILE)
        window = LiveViewerWindow(cfg, ip)
        window.show()
        app.exec()
    except Exception as e:
        log.error(f"Failed to initialize: {e}")

if __name__ == "__main__":
    main()