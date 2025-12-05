import csv
import os
from datetime import datetime

class Writer:
    def __init__(self, filename=None, num_joints=33, include_z=True, batch_size=32):
        if filename is None:
            os.makedirs("records", exist_ok=True)
            filename = f"records/joints_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        self.filename = filename
        self.num_joints = num_joints
        self.include_z = include_z
        self.batch_size = batch_size
        self.buffer = []

        file_exists = os.path.exists(filename)
        self.file = open(filename, 'a', newline='')

        # Build field names
        self.keys = []
        for i in range(num_joints):
            self.keys.append(f"joint_{i}_x")
            self.keys.append(f"joint_{i}_y")
            if include_z:
                self.keys.append(f"joint_{i}_z")

        self.writer = csv.DictWriter(self.file, fieldnames=["timestamp"] + self.keys)
        if not file_exists:
            self.writer.writeheader()

    def log(self, joints_dict):
        """Add a single joint dict to the buffer."""
        row = {"timestamp": datetime.now().isoformat()}
        for i in range(self.num_joints):
            j = joints_dict.get(i)
            if j is None:
                row[f"joint_{i}_x"] = ""
                row[f"joint_{i}_y"] = ""
                if self.include_z:
                    row[f"joint_{i}_z"] = ""
            else:
                if isinstance(j, (list, tuple)):
                    row[f"joint_{i}_x"] = j[0] if len(j) > 0 else ""
                    row[f"joint_{i}_y"] = j[1] if len(j) > 1 else ""
                    if self.include_z:
                        row[f"joint_{i}_z"] = j[2] if len(j) > 2 else ""
                else:  # single int/float
                    row[f"joint_{i}_x"] = j
                    row[f"joint_{i}_y"] = ""
                    if self.include_z:
                        row[f"joint_{i}_z"] = ""
        self.buffer.append(row)

        # Flush automatically when buffer is full
        if len(self.buffer) >= self.batch_size:
            self.flush()

    def flush(self):
        """Write all buffered rows to file."""
        if self.buffer:
            self.writer.writerows(self.buffer)
            self.file.flush()
            self.buffer.clear()

    def close(self):
        """Flush remaining data and close the file."""
        self.flush()
        self.file.close()
