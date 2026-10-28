"""
Unit and Integration Tests for MachineGuard AI
Tests ML models, predictions, failure diagnostics, anomaly detection, database, and digital twin.
"""

import os
import pytest
import numpy as np
import pandas as pd
from src.database import init_db, add_maintenance_log, get_maintenance_logs, log_alert, get_alerts, update_alert_status
from src.predictor import MachineFailurePredictor
from src.anomaly_detector import AnomalyDetector
from src.digital_twin import DigitalTwinSpindle

TEST_DB_PATH = "test_machineguard.db"

@pytest.fixture(scope="module")
def setup_test_db():
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    init_db(TEST_DB_PATH)
    yield TEST_DB_PATH
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

def test_dataset_exists_and_valid():
    """Verify official AI4I 2020 dataset is present and has expected columns."""
    csv_path = "data/ai4i2020.csv"
    assert os.path.exists(csv_path), "AI4I dataset file missing from data/"
    df = pd.read_csv(csv_path)
    assert len(df) == 10000, f"Expected 10,000 records, got {len(df)}"
    
    expected_cols = [
        'Air temperature [K]',
        'Process temperature [K]',
        'Rotational speed [rpm]',
        'Torque [Nm]',
        'Tool wear [min]',
        'Machine failure'
    ]
    for col in expected_cols:
        assert col in df.columns, f"Column {col} missing from dataset"

def test_predictor_nominal_machine():
    """Test model on healthy machine telemetry (typical factory baseline)."""
    predictor = MachineFailurePredictor()
    result = predictor.predict_single(
        air_temp=298.1,
        process_temp=308.6,
        rpm=1551.0,
        torque=42.8,
        tool_wear=15.0,
        product_type="M"
    )
    assert 0.0 <= result["failure_probability"] <= 1.0
    assert result["risk_level"] in ["Healthy", "Warning", "Critical"]
    assert result["risk_level"] == "Healthy", f"Expected Healthy, got {result['risk_level']}"
    assert len(result["diagnostics"]) == 0

def test_predictor_tool_wear_failure_twf():
    """Test deterministic Tool Wear Failure trigger when tool wear exceeds 200 min."""
    predictor = MachineFailurePredictor()
    result = predictor.predict_single(
        air_temp=300.0,
        process_temp=310.0,
        rpm=1500.0,
        torque=45.0,
        tool_wear=225.0,  # Critical tool wear
        product_type="M"
    )
    diagnosed_codes = [d["code"] for d in result["diagnostics"]]
    assert "TWF" in diagnosed_codes, "TWF was not triggered for tool_wear >= 200"
    assert result["risk_level"] == "Critical"
    assert result["failure_probability"] >= 0.70

def test_predictor_heat_dissipation_failure_hdf():
    """Test Heat Dissipation Failure trigger when delta T < 8.6 K and RPM < 1380."""
    predictor = MachineFailurePredictor()
    result = predictor.predict_single(
        air_temp=302.5,
        process_temp=308.0,  # Delta T = 5.5 K (< 8.6 K)
        rpm=1320.0,          # RPM < 1380
        torque=40.0,
        tool_wear=50.0,
        product_type="L"
    )
    diagnosed_codes = [d["code"] for d in result["diagnostics"]]
    assert "HDF" in diagnosed_codes, "HDF was not triggered for low delta-T and low RPM"
    assert result["risk_level"] == "Critical"

def test_predictor_overstrain_failure_osf():
    """Test Overstrain Failure trigger when Tool Wear * Torque exceeds Type threshold."""
    predictor = MachineFailurePredictor()
    # For Type L, threshold is 11,000 min*Nm. 200 min * 65 Nm = 13,000 min*Nm
    result = predictor.predict_single(
        air_temp=298.0,
        process_temp=308.0,
        rpm=1450.0,
        torque=65.0,
        tool_wear=200.0,
        product_type="L"
    )
    diagnosed_codes = [d["code"] for d in result["diagnostics"]]
    assert "OSF" in diagnosed_codes, "OSF was not triggered when overstrain exceeds threshold"

def test_anomaly_detector():
    """Test anomaly detection logic and Z-score calculations."""
    detector = AnomalyDetector()
    
    # 1. Normal readings
    norm_res = detector.detect_single(
        air_temp=300.0,
        process_temp=310.0,
        rpm=1540.0,
        torque=40.0,
        tool_wear=80.0
    )
    assert norm_res["max_z_score"] < 2.0
    
    # 2. Extreme anomalous readings (Torque = 80 Nm, RPM = 2700)
    anom_res = detector.detect_single(
        air_temp=304.0,
        process_temp=311.0,
        rpm=2700.0,
        torque=80.0,
        tool_wear=230.0
    )
    assert anom_res["is_anomaly"] is True
    assert len(anom_res["contributing_factors"]) > 0

def test_database_crud(setup_test_db):
    """Test SQLite database initialization, insert, and fetch."""
    db_path = setup_test_db
    
    # Insert maintenance log
    log_id = add_maintenance_log(
        machine_id="TEST-001",
        technician="Test Engineer",
        maintenance_type="Bearing Lube",
        priority="Medium",
        parts="Synthetic Grease",
        notes="Routine scheduled lubrication",
        db_path=db_path
    )
    assert log_id > 0
    
    logs = get_maintenance_logs(db_path=db_path)
    assert any(l["machine_id"] == "TEST-001" for l in logs)
    
    # Alert logging
    alert_id = log_alert(
        machine_id="TEST-001",
        alert_type="HDF Warning",
        risk_score=0.88,
        severity="Critical",
        sensors={"air_temp": 302.0, "process_temp": 307.0},
        db_path=db_path
    )
    assert alert_id > 0
    
    alerts = get_alerts(db_path=db_path)
    assert any(a["id"] == alert_id for a in alerts)
    
    # Acknowledge alert
    update_alert_status(alert_id, "Acknowledged", db_path=db_path)
    updated_alerts = get_alerts(db_path=db_path)
    target = next(a for a in updated_alerts if a["id"] == alert_id)
    assert target["status"] == "Acknowledged"

def test_digital_twin_simulation():
    """Test digital twin physics tick and scenario handling."""
    twin = DigitalTwinSpindle("DT-TEST-99", "M")
    telem_initial = twin.get_telemetry()
    assert telem_initial["rotational_speed_rpm"] > 1400.0
    
    # Step nominal
    telem_step = twin.update_tick(delta_time_sec=1.0)
    assert telem_step["step_count"] == 1
    assert telem_step["tool_wear_min"] >= telem_initial["tool_wear_min"]
    
    # Set over_torque scenario
    twin.set_scenario("over_torque")
    for _ in range(5):
        twin.update_tick(delta_time_sec=1.0)
    telem_stressed = twin.get_telemetry()
    assert telem_stressed["torque_Nm"] > telem_initial["torque_Nm"]
