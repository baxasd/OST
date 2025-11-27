import csv
import os
from datetime import datetime

class Writer:
    def __init__(self, filename=None, num_joints=33, include_z=True):
        if filename is None:
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

        # Only write header once
        if not file_exists:
            self.writer.writeheader()

    def log(self, joints):
        """
        Expected format:
        joints = [(x,y,z), (x,y,z), ...]  # len = num_joints
        """

        row = {"timestamp": datetime.now().isoformat()}

        flat = []
        for j in joints:
            if j is None:
                if self.include_z:
                    flat.extend(["", "", ""])
                else:
                    flat.extend(["", ""])
                continue

            flat.append(j[0])
            flat.append(j[1])
            if self.include_z:
                flat.append(j[2])

        for k, v in zip(self.keys, flat):
            row[k] = v

        self.writer.writerow(row)
        self.file.flush()

    def close(self):
        self.file.close()
