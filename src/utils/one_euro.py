import numpy as np
import math

class OneEuroFilter:
    def __init__(self, freq=30, min_cutoff=1.0, beta=0.0, d_cutoff=1.0):
        self.freq = freq
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff

        self.prev_x = None
        self.prev_dx = None

    def _alpha(self, cutoff):
        tau = 1.0 / (2 * math.pi * cutoff)
        te = 1.0 / self.freq
        return 1.0 / (1.0 + tau / te)

    def _lowpass(self, x, alpha, prev):
        if prev is None:
            return x
        return alpha * x + (1 - alpha) * prev

    def __call__(self, x):
        x = np.array(x)

        # First derivative
        dx = (x - self.prev_x) * self.freq if self.prev_x is not None else np.zeros_like(x)
        alpha_d = self._alpha(self.d_cutoff)
        dx_hat = self._lowpass(dx, alpha_d, self.prev_dx)

        # Main smoothing
        cutoff = self.min_cutoff + self.beta * np.linalg.norm(dx_hat)
        alpha = self._alpha(cutoff)
        x_hat = self._lowpass(x, alpha, self.prev_x)

        # Update state
        self.prev_x = x_hat
        self.prev_dx = dx_hat

        return x_hat
