import csv
import os
from datetime import datetime

class Writer:
    def __init__(self, filename=None, num_joints=33, include_z=True, metadata=None):
        """
        metadata: dict (optional) - Dictionary of data to save at top of file
                  e.g., {"Subject": "A1", "Comments": "Walking test"}
        """
        if filename is None:
            os.makedirs("records", exist_ok=True)
            filename = f"records/joints_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        self.filename = filename
        self.num_joints = num_joints
        self.include_z = include_z

        # Check if file exists before we open it
        file_exists = os.path.exists(filename)
        
        self.file = open(filename, 'a', newline='')

        # --- 1. Write Metadata (Only if new file) ---
        if not file_exists and metadata:
            self.file.write("# SESSION METADATA\n")
            for key, value in metadata.items():
                # Write as comments so it doesn't break CSV parsers
                self.file.write(f"# {key}: {value}\n")
            self.file.write("# ----------------\n")

        # --- 2. Setup CSV Columns ---
        self.keys = []
        for i in range(num_joints):
            # Pixel space
            self.keys.append(f"joint_{i}_px")
            self.keys.append(f"joint_{i}_py")

            # Metric space
            self.keys.append(f"joint_{i}_x")
            self.keys.append(f"joint_{i}_y")
            if include_z:
                self.keys.append(f"joint_{i}_z")

        self.writer = csv.DictWriter(
            self.file,
            fieldnames=["timestamp"] + self.keys
        )

        # Write header only if file didn't exist
        if not file_exists:
            self.writer.writeheader()

    def log(self, joints_dict):
        row = {"timestamp": datetime.now().isoformat()}

        for i in range(self.num_joints):
            joint = joints_dict.get(i, {})

            # Pixel coords
            px, py = joint.get("pixel", (None, None))
            row[f"joint_{i}_px"] = px if px is not None else ""
            row[f"joint_{i}_py"] = py if py is not None else ""

            # Metric coords
            mx, my, mz = joint.get("metric", (None, None, None))
            row[f"joint_{i}_x"] = mx if mx is not None else ""
            row[f"joint_{i}_y"] = my if my is not None else ""
            if self.include_z:
                row[f"joint_{i}_z"] = mz if mz is not None else ""

        self.writer.writerow(row)
        
        # Flush every frame so data isn't lost if crashed
        self.file.flush()

    def close(self):
        """Flush remaining data and close the file."""
        if not self.file.closed:
            self.file.flush() # <--- FIXED: Was self.flush()
            self.file.close()