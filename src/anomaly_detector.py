"""
MachineGuard AI - Anomaly Detection Engine
Combines unsupervised Isolation Forest with statistical Z-Score thresholding
for industrial multivariate anomaly detection.
"""

import os
import math
import numpy as np
import pandas as pd
import joblib

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
ISO_PATH = os.path.join(MODEL_DIR, "iso_forest.joblib")
SCALER_PATH = os.path.join(MODEL_DIR, "scaler.joblib")

class AnomalyDetector:
    def __init__(self):
        self.iso_forest = None
        self.scaler = None
        self._load_models()
        
        # Baseline statistical norms from AI4I 2020 dataset
        self.norms = {
            'air_temp': {'mean': 300.0, 'std': 2.0},
            'process_temp': {'mean': 310.0, 'std': 1.48},
            'rpm': {'mean': 1538.7, 'std': 179.3},
            'torque': {'mean': 39.99, 'std': 9.97},
            'tool_wear': {'mean': 107.95, 'std': 63.65}
        }
        
    def _load_models(self):
        if os.path.exists(ISO_PATH) and os.path.exists(SCALER_PATH):
            self.iso_forest = joblib.load(ISO_PATH)
            self.scaler = joblib.load(SCALER_PATH)
            
    def compute_z_scores(self, air_temp, process_temp, rpm, torque, tool_wear):
        z_scores = {
            'air_temp': abs(air_temp - self.norms['air_temp']['mean']) / self.norms['air_temp']['std'],
            'process_temp': abs(process_temp - self.norms['process_temp']['mean']) / self.norms['process_temp']['std'],
            'rpm': abs(rpm - self.norms['rpm']['mean']) / self.norms['rpm']['std'],
            'torque': abs(torque - self.norms['torque']['mean']) / self.norms['torque']['std'],
            'tool_wear': abs(tool_wear - self.norms['tool_wear']['mean']) / self.norms['tool_wear']['std']
        }
        max_z = max(z_scores.values())
        return z_scores, max_z

    def detect_single(self, air_temp, process_temp, rpm, torque, tool_wear, product_type="M"):
        temp_diff = process_temp - air_temp
        power_w = torque * (rpm * 2 * math.pi / 60)
        overstrain = tool_wear * torque
        type_num = {'L': 0, 'M': 1, 'H': 2}.get(product_type, 1)
        
        feature_vec = np.array([[
            air_temp, process_temp, rpm, torque, tool_wear,
            type_num, temp_diff, power_w, overstrain
        ]])
        
        iso_score = 0.0
        is_iso_anomaly = False
        
        if self.iso_forest and self.scaler:
            scaled_vec = self.scaler.transform(feature_vec)
            # Isolation forest decision function (negative = outlier, positive = inlier)
            raw_score = self.iso_forest.decision_function(scaled_vec)[0]
            # Convert to anomaly score 0.0 (normal) -> 1.0 (severe outlier)
            iso_score = max(0.0, min(1.0, 0.5 - raw_score * 2.5))
            pred = self.iso_forest.predict(scaled_vec)[0]
            is_iso_anomaly = (pred == -1)
            
        z_dict, max_z = self.compute_z_scores(air_temp, process_temp, rpm, torque, tool_wear)
        is_stat_anomaly = max_z > 3.0
        
        is_anomaly = is_iso_anomaly or is_stat_anomaly
        
        contributing_factors = []
        if z_dict['torque'] > 2.5:
            contributing_factors.append(f"Abnormal torque reading ({torque:.1f} Nm, Z={z_dict['torque']:.2f})")
        if z_dict['rpm'] > 2.5:
            contributing_factors.append(f"Extreme rotational speed deviation ({rpm:.0f} RPM, Z={z_dict['rpm']:.2f})")
        if temp_diff < 8.6:
            contributing_factors.append(f"Thermal dissipation compression (\u0394T={temp_diff:.2f} K < 8.6 K)")
        if power_w < 3500 or power_w > 9000:
            contributing_factors.append(f"Power envelope violation ({power_w:.0f} W)")
        if tool_wear > 200:
            contributing_factors.append(f"Tool wear threshold reached ({tool_wear:.0f} min)")
            
        return {
            'is_anomaly': bool(is_anomaly),
            'anomaly_score': round(float(iso_score), 4),
            'max_z_score': round(float(max_z), 2),
            'z_scores': {k: round(v, 2) for k, v in z_dict.items()},
            'contributing_factors': contributing_factors
        }
