import numpy as np
import pandas as pd
from scipy.spatial import distance
from scipy.stats import linregress

class FatigueAnalyzer:
    def __init__(self, df, fps=15):
        self.df = df.copy()
        self.fps = fps
        self.metric_cols = [c for c in self.df.columns if c not in ['timestamp', 'frame']]
        
        # 5-second window for smoothing so we keep the "swings" but remove jitter
        self.smooth_win = int(5 * fps)

    def analyze(self):
        """Main execution loop for the new analysis requirements."""
        # 1. Smooth all data
        rolling = self.df[self.metric_cols].rolling(window=self.smooth_win, min_periods=1).mean()
        
        # Save smoothed back to df for plotting
        for col in self.metric_cols:
            self.df[f'{col}_smooth'] = rolling[col]

        # 2. Calculate Mahalanobis (Overall Drift)
        self._add_mahalanobis(rolling)
        
        # 3. Calculate Trends (Linear Regression for Trunk)
        trends = self._calculate_trends(rolling)
        
        # 4. Calculate Symmetry (Dominance)
        # We compare the rolling averages of Left vs Right
        self.df['shoulder_sym'] = rolling['l_sho'] - rolling['r_sho']
        self.df['hip_sym'] = rolling['l_hip'] - rolling['r_hip']
        
        # Determine Dominance
        # If left is generally higher/more extended, Left is dominant
        dom_sho = "Left" if self.df['shoulder_sym'].mean() > 0 else "Right"
        dom_hip = "Left" if self.df['hip_sym'].mean() > 0 else "Right"
        dominance = {'shoulder': dom_sho, 'hip': dom_hip}
        
        return self.df, trends, dominance

    def _add_mahalanobis(self, rolling_df):
        """Computes drift from the first 5 minutes."""
        baseline_frames = int(5 * 60 * self.fps)
        
        # Fallback if the trial is shorter than 5 minutes
        if len(rolling_df) < baseline_frames:
            baseline_frames = len(rolling_df) // 2 
            
        baseline = rolling_df.iloc[:baseline_frames]
        
        mu = baseline.mean().values
        # Pseudo-inverse covariance
        inv_cov = np.linalg.pinv(np.cov(baseline.T))
        
        distances = []
        for _, row in rolling_df.iterrows():
            if row.isnull().any():
                distances.append(0)
            else:
                distances.append(distance.mahalanobis(row.values, mu, inv_cov))
                
        self.df['mahalanobis'] = distances

    def _calculate_trends(self, rolling_df):
        """Calculates Linear Regression lines for Trunk Leans."""
        trends = {}
        x = np.arange(len(rolling_df))
        
        for col in ['lean_x', 'lean_z']:
            y = rolling_df[col].fillna(0).values
            slope, intercept, _, _, _ = linregress(x, y)
            trends[col] = (slope * x) + intercept
            trends[f'{col}_slope'] = slope
            
        return trends