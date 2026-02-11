# ost/core/processing.py
import pandas as pd
import numpy as np
from scipy.signal import savgol_filter
from core.data import identify_joint_columns

class PipelineProcessor:
    """ Logic for validating and cleaning motion data"""
    @staticmethod
    def validate(df: pd.DataFrame):
        """Returns: (report_string, needs_repair_bool)"""
        report = []
        issues = 0
        
        # Check Structure using centralized logic
        x_cols = identify_joint_columns(df.columns)
        if not x_cols:
            return "CRITICAL: No joint data found (checked 'j0_x' and 'joint_0_x').", False
            
        # Check Tracking
        all_joint_cols = []
        for c in x_cols:
            base = c[:-2] # remove '_x'
            all_joint_cols.extend([f"{base}_x", f"{base}_y", f"{base}_z"])
        
        # Filter to only existing columns
        existing_cols = [c for c in all_joint_cols if c in df.columns]
        
        zeros = (df[existing_cols] == 0.0).sum().sum()
        if zeros > 0:
            pct = (zeros / df[existing_cols].size) * 100
            report.append(f"• Tracking Loss: {pct:.1f}% zeros detected.")
            issues += 1
            
        # Check Gaps
        nans = df[existing_cols].isna().sum().sum()
        if nans > 0:
            report.append(f"• Data Gaps: {nans} missing values.")
            issues += 1

        # Check Frame Drops
        if 'frame' in df.columns:
            diffs = df['frame'].diff().fillna(1)
            drops = (diffs > 1).sum()
            if drops > 0:
                report.append(f"• Frame Drops: {int(drops)} discontinuities detected.")
                issues += 1

        if issues == 0:
            return "✔ DATA INTEGRITY: PASS\nNo obvious tracking issues found.", False
        else:
            header = f"⚠ ISSUES FOUND ({issues}):"
            return header + "\n" + "\n".join(report), True

    @staticmethod
    def repair(df: pd.DataFrame, method='linear', limit=30):
        """Fills gaps where sensor lost tracking."""
        df_clean = df.copy()
        
        x_cols = identify_joint_columns(df.columns)
        target_cols = []
        for c in x_cols:
            base = c[:-2]
            target_cols.extend([f"{base}_x", f"{base}_y", f"{base}_z"])
            
        valid_cols = [c for c in target_cols if c in df.columns]
        
        # Treat 0.0 as NaN
        df_clean[valid_cols] = df_clean[valid_cols].replace(0.0, np.nan)
        
        # Interpolate
        try:
            if method == 'spline':
                df_clean[valid_cols] = df_clean[valid_cols].interpolate(method='spline', order=3, limit=limit, limit_direction='both')
            else:
                df_clean[valid_cols] = df_clean[valid_cols].interpolate(method='linear', limit=limit, limit_direction='both')
        except:
            df_clean[valid_cols] = df_clean[valid_cols].interpolate(method='linear', limit=limit)
            
        return df_clean.fillna(0.0)

    @staticmethod
    def smooth(df: pd.DataFrame, window=5, poly=2):
        """Applies Savitzky-Golay filter."""
        df_proc = df.copy()
        x_cols = identify_joint_columns(df.columns)
        
        for c in x_cols:
            base = c[:-2]
            cols = [f"{base}_{ax}" for ax in ['x', 'y', 'z']]
            if not all(k in df_proc.columns for k in cols): continue
            
            coords = df_proc[cols].values
            for axis in range(3):
                try:
                    coords[:, axis] = savgol_filter(coords[:, axis], window, poly)
                except ValueError: pass
            
            df_proc[cols] = coords
            
        return df_proc