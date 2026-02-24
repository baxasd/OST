import numpy as np
import pandas as pd
from scipy.spatial import distance

class FatigueAnalyzer:
    def __init__(self, df_timeseries, fps=15, baseline_mins=5, rolling_window_sec=60):
        """
        Initializes the Fatigue Pipeline.
        Args:
            df_timeseries: The pandas DataFrame containing all frame-by-frame joint angles.
            fps: Frames per second of the capture.
            baseline_mins: How many minutes to use for the baseline model.
            rolling_window_sec: How many seconds for the rolling smoothing window.
        """
        # Ensure we don't modify the original dataframe
        self.df = df_timeseries.copy() 
        self.fps = fps
        self.baseline_frames = int(baseline_mins * 60 * fps)
        self.rolling_frames = int(rolling_window_sec * fps)
        
        # We only want to analyze the actual metric columns (ignore timestamp/frame)
        self.metric_cols = [c for c in self.df.columns if c not in ['timestamp', 'frame']]
        
        self.baseline_mean = None
        self.baseline_std = None
        self.cov_matrix = None
        self.inv_cov_matrix = None

    def run_pipeline(self):
        """Executes the full fatigue detection algorithm."""
        self._calculate_baseline()
        self._calculate_rolling_metrics()
        self._calculate_mahalanobis()
        self._calculate_fii()
        return self._generate_summary()

    def _calculate_baseline(self):
        """Establish the multivariate baseline using the first N minutes."""
        # Isolate the baseline data
        baseline_data = self.df.iloc[:self.baseline_frames][self.metric_cols]
        
        # Univariate baselines
        self.baseline_mean = baseline_data.mean()
        self.baseline_std = baseline_data.std()
        
        # Multivariate baseline (Covariance Matrix)
        # We transpose because np.cov expects variables as rows and observations as columns
        self.cov_matrix = np.cov(baseline_data.T)
        
        # Pseudo-inverse is safer for highly collinear biomechanical data (e.g., knee and hip moving together)
        self.inv_cov_matrix = np.linalg.pinv(self.cov_matrix)

    def _calculate_rolling_metrics(self):
        """Apply rolling window to smooth data and calculate Z-Scores."""
        # 1. Smooth the raw data
        rolling_means = self.df[self.metric_cols].rolling(window=self.rolling_frames, min_periods=1).mean()
        
        # 2. Calculate Z-Scores based on the BASELINE distribution: (Current - Base Mean) / Base STD
        for col in self.metric_cols:
            self.df[f'{col}_zscore'] = (rolling_means[col] - self.baseline_mean[col]) / self.baseline_std[col]
            
        # Store smoothed means for Mahalanobis calculation
        self.smoothed_data = rolling_means

    def _calculate_mahalanobis(self):
        """Calculate Mahalanobis distance from the baseline centroid for every smoothed frame."""
        centroid = self.baseline_mean.values
        
        distances = []
        for index, row in self.smoothed_data.iterrows():
            # If the rolling window hasn't filled yet (start of recording), distance is 0
            if pd.isna(row.iloc[0]):
                distances.append(0)
                continue
            
            current_vector = row.values
            # scipy mahalanobis takes (u, v, inverse_covariance)
            md = distance.mahalanobis(current_vector, centroid, self.inv_cov_matrix)
            distances.append(md)
            
        self.df['mahalanobis_dist'] = distances

    def _calculate_fii(self):
        """
        Calculates the Composite Fatigue Instability Index (FII).
        We combine the normalized Mahalanobis distance with extreme Z-score tracking.
        """
        # Get all z-score columns
        z_cols = [c for c in self.df.columns if c.endswith('_zscore')]
        
        # Calculate the Mean Absolute Z-Score across all joints for each frame
        self.df['mean_abs_z'] = self.df[z_cols].abs().mean(axis=1)
        
        # Normalize Mahalanobis distance by the number of metrics (degrees of freedom)
        self.df['norm_mahalanobis'] = self.df['mahalanobis_dist'] / len(self.metric_cols)
        
        # The FII is a composite of how far the whole body drifted (Mahalanobis) 
        # plus the average univariate extreme deviations.
        self.df['FII'] = self.df['norm_mahalanobis'] + self.df['mean_abs_z']

    def _generate_summary(self):
        """Downsamples the frame-by-frame data into a minute-by-minute report."""
        # Create a 'minute' grouping column
        self.df['minute'] = (self.df['timestamp'] // 60).astype(int) + 1
        
        # Group by minute and take the mean of the metrics for that minute
        summary_df = self.df.groupby('minute').agg(
            FII=('FII', 'mean'),
            Mahalanobis=('mahalanobis_dist', 'mean'),
            Lean_X_Zscore=('lean_x_zscore', 'mean'),
            R_Knee_Zscore=('r_knee_zscore', 'mean'),
            L_Knee_Zscore=('l_knee_zscore', 'mean')
        ).reset_index()
        
        # Detect Fatigue Onset (First minute where FII > Threshold)
        # We can define a threshold of 2.0 (meaning a severe deviation across multiple metrics)
        onset_df = summary_df[summary_df['FII'] > 2.0]
        fatigue_onset_min = onset_df['minute'].iloc[0] if not onset_df.empty else None
        
        return self.df, summary_df, fatigue_onset_min