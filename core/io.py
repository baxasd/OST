# ost/core/io.py
import csv
import os
from datetime import datetime

class SessionWriter:
    def __init__(self, filename=None, metadata=None):
        if filename is None:
            os.makedirs("records", exist_ok=True)
            filename = f"records/session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        self.filename = filename
        self.file = open(filename, 'a', newline='')
        
        # Write Metadata
        if metadata:
            self.file.write("# SESSION METADATA\n")
            for k, v in metadata.items():
                self.file.write(f"# {k}: {v}\n")
            self.file.write("# ----------------\n")

        # Setup Columns (Standard Mediapipe 33 joints)
        self.keys = ["timestamp"]
        for i in range(33):
            self.keys.extend([f"j{i}_px", f"j{i}_py", f"j{i}_x", f"j{i}_y", f"j{i}_z"])

        self.writer = csv.DictWriter(self.file, fieldnames=self.keys)
        self.writer.writeheader()

    def write_frame(self, frame_data: dict):
        """
        Expects a dict with 'timestamp' and joint data.
        """
        self.writer.writerow(frame_data)
        self.file.flush()

    def close(self):
        if not self.file.closed:
            self.file.flush()
            self.file.close()