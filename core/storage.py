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
        self.chunk_size = 100  # Flush to disk every ~10 seconds
        self.writer = None
        self.total_frames = 0
        
        # --- Define strict column schema ---
        self.schema_columns = ['timestamp']
        for i in range(33):
            self.schema_columns.extend([f"j{i}_x", f"j{i}_y", f"j{i}_z"])

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
            
        # --- Force Pandas to use the exact column structure ---
        df = pd.DataFrame(self.data_buffer, columns=self.schema_columns)
        table = pa.Table.from_pandas(df)
        
        # If this is the FIRST chunk, we must initialize the Parquet Writer
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
        
        # Empty the memory buffer!
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
    """Exports a processed DataFrame to CSV."""
    try:
        df.to_csv(filepath, index=False)
        return True, f"Successfully saved to {os.path.basename(filepath)}"
    except Exception as e:
        return False, f"Export failed: {str(e)}"
    
def load_session_data(filepath: str):
    """
    Universal loader for OST session data.
    Abstracts file formats (Parquet/CSV) away from the UI.
    
    Returns:
        tuple: (pd.DataFrame, subject_id, activity)
    """
    subj, act = "Unknown", "Unknown"

    if filepath.endswith('.parquet'):
        # 1. Instantly read Metadata from Footer
        schema = pq.read_schema(filepath)
        if schema.metadata:
            if b'subject_id' in schema.metadata:
                subj = schema.metadata[b'subject_id'].decode()
            if b'activity' in schema.metadata:
                act = schema.metadata[b'activity'].decode()
                
        # 2. Load Data
        df = pd.read_parquet(filepath)

    elif filepath.endswith('.csv'):
        # 1. Load Data
        df = pd.read_csv(filepath)
        
        # 2. Fallback Metadata: Extract from filename
        clean_name = os.path.basename(filepath).replace('.csv', '')
        parts = clean_name.split('_')
        if len(parts) >= 2:
            subj, act = parts[0], parts[1]
    else:
        raise ValueError(f"Unsupported file format: {filepath}")

    return df, subj, act

def export_analysis_results(df_timeseries, df_stats, base_filepath):
    """
    Saves the Timeseries and Summary stats to two linked CSV files 
    for Excel plotting and Machine Learning.
    """
    try:
        # Strip the .csv extension if the user typed it, so we can append our suffixes safely
        if base_filepath.endswith('.csv'):
            base_filepath = base_filepath[:-4]
        
        ts_path = f"{base_filepath}_timeseries.csv"
        stats_path = f"{base_filepath}_summary.csv"
        
        # Save Timeseries without an index (cleaner for Excel)
        df_timeseries.to_csv(ts_path, index=False)
        
        # Save Stats WITH the index (because the index contains the labels 'mean', '50%', etc.)
        df_stats.to_csv(stats_path, index=True) 
        
        return True, f"Exported Successfully:\n{os.path.basename(ts_path)}\n{os.path.basename(stats_path)}"
    except Exception as e:
        return False, f"Export failed: {str(e)}"