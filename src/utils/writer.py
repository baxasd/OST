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

        if not file_exists:
            self.writer.writeheader()

    def log(self, joints_dict):
        """
        Expects:
        {
          joint_id: {
              "pixel": (px, py),
              "metric": (x, y, z)
          }
        }
        """
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
        self.file.flush()

    def close(self):
        self.file.close()
