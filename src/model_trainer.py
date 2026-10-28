"""
MachineGuard AI - Real Model Training Pipeline
Dataset: AI4I 2020 Predictive Maintenance Dataset (UCI Machine Learning Repository)
Trains a Random Forest Classifier and Isolation Forest for Anomaly Detection.
"""

import os
import json
import math
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report
)
import joblib

def load_data(filepath="data/ai4i2020.csv"):
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Dataset not found at {filepath}")
    df = pd.read_csv(filepath)
    return df

def feature_engineering(df):
    data = df.copy()
    # Compute physical derived features
    data['Temp_difference'] = data['Process temperature [K]'] - data['Air temperature [K]']
    data['Power_W'] = data['Torque [Nm]'] * (data['Rotational speed [rpm]'] * (2 * math.pi / 60))
    data['Overstrain_factor'] = data['Tool wear [min]'] * data['Torque [Nm]']
    
    # Map Type to numeric encoding: L=0, M=1, H=2
    type_map = {'L': 0, 'M': 1, 'H': 2}
    if 'Type' in data.columns:
        data['Type_numeric'] = data['Type'].map(type_map).fillna(0)
    else:
        data['Type_numeric'] = 0
        
    return data

def train_and_evaluate(dataset_path="data/ai4i2020.csv", output_dir="models"):
    os.makedirs(output_dir, exist_ok=True)
    df = load_data(dataset_path)
    df_feat = feature_engineering(df)
    
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
    
    X = df_feat[feature_cols]
    y = df_feat['Machine failure']
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Train Random Forest with balanced class weight to address 3.39% failure imbalance
    rf_clf = RandomForestClassifier(
        n_estimators=100,
        max_depth=12,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1
    )
    rf_clf.fit(X_train_scaled, y_train)
    
    # Predict and evaluate
    y_pred = rf_clf.predict(X_test_scaled)
    y_prob = rf_clf.predict_proba(X_test_scaled)[:, 1]
    
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    roc_auc = roc_auc_score(y_test, y_prob)
    cm = confusion_matrix(y_test, y_pred).tolist()
    
    # Feature importance
    feature_importance = dict(zip(feature_cols, rf_clf.feature_importances_.tolist()))
    
    # Train Isolation Forest for unsupervised anomaly detection
    iso_forest = IsolationForest(
        n_estimators=100,
        contamination=0.035,
        random_state=42
    )
    iso_forest.fit(X_train_scaled)
    
    # Save artifacts
    joblib.dump(rf_clf, os.path.join(output_dir, "machineguard_rf.joblib"))
    joblib.dump(scaler, os.path.join(output_dir, "scaler.joblib"))
    joblib.dump(iso_forest, os.path.join(output_dir, "iso_forest.joblib"))
    
    metrics = {
        "dataset": "AI4I 2020 Predictive Maintenance (UCI)",
        "total_records": len(df),
        "train_records": len(X_train),
        "test_records": len(X_test),
        "test_failures": int(y_test.sum()),
        "test_healthy": int((y_test == 0).sum()),
        "accuracy": round(float(acc), 4),
        "precision": round(float(prec), 4),
        "recall": round(float(rec), 4),
        "f1_score": round(float(f1), 4),
        "roc_auc": round(float(roc_auc), 4),
        "confusion_matrix": cm,
        "feature_importance": {k: round(v, 4) for k, v in feature_importance.items()},
        "feature_cols": feature_cols
    }
    
    with open(os.path.join(output_dir, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)
        
    print(f"Model Training Complete!")
    print(f"Accuracy: {acc:.4f} | Recall: {rec:.4f} | Precision: {prec:.4f} | ROC-AUC: {roc_auc:.4f}")
    return metrics

if __name__ == "__main__":
    train_and_evaluate()
