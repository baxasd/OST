# ost/core/io.py
import csv
import os
import time

class SessionWriter:
    def __init__(self, s, a, metadata=None):


        os.makedirs("records", exist_ok=True)
        filename = f"records/{s}_{a}_{int(time.time())}.csv"
        
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
            self.keys.extend([f"j{i}_x", f"j{i}_y", f"j{i}_z"])

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