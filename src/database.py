"""
MachineGuard AI - SQLite Database Operations
Manages persistence for telemetry readings, maintenance logs, and alert history.
"""

import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "machineguard.db")

def get_connection(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path=DB_PATH):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    # 1. Maintenance logs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS maintenance_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        machine_id TEXT NOT NULL,
        technician_name TEXT NOT NULL,
        maintenance_type TEXT NOT NULL,
        priority TEXT NOT NULL,
        parts_replaced TEXT,
        notes TEXT,
        status TEXT DEFAULT 'Completed',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # 2. Alert history
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alert_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        machine_id TEXT NOT NULL,
        alert_type TEXT NOT NULL,
        risk_score REAL NOT NULL,
        severity TEXT NOT NULL,
        sensors_snapshot TEXT,
        status TEXT DEFAULT 'Active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # 3. Telemetry history
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS telemetry_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        machine_id TEXT NOT NULL,
        air_temp REAL,
        process_temp REAL,
        rpm REAL,
        torque REAL,
        tool_wear REAL,
        failure_prob REAL,
        is_anomaly INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    conn.commit()
    
    # Seed default maintenance logs if empty
    cursor.execute("SELECT COUNT(*) FROM maintenance_logs")
    if cursor.fetchone()[0] == 0:
        sample_logs = [
            ("M14860", "Alex Henderson", "Spindle Bearing Replacement", "Critical", "Ceramic Spindle Bearings, Lubricant Seal", "Spindle vibration reached 4.2 mm/s due to bearing race pitting. Replaced and laser-aligned.", "Completed", "2026-10-15 09:30:00"),
            ("L47181", "Sarah Chen", "Coolant Flow Line Cleaning", "High", "Pressure Transducer, High-Flow Filter", "HDF warning triggered; temperature differential dropped to 7.8 K. Cleared clogged nozzle line.", "Completed", "2026-10-18 14:15:00"),
            ("H31801", "Marcus Vance", "End Mill Tool Inspection & Swap", "Medium", "Carbide 12mm 4-Flute End Mill", "Tool wear reached 214 min. Replaced tool tip before overstrain failure.", "Completed", "2026-10-22 11:00:00"),
            ("M24200", "Elena Rostova", "Drive Belt Tension Calibration", "Low", "Poly-V Drive Belt", "Torque variance noted during high-speed cycle. Re-tensioned to factory spec (42 Nm).", "Completed", "2026-10-25 16:45:00")
        ]
        cursor.executemany("""
        INSERT INTO maintenance_logs (machine_id, technician_name, maintenance_type, priority, parts_replaced, notes, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, sample_logs)
        conn.commit()
        
    conn.close()

def add_maintenance_log(machine_id, technician, maintenance_type, priority, parts, notes, status="Completed", db_path=DB_PATH):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO maintenance_logs (machine_id, technician_name, maintenance_type, priority, parts_replaced, notes, status)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (machine_id, technician, maintenance_type, priority, parts, notes, status))
    conn.commit()
    log_id = cursor.lastrowid
    conn.close()
    return log_id

def get_maintenance_logs(limit=50, db_path=DB_PATH):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM maintenance_logs ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def log_alert(machine_id, alert_type, risk_score, severity, sensors, status="Active", db_path=DB_PATH):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO alert_history (machine_id, alert_type, risk_score, severity, sensors_snapshot, status)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (machine_id, alert_type, risk_score, severity, json.dumps(sensors), status))
    conn.commit()
    alert_id = cursor.lastrowid
    conn.close()
    return alert_id

def get_alerts(status=None, limit=50, db_path=DB_PATH):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    if status:
        cursor.execute("SELECT * FROM alert_history WHERE status = ? ORDER BY created_at DESC LIMIT ?", (status, limit))
    else:
        cursor.execute("SELECT * FROM alert_history ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def update_alert_status(alert_id, new_status="Acknowledged", db_path=DB_PATH):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE alert_history SET status = ? WHERE id = ?", (new_status, alert_id))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")
