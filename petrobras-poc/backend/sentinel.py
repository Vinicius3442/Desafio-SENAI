import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from typing import Dict, Any
from datetime import datetime

class SentinelAI:
    def __init__(self):
        # IsolationForest is excellent for unsupervised anomaly detection (DLP & User behavior model)
        self.model = IsolationForest(
            n_estimators=100, 
            contamination=0.15, # Increased sensitivity to strict Zero Trust
            random_state=42
        )
        self.train_model()
        
    def _create_mock_dataset(self) -> pd.DataFrame:
        """
        Creates a mock dataset simulating 'normal' operations.
        Normal bounds:
        Internal/BR IPs, operating roughly between 6 AM and 8 PM, very low GPS variance.
        """
        # Generate 1000 normal events
        np.random.seed(42)
        n_samples = 1000
        
        # ZERO TRUST: Quase todo tráfego via de regra DEVE ser interno, tornando chamadas externas severamente evidentes
        is_internal_ip = np.random.choice([1]*99 + [0], size=n_samples)
        
        # Hours of operation (0 to 23). Normally between 6 and 20.
        hour = np.random.normal(loc=13, scale=3, size=n_samples)
        hour = np.clip(hour, 6, 20)
        
        # GPS variance from base facility (0 is perfect accuracy, > 0 is distance variation)
        gps_variance = np.abs(np.random.normal(loc=0, scale=0.5, size=n_samples))
        
        return pd.DataFrame({
            "is_internal_ip": is_internal_ip,
            "hour": hour,
            "gps_variance": gps_variance
        })
        
    def train_model(self):
        print("[SentinelAI] Generating baseline behavior dataset...")
        df_normal = self._create_mock_dataset()
        print("[SentinelAI] Training IsolationForest model...")
        self.model.fit(df_normal)
        print("[SentinelAI] Model successfully trained and baseline established.")
        
    def predict(self, metadata: Dict[str, Any]) -> bool:
        """
        Predicts if a request is anomalous.
        Returns:
            True if anomalous (should block)
            False if normal behavior (should pass)
        """
        ip = metadata.get("ip", "0.0.0.0")
        # Define internal IPs simplistically (like a 10.x block)
        is_internal_ip = 1 if ip.startswith("10.") or ip.startswith("192.168.") or ip.startswith("172.") else 0
        
        try:
            timestamp = metadata.get("timestamp", datetime.now().isoformat())
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            hour = dt.hour
        except Exception:
            hour = 12
            
        gps_variance = float(metadata.get("gps_variance", 0.0))
        
        df_request = pd.DataFrame([{
            "is_internal_ip": is_internal_ip,
            "hour": hour,
            "gps_variance": gps_variance
        }])
        
        prediction = self.model.predict(df_request)
        
        # IsolationForest returns -1 for outlier/anomaly and 1 for inlier.
        is_anomalous = bool(prediction[0] == -1)
        
        if is_anomalous:
            reasons = []
            if is_internal_ip == 0:
                reasons.append(f"External/Unknown IP ({ip})")
            if hour < 6 or hour > 20:
                reasons.append(f"Unusual Hour ({hour})")
            if gps_variance > 1.5:
                reasons.append(f"High GPS Deviation ({gps_variance})")
                
            reason_str = ", ".join(reasons) if reasons else "Subtle anomaly detected across combined features"
            print(f"[ALERT] SentinelAI blocked request. Variables: {reason_str}")
            
        return is_anomalous
