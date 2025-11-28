import csv
import os
from datetime import datetime

class Writer:
    def __init__(self, filename=None, num_joints=33, include_z=True):
        if filename is None:
            os.makedirs("records", exist_ok=True)
            filename = f"records/joints_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        self.filename = filename
        self.num_joints = num_joints
        self.include_z = include_z

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
        """
        Expects a dict: {0: (x,y,z), 1: (x,y,z), ...}
        Missing joints will be filled with empty values.
        """
        row = {"timestamp": datetime.now().isoformat()}
        for i in range(self.num_joints):
            j = joints_dict.get(i)
            if j is None:
                row[f"joint_{i}_x"] = ""
                row[f"joint_{i}_y"] = ""
                if self.include_z:
                    row[f"joint_{i}_z"] = ""
            else:
                row[f"joint_{i}_x"] = j[0]
                row[f"joint_{i}_y"] = j[1]
                if self.include_z:
                    row[f"joint_{i}_z"] = j[2] if len(j) > 2 else ""
        
        self.writer.writerow(row)
        self.file.flush()

    def close(self):
        self.file.close()
