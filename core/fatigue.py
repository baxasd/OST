import numpy as np
import pandas as pd
from scipy.spatial import distance

class FatigueAnalyzer:
    def __init__(self, df_timeseries, fps=15, baseline_mins=5, rolling_window_sec=60):
        self.df = df_timeseries.copy() 
        self.fps = fps
        self.baseline_frames = int(baseline_mins * 60 * fps)
        self.rolling_frames = int(rolling_window_sec * fps)
        self.metric_cols = [c for c in self.df.columns if c not in ['timestamp', 'frame']]
        
        self.baseline_mean = None; self.baseline_std = None
        self.cov_matrix = None; self.inv_cov_matrix = None

    def run_pipeline(self):
        self._calculate_baseline()
        self._calculate_rolling_metrics()
        self._calculate_mahalanobis()
        self._calculate_fii()
        summary_df, onset_min = self._generate_summary()
        adv_metrics = self._calculate_advanced_metrics() 
        
        return self.df, summary_df, onset_min, adv_metrics

    def _calculate_baseline(self):
        baseline_data = self.df.iloc[:self.baseline_frames][self.metric_cols]
        self.baseline_mean = baseline_data.mean()
        self.baseline_std = baseline_data.std()
        self.cov_matrix = np.cov(baseline_data.T)
        self.inv_cov_matrix = np.linalg.pinv(self.cov_matrix)

    def _calculate_rolling_metrics(self):
        rolling_means = self.df[self.metric_cols].rolling(window=self.rolling_frames, min_periods=1).mean()
        for col in self.metric_cols:
            self.df[f'{col}_zscore'] = (rolling_means[col] - self.baseline_mean[col]) / self.baseline_std[col]
        self.smoothed_data = rolling_means

    def _calculate_mahalanobis(self):
        centroid = self.baseline_mean.values
        distances = []
        for index, row in self.smoothed_data.iterrows():
            if pd.isna(row.iloc[0]):
                distances.append(0)
                continue
            distances.append(distance.mahalanobis(row.values, centroid, self.inv_cov_matrix))
        self.df['mahalanobis_dist'] = distances

    def _calculate_fii(self):
        z_cols = [c for c in self.df.columns if c.endswith('_zscore')]
        self.df['mean_abs_z'] = self.df[z_cols].abs().mean(axis=1)
        self.df['norm_mahalanobis'] = self.df['mahalanobis_dist'] / len(self.metric_cols)
        self.df['FII'] = self.df['norm_mahalanobis'] + self.df['mean_abs_z']

    def _generate_summary(self):
        self.df['minute'] = (self.df['timestamp'] // 60).astype(int) + 1
        summary_df = self.df.groupby('minute').agg(FII=('FII', 'mean'), Mahalanobis=('mahalanobis_dist', 'mean')).reset_index()
        onset_df = summary_df[summary_df['FII'] > 2.0]
        fatigue_onset_min = onset_df['minute'].iloc[0] if not onset_df.empty else None
        return summary_df, fatigue_onset_min

    def _calculate_advanced_metrics(self):
        """Calculates per-minute slopes and brutally detailed descriptive stats for all columns."""
        metrics = {}
        t_sec = self.df['timestamp'].values
        
        # 1. Calculate the Rate of Change (Slope per minute) for every single metric
        if len(t_sec) > 1:
            for col in self.metric_cols + ['mahalanobis_dist']:
                metrics[f'slope_{col}'] = np.polyfit(t_sec, self.df[col].fillna(0), 1)[0] * 60
        else:
            for col in self.metric_cols + ['mahalanobis_dist']:
                metrics[f'slope_{col}'] = 0.0

        # 2. Extract standard pandas describe() to merge into our console text
        safe_df = self.df.drop(columns=['timestamp', 'frame', 'minute', 'norm_mahalanobis', 'mean_abs_z', 'FII'], errors='ignore')
        metrics['describe'] = safe_df.describe().T
        return metrics