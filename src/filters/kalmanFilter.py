import numpy  as np
from filterpy.kalman import KalmanFilter

class KalmanFilter:
    def __init__(self, num_joints=33, dt=1/30):   
        self.filters = {jid: self._create_filter(dt) for jid in range(num_joints)}

    
    def _create_filter(self, dt):

        try:

            kf = KalmanFilter(dim_x=6, dim_z=3)
            kf.F = np.array([[1,0,0,dt,0,0],
                            [0,1,0,0,dt,0],
                            [0,0,1,0,0,dt],
                            [0,0,0,1,0,0],
                            [0,0,0,0,1,0],
                            [0,0,0,0,0,1]])
            kf.H = np.array([[1,0,0,0,0,0],
                            [0,1,0,0,0,0],
                            [0,0,1,0,0,0]])
            
            kf.P *= 0.1
            kf.R *= 0.01
            kf.Q *= 0.01
            kf.x[:3] = 0
            return kf
        except Exception as e:
            print("Error creating Kalman filter:", e)
            return None
    
    def update(self, jid, X, Y, Z):

        try:
                
            if jid not in self.filters:
                self._init_filter(jid)

            kf = self.filters[jid]
            if np.all(kf.x[:3] == 0):
                kf.x[:3] = np.array([[X], [Y], [Z]])

            kf.predict()
            kf.update(np.array([X, Y, Z]))

            X_s, Y_s, Z_s = kf.x[:3].flatten()
            return X_s, Y_s, Z_s
        
        except Exception as e:
            print(f"Error in KalmanSmoother update for joint {jid}:", e)
            return X, Y, Z