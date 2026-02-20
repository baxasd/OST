import os
import datetime
import json
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

class SessionWriter:
    def __init__(self, s, a, metadata=None):
        os.makedirs("records", exist_ok=True)
        self.subject_id = s
        self.activity = a
        self.metadata = metadata or {}
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.filepath = f"records/{s}_{a}_{timestamp}.parquet"
        
        self.data_buffer = []
        self.chunk_size = 300  # Flush to disk every 300 frames (~10 seconds at 30fps)
        self.writer = None
        self.total_frames = 0

    def write_frame(self, frame_data: dict):
        """Appends to buffer. Flushes to disk if buffer reaches chunk_size."""
        self.data_buffer.append(frame_data)
        self.total_frames += 1
        
        if len(self.data_buffer) >= self.chunk_size:
            self._flush_buffer()

    def _flush_buffer(self):
        """Converts the buffer to a Parquet Row Group and clears memory."""
        if not self.data_buffer:
            return
            
        df = pd.DataFrame(self.data_buffer)
        table = pa.Table.from_pandas(df)
        
        # If this is the FIRST chunk, we must initialize the Parquet Writer
        # because we need the data schema to embed our metadata.
        if self.writer is None:
            custom_meta = {
                b"subject_id": str(self.subject_id).encode(),
                b"activity": str(self.activity).encode(),
                b"session_meta": json.dumps(self.metadata).encode()
            }
            existing_meta = table.schema.metadata or {}
            combined_meta = {**existing_meta, **custom_meta}
            
            # Create a new schema with our embedded metadata
            schema_with_meta = table.schema.with_metadata(combined_meta)
            table = table.cast(schema_with_meta) # Apply to table
            
            # Open the file stream
            self.writer = pq.ParquetWriter(self.filepath, schema_with_meta)
            
        # Write the chunk to disk
        self.writer.write_table(table)
        
        # CRITICAL: Empty the memory buffer!
        self.data_buffer.clear()

    def close(self):
        """Flushes any remaining frames and safely closes the file."""
        self._flush_buffer()
        
        if self.writer:
            self.writer.close()
            print(f"✅ Session saved: {self.filepath} ({self.total_frames} frames)")
        else:
            print("No data recorded.")

def export_clean_csv(df: pd.DataFrame, filepath: str):
    """
    Exports a processed DataFrame to CSV.
    Separates IO logic from the UI.
    """
    try:
        df.to_csv(filepath, index=False)
        return True, f"Successfully saved to {os.path.basename(filepath)}"
    except Exception as e:
        return False, f"Export failed: {str(e)}"