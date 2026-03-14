import numpy as np
import pandas as pd
from scipy.stats import linregress

class FatigueAnalyzer:
    """
    Basic Kinematic Engine.
    Converts noisy frame-by-frame telemetry into smooth, second-by-second averages,
    and calculates the overall drift (slope) of the runner's posture.
    """
    def __init__(self, df_timeseries: pd.DataFrame, fps: float, baseline_mins: int = 1):
        self.df = df_timeseries.copy()
        self.fps = fps if fps > 0 else 30.0

    def run_pipeline(self):
        # 1. Convert timestamps into flat integer seconds (e.g., 1.23s and 1.98s both become 1)
        self.df['time_sec'] = np.floor(self.df['timestamp']).astype(int)
        
        # 2. Group by second and calculate the mean for all angles
        # This shrinks the dataset (e.g., 30 frames become 1 clean row per second)
        numeric_cols = [c for c in self.df.columns if c not in ['frame', 'time_sec']]
        df_per_second = self.df.groupby('time_sec')[numeric_cols].mean().reset_index()
        
        # 3. Calculate basic drift (linear regression) to see how angles change over time
        # We calculate the slope per MINUTE to make the output readable for humans
        adv_metrics = {}
        if len(df_per_second) > 1:
            x_minutes = df_per_second['time_sec'] / 60.0
            
            # Check the drift for our most important metrics
            for col in ['lean_x', 'lean_z', 'l_knee', 'r_knee']:
                if col in df_per_second.columns:
                    slope, intercept, r_value, p_value, std_err = linregress(x_minutes, df_per_second[col])
                    adv_metrics[f"slope_{col}"] = slope

        # 4. Calculate standard summary stats (Min, Max, Mean, Std Dev)
        summary_df = df_per_second.drop(columns=['time_sec', 'timestamp'], errors='ignore').describe()

        return df_per_second, summary_df, adv_metrics