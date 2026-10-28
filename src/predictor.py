"""
MachineGuard AI - Machine Failure Risk Predictor Pipeline
Performs inference using trained Random Forest & physical failure mode diagnostics.
"""

import os
import math
import numpy as np
import pandas as pd
import joblib

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
MODEL_PATH = os.path.join(MODEL_DIR, "machineguard_rf.joblib")
SCALER_PATH = os.path.join(MODEL_DIR, "scaler.joblib")

class MachineFailurePredictor:
    def __init__(self):
        self.model = None
        self.scaler = None
        self._load_artifacts()
        
    def _load_artifacts(self):
        if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
            self.model = joblib.load(MODEL_PATH)
            self.scaler = joblib.load(SCALER_PATH)
        else:
            raise FileNotFoundError("Model artifacts not found. Please run model_trainer.py first.")
            
    def diagnose_failure_modes(self, air_temp, process_temp, rpm, torque, tool_wear, product_type="M"):
        """
        Diagnoses specific physical failure modes according to the AI4I 2020 dataset specs.
        """
        temp_diff = process_temp - air_temp
        angular_velocity = rpm * (2 * math.pi / 60)
        power_w = torque * angular_velocity
        overstrain = tool_wear * torque
        
        type_threshold = {'L': 11000, 'M': 12000, 'H': 13000}.get(product_type, 12000)
        
        twf = bool(tool_wear >= 200)
        hdf = bool(temp_diff < 8.6 and rpm < 1380)
        pwf = bool(power_w < 3500 or power_w > 9000)
        osf = bool(overstrain > type_threshold)
        
        diagnostics = []
        recommendations = []
        
        if twf:
            diagnostics.append({
                "code": "TWF",
                "name": "Tool Wear Failure",
                "severity": "Critical" if tool_wear >= 220 else "High",
                "description": f"Tool accumulated {tool_wear:.0f} mins of wear (critical threshold >= 200 min)."
            })
            recommendations.append("Immediate tool insert / end-mill replacement recommended to prevent workpiece damage.")
            
        if hdf:
            diagnostics.append({
                "code": "HDF",
                "name": "Heat Dissipation Failure",
                "severity": "Critical",
                "description": f"Temperature differential \u0394T ({temp_diff:.2f} K) is below 8.6 K under low speed ({rpm:.0f} RPM)."
            })
            recommendations.append("Inspect coolant pump flow rate, clean heat exchanger fins, and check fluid nozzle alignment.")
            
        if pwf:
            status = "excessive" if power_w > 9000 else "insufficient"
            diagnostics.append({
                "code": "PWF",
                "name": "Power Failure",
                "severity": "Critical",
                "description": f"Mechanical power ({power_w:.1f} W) is outside safe operational envelope (3500W - 9000W)."
            })
            recommendations.append("Examine drive motor controller, inverter frequency, and check for spindle shaft binding.")
            
        if osf:
            diagnostics.append({
                "code": "OSF",
                "name": "Overstrain Failure",
                "severity": "Critical",
                "description": f"Overstrain product ({overstrain:.0f} min\u00b7Nm) exceeds safe limit for Type {product_type} ({type_threshold} min\u00b7Nm)."
            })
            recommendations.append("Reduce feed rate and depth of cut immediately. Replace cutter to alleviate torque loading.")
            
        return {
            "modes": diagnostics,
            "recommendations": recommendations,
            "physical_metrics": {
                "temp_diff_K": round(temp_diff, 2),
                "power_W": round(power_w, 1),
                "overstrain_min_Nm": round(overstrain, 1),
                "threshold_min_Nm": type_threshold
            }
        }

    def predict_single(self, air_temp, process_temp, rpm, torque, tool_wear, product_type="M"):
        temp_diff = process_temp - air_temp
        power_w = torque * (rpm * 2 * math.pi / 60)
        overstrain = tool_wear * torque
        type_num = {'L': 0, 'M': 1, 'H': 2}.get(product_type, 1)
        
        feature_vec = np.array([[
            air_temp, process_temp, rpm, torque, tool_wear,
            type_num, temp_diff, power_w, overstrain
        ]])
        
        scaled_vec = self.scaler.transform(feature_vec)
        prob = float(self.model.predict_proba(scaled_vec)[0, 1])
        prediction = int(self.model.predict(scaled_vec)[0])
        
        diagnostics = self.diagnose_failure_modes(air_temp, process_temp, rpm, torque, tool_wear, product_type)
        
        # If physical deterministic failure conditions are met, ensure high risk score
        if len(diagnostics["modes"]) > 0:
            prob = max(prob, 0.78)
            prediction = 1
            
        if prob < 0.35:
            risk_level = "Healthy"
            risk_color = "green"
        elif prob < 0.70:
            risk_level = "Warning"
            risk_color = "amber"
        else:
            risk_level = "Critical"
            risk_color = "red"
            
        return {
            "failure_probability": round(prob, 4),
            "predicted_failure": prediction,
            "risk_level": risk_level,
            "risk_color": risk_color,
            "diagnostics": diagnostics["modes"],
            "recommendations": diagnostics["recommendations"],
            "physical_metrics": diagnostics["physical_metrics"]
        }
        
    def predict_batch(self, df):
        """
        Runs batch predictions on a DataFrame with validation and cleaning.
        """
        required_cols = [
            'Air temperature [K]',
            'Process temperature [K]',
            'Rotational speed [rpm]',
            'Torque [Nm]',
            'Tool wear [min]'
        ]
        
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns in dataset: {missing}")
            
        clean_df = df.copy()
        
        # Data cleaning: drop NaNs in critical columns or fill with median
        for col in required_cols:
            if clean_df[col].isna().sum() > 0:
                clean_df[col] = clean_df[col].fillna(clean_df[col].median())
                
        # Type handling
        if 'Type' not in clean_df.columns:
            clean_df['Type'] = 'M'
        clean_df['Type'] = clean_df['Type'].fillna('M')
        
        # Derived features
        clean_df['Temp_difference'] = clean_df['Process temperature [K]'] - clean_df['Air temperature [K]']
        clean_df['Power_W'] = clean_df['Torque [Nm]'] * (clean_df['Rotational speed [rpm]'] * (2 * math.pi / 60))
        clean_df['Overstrain_factor'] = clean_df['Tool wear [min]'] * clean_df['Torque [Nm]']
        
        type_map = {'L': 0, 'M': 1, 'H': 2}
        clean_df['Type_numeric'] = clean_df['Type'].map(type_map).fillna(1)
        
        feature_cols = [
            'Air temperature [K]',
            'Process temperature [K]',
            'Rotational speed [rpm]',
            'Torque [Nm]',
            'Tool wear [min]',
            'Type_numeric',
            'Temp_difference',
            'Power_W',
            'Overstrain_factor'
        ]
        
        X = clean_df[feature_cols]
        X_scaled = self.scaler.transform(X)
        
        probs = self.model.predict_proba(X_scaled)[:, 1]
        preds = self.model.predict(X_scaled)
        
        clean_df['Failure_Probability'] = [round(float(p), 4) for p in probs]
        clean_df['Predicted_Failure'] = preds
        
        def assign_risk(p):
            if p < 0.35:
                return "Healthy"
            elif p < 0.70:
                return "Warning"
            return "Critical"
            
        clean_df['Risk_Category'] = clean_df['Failure_Probability'].apply(assign_risk)
        return clean_df
