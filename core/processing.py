# ost/core/processing.py
import pandas as pd
import numpy as np
from scipy.signal import savgol_filter

class PipelineProcessor:
    """Handles data cleanup: interpolation, smoothing, and integrity checks."""
    
    @staticmethod
    def validate(df: pd.DataFrame):
        """Returns: (is_valid, report_string, needs_repair)"""
        report = []
        issues = 0
        
        # 1. Check Structure
        if 'timestamp' not in df.columns:
            return False, "CRITICAL: Missing 'timestamp' column", False
            
        joint_cols = [c for c in df.columns if 'joint_' in c]
        if not joint_cols:
            return False, "CRITICAL: No joint data found", False

        # 2. Check Zeros (Tracking Loss)
        zeros = (df[joint_cols] == 0.0).sum().sum()
        if zeros > 0:
            pct = (zeros / df[joint_cols].size) * 100
            report.append(f"• Tracking Loss: {pct:.1f}% zeros detected.")
            issues += 1
            
        # 3. Check NaNs
        nans = df[joint_cols].isna().sum().sum()
        if nans > 0:
            report.append(f"• Missing Data: {nans} NaN values found.")
            issues += 1

        status = "CLEAN" if issues == 0 else "WARNINGS"
        return True, "\n".join(report), (issues > 0)

    @staticmethod
    def repair(df: pd.DataFrame, method='linear', limit=30):
        """Fills gaps (zeros or NaNs)."""
        df_clean = df.copy()
        cols = [c for c in df.columns if "joint_" in c]
        
        # Treat 0.0 as NaN for interpolation
        df_clean[cols] = df_clean[cols].replace(0.0, np.nan)
        
        # Interpolate
        # Note: 'spline' requires numeric index or converting timestamp to float
        if method == 'spline':
            df_clean[cols] = df_clean[cols].interpolate(method='spline', order=3, limit=limit)
        else:
            df_clean[cols] = df_clean[cols].interpolate(method='linear', limit=limit)
            
        return df_clean.fillna(0) # Fill remaining edges with 0

    @staticmethod
    def smooth(df: pd.DataFrame, window=5, poly=2):
        """Applies Savitzky-Golay filter."""
        df_proc = df.copy()
        
        # Find joint indices (0 to 32)
        indices = set([int(c.split('_')[1]) for c in df.columns if 'joint_' in c and '_x' in c])
        
        for i in indices:
            cols = [f"joint_{i}_{ax}" for ax in ['x', 'y', 'z']]
            # Skip if any column missing
            if not all(c in df.columns for c in cols): continue
                
            coords = df_proc[cols].values
            
            # Apply filter per axis
            for axis in range(3):
                try:
                    coords[:, axis] = savgol_filter(coords[:, axis], window, poly)
                except ValueError:
                    pass # Window too large for data
            
            df_proc[cols] = coords
            
        return df_proc