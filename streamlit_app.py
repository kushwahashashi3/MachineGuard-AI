"""
MachineGuard AI - Industrial Predictive Maintenance System
Final-Year B.Tech CSE Capstone Project Application
Frameworks: Streamlit, Plotly, Pandas, NumPy, Scikit-learn, SQLite, Joblib
"""

import os
import json
import math
import time
import sqlite3
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# Import local modules
from src.predictor import MachineFailurePredictor
from src.anomaly_detector import AnomalyDetector
from src.digital_twin import DigitalTwinSpindle
from src.database import (
    init_db, add_maintenance_log, get_maintenance_logs,
    log_alert, get_alerts, update_alert_status, DB_PATH
)

# Page Configuration
st.set_page_config(
    page_title="MachineGuard AI | Predictive Maintenance",
    page_icon="\u2699\ufe0f",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Database and Models
init_db()

@st.cache_resource
def load_predictor():
    return MachineFailurePredictor()

@st.cache_resource
def load_anomaly_detector():
    return AnomalyDetector()

@st.cache_data
def load_dataset():
    if os.path.exists("data/ai4i2020.csv"):
        return pd.read_csv("data/ai4i2020.csv")
    return None

@st.cache_data
def load_metrics():
    if os.path.exists("models/metrics.json"):
        with open("models/metrics.json", "r") as f:
            return json.load(f)
    return None

predictor = load_predictor()
anomaly_detector = load_anomaly_detector()
dataset = load_dataset()
metrics = load_metrics()

# Custom CSS for Industrial Aesthetics
st.markdown("""
<style>
    .metric-card {
        background-color: #1E293B;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .metric-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 28px;
        font-weight: 700;
    }
    .status-healthy { color: #22C55E; }
    .status-warning { color: #F59E0B; }
    .status-critical { color: #EF4444; }
    .stButton>button {
        border-radius: 6px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar Navigation
st.sidebar.title("\u2699\ufe0f MachineGuard AI")
st.sidebar.caption("Industrial Predictive Maintenance \u00b7 B.Tech CSE Project")

nav_choice = st.sidebar.radio(
    "Navigation",
    [
        "1. Executive Fleet Dashboard",
        "2. Failure Risk Predictor",
        "3. Digital Twin Simulator",
        "4. Batch CSV Upload & Inference",
        "5. Anomaly Detection & Alerts",
        "6. Maintenance Logs & Work Orders",
        "7. Model Verification & Metrics"
    ]
)

st.sidebar.markdown("---")
st.sidebar.markdown("**System Health**")
st.sidebar.markdown("- **Engine**: Random Forest (100 Trees)")
st.sidebar.markdown("- **Anomaly**: Isolation Forest + Z-Score")
st.sidebar.markdown("- **Database**: SQLite3 (`machineguard.db`)")
st.sidebar.markdown("- **Dataset**: UCI AI4I 2020 (10,000 records)")

# -------------------------------------------------------------
# PAGE 1: EXECUTIVE FLEET DASHBOARD
# -------------------------------------------------------------
if nav_choice == "1. Executive Fleet Dashboard":
    st.title("Executive Fleet Health Dashboard")
    st.write("Real-time monitoring across 10,000 milling machine records from the AI4I 2020 dataset.")
    
    if dataset is not None:
        total_records = len(dataset)
        total_failures = int(dataset['Machine failure'].sum())
        healthy_count = total_records - total_failures
        
        # Calculate Warning estimate (near critical bounds)
        twf_count = int(dataset['TWF'].sum())
        hdf_count = int(dataset['HDF'].sum())
        pwf_count = int(dataset['PWF'].sum())
        osf_count = int(dataset['OSF'].sum())
        rnf_count = int(dataset['RNF'].sum())
        warning_count = int(((dataset['Tool wear [min]'] > 180) & (dataset['Machine failure'] == 0)).sum())
        critical_count = total_failures

        # KPI Metrics Row
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Machine Fleet", f"{total_records:,}")
        with col2:
            st.metric("Healthy Machines", f"{healthy_count:,}", f"{(healthy_count/total_records)*100:.1f}%")
        with col3:
            st.metric("Warning Alerts", f"{warning_count:,}", "- Near wear limit")
        with col4:
            st.metric("Critical Alerts", f"{critical_count:,}", f"{(critical_count/total_records)*100:.2f}% failure rate", delta_color="inverse")
            
        st.markdown("---")
        
        # Charts Row
        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            st.subheader("Failure Modes Distribution")
            failure_df = pd.DataFrame({
                "Failure Mode": ["Tool Wear (TWF)", "Heat Dissipation (HDF)", "Power Failure (PWF)", "Overstrain (OSF)", "Random Failure (RNF)"],
                "Count": [twf_count, hdf_count, pwf_count, osf_count, rnf_count]
            })
            fig_fail = px.bar(
                failure_df, x="Failure Mode", y="Count",
                color="Count",
                color_continuous_scale="Reds",
                title="AI4I 2020 Root-Cause Failure Occurrences"
            )
            fig_fail.update_layout(template="plotly_dark", height=350)
            st.plotly_chart(fig_fail, use_container_width=True)
            
        with chart_col2:
            st.subheader("Machine Quality Type vs Failure Rate")
            type_group = dataset.groupby('Type')['Machine failure'].agg(['count', 'sum']).reset_index()
            type_group['failure_rate'] = (type_group['sum'] / type_group['count']) * 100
            type_group['Type_Name'] = type_group['Type'].map({'L': 'Low (50%)', 'M': 'Medium (30%)', 'H': 'High (20%)'})
            
            fig_type = px.bar(
                type_group, x="Type_Name", y="failure_rate",
                color="failure_rate",
                color_continuous_scale="Viridis",
                labels={"failure_rate": "Failure Rate (%)", "Type_Name": "Product Quality Tier"},
                title="Failure Rate by Product Quality Tier (L, M, H)"
            )
            fig_type.update_layout(template="plotly_dark", height=350)
            st.plotly_chart(fig_type, use_container_width=True)
            
        # Scatter correlation
        st.subheader("Sensor Operational Boundary: Torque vs Rotational Speed")
        sample_viz = dataset.sample(1500, random_state=42)
        fig_scatter = px.scatter(
            sample_viz, x="Rotational speed [rpm]", y="Torque [Nm]",
            color=sample_viz["Machine failure"].map({0: "Healthy (0)", 1: "Failure (1)"}),
            color_discrete_map={"Healthy (0)": "#22C55E", "Failure (1)": "#EF4444"},
            size="Tool wear [min]",
            hover_data=["Air temperature [K]", "Process temperature [K]"],
            title="Spindle Power Envelope (Sample 1,500 machines)"
        )
        fig_scatter.update_layout(template="plotly_dark", height=420)
        st.plotly_chart(fig_scatter, use_container_width=True)
        
        # Recent Alerts from SQLite
        st.subheader("Recent System Alerts (SQLite Database)")
        alerts = get_alerts(limit=5)
        if alerts:
            st.dataframe(pd.DataFrame(alerts)[['id', 'machine_id', 'alert_type', 'risk_score', 'severity', 'status', 'created_at']], use_container_width=True)
        else:
            st.info("No active alerts logged.")
    else:
        st.error("Dataset not found at data/ai4i2020.csv.")

# -------------------------------------------------------------
# PAGE 2: FAILURE RISK PREDICTOR
# -------------------------------------------------------------
elif nav_choice == "2. Failure Risk Predictor":
    st.title("Machine Failure Risk Predictor")
    st.write("Input machine operational sensor parameters to compute real-time failure probability using the trained Scikit-learn Random Forest model.")
    
    col_input, col_result = st.columns([1, 1])
    
    with col_input:
        st.subheader("Sensor Input Parameters")
        p_type = st.selectbox("Product Quality Tier", ["M", "L", "H"], index=0, help="L = Low (50%), M = Medium (30%), H = High (20%)")
        air_t = st.slider("Air Temperature [K]", min_value=290.0, max_value=310.0, value=298.5, step=0.1, help="Factory ambient temperature (~295K - 305K)")
        proc_t = st.slider("Process Temperature [K]", min_value=300.0, max_value=320.0, value=308.8, step=0.1, help="Machining interface temperature (~305K - 315K)")
        rpm_val = st.slider("Rotational Speed [rpm]", min_value=1100, max_value=2900, value=1530, step=10, help="Spindle rotational speed")
        torque_val = st.slider("Torque [Nm]", min_value=3.0, max_value=85.0, value=40.5, step=0.5, help="Drive motor torque")
        wear_val = st.slider("Tool Wear [min]", min_value=0, max_value=255, value=75, step=1, help="Cumulative tool wear time in minutes")
        
        st.caption(f"Calculated Temperature Difference \u0394T: {proc_t - air_t:.2f} K")
        st.caption(f"Calculated Power: {torque_val * (rpm_val * 2 * math.pi / 60):.1f} W (Safe envelope: 3500W - 9000W)")
        st.caption(f"Overstrain Product: {wear_val * torque_val:.1f} min\u00b7Nm (Limit: 12,000 for Type M)")
        
        submit_btn = st.button("Predict Machine Failure Risk", type="primary", use_container_width=True)

    with col_result:
        st.subheader("Prediction & Diagnostic Report")
        res = predictor.predict_single(
            air_temp=air_t,
            process_temp=proc_t,
            rpm=float(rpm_val),
            torque=float(torque_val),
            tool_wear=float(wear_val),
            product_type=p_type
        )
        
        prob_pct = res["failure_probability"] * 100
        
        # Gauge Meter
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=prob_pct,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': f"Risk Score: {res['risk_level']}", 'font': {'size': 20}},
            number={'suffix': "%", 'font': {'size': 36}},
            gauge={
                'axis': {'range': [0, 100], 'tickwidth': 1},
                'bar': {'color': "#EF4444" if prob_pct > 70 else ("#F59E0B" if prob_pct > 35 else "#22C55E")},
                'steps': [
                    {'range': [0, 35], 'color': "rgba(34, 197, 94, 0.2)"},
                    {'range': [35, 70], 'color': "rgba(245, 158, 11, 0.2)"},
                    {'range': [70, 100], 'color': "rgba(239, 68, 68, 0.2)"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 3},
                    'thickness': 0.75,
                    'value': 70
                }
            }
        ))
        fig_gauge.update_layout(template="plotly_dark", height=280, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_gauge, use_container_width=True)
        
        if res["diagnostics"]:
            st.error(f"Detected {len(res['diagnostics'])} Failure Mode(s):")
            for mode in res["diagnostics"]:
                st.markdown(f"- **{mode['name']} ({mode['code']})** [{mode['severity']}]: {mode['description']}")
                
            st.warning("Actionable Recommendations:")
            for rec in res["recommendations"]:
                st.markdown(f"- {rec}")
        else:
            st.success("Machine telemetry within nominal operating safety limits. No active failure conditions detected.")

# -------------------------------------------------------------
# PAGE 3: DIGITAL TWIN SIMULATOR
# -------------------------------------------------------------
elif nav_choice == "3. Digital Twin Simulator":
    st.title("Industrial Digital Twin Simulation")
    st.write("Real-time telemetry and physical simulation of a CNC Milling Spindle with stress tests.")
    
    if "twin" not in st.session_state:
        st.session_state.twin = DigitalTwinSpindle("CNC-SPINDLE-402", "M")
        st.session_state.history = []
        
    twin = st.session_state.twin
    
    col_controls, col_twin_viz = st.columns([1, 2])
    
    with col_controls:
        st.subheader("Simulation Controls")
        scenario = st.selectbox(
            "Stress Test Scenario",
            ["nominal", "thermal_stress", "over_torque", "tool_degraded", "emergency_stop"],
            format_func=lambda x: {
                "nominal": "Nominal Operation",
                "thermal_stress": "Coolant Failure / Thermal Shock",
                "over_torque": "High Cutter Torque Load",
                "tool_degraded": "Tool Expiration Stress",
                "emergency_stop": "Emergency Stop"
            }[x]
        )
        if st.button("Apply Scenario"):
            twin.set_scenario(scenario)
            st.success(f"Scenario updated to {scenario}")
            
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("Step 1 Tick (+1s)"):
                telem = twin.update_tick(1.0)
                st.session_state.history.append(telem)
                if len(st.session_state.history) > 30:
                    st.session_state.history.pop(0)
        with col_btn2:
            if st.button("Reset Tool Wear"):
                twin.reset_tool()
                st.info("Tool reset to 0 minutes.")
                
        # Current telemetry metrics
        current = twin.get_telemetry()
        st.markdown("---")
        st.markdown("**Live Spindle Readings**")
        st.write(f"- Rotational Speed: **{current['rotational_speed_rpm']} RPM**")
        st.write(f"- Torque: **{current['torque_Nm']} Nm**")
        st.write(f"- Process Temp: **{current['process_temp_C']} \u00b0C** ({current['process_temp_K']} K)")
        st.write(f"- Tool Wear: **{current['tool_wear_min']} min**")
        st.write(f"- Vibration: **{current['vibration_rms']} mm/s RMS**")
        st.write(f"- Mechanical Power: **{current['power_W']} W**")
        
    with col_twin_viz:
        st.subheader("Live Telemetry Waveform")
        if len(st.session_state.history) > 1:
            hist_df = pd.DataFrame(st.session_state.history)
            fig_hist = make_subplots(rows=2, cols=1, shared_xaxes=True, subplot_titles=("RPM & Torque", "Temperatures (K)"))
            fig_hist.add_trace(go.Scatter(y=hist_df["rotational_speed_rpm"], name="RPM", line=dict(color="#38BDF8")), row=1, col=1)
            fig_hist.add_trace(go.Scatter(y=hist_df["torque_Nm"] * 25, name="Torque (scaled x25)", line=dict(color="#F59E0B")), row=1, col=1)
            fig_hist.add_trace(go.Scatter(y=hist_df["process_temp_K"], name="Process Temp (K)", line=dict(color="#EF4444")), row=2, col=1)
            fig_hist.add_trace(go.Scatter(y=hist_df["air_temp_K"], name="Air Temp (K)", line=dict(color="#10B981")), row=2, col=1)
            fig_hist.update_layout(template="plotly_dark", height=400, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig_hist, use_container_width=True)
        else:
            st.info("Click 'Step 1 Tick' to generate live simulation steps.")

# -------------------------------------------------------------
# PAGE 4: BATCH CSV UPLOAD & INFERENCE
# -------------------------------------------------------------
elif nav_choice == "4. Batch CSV Upload & Inference":
    st.title("Batch CSV Upload, Validation & Predictions")
    st.write("Upload telemetry CSV files to run automated validation, feature engineering, and batch failure inference.")
    
    uploaded_file = st.file_uploader("Upload Machine Telemetry CSV", type=["csv"])
    
    col_sample, col_info = st.columns([1, 2])
    with col_sample:
        if st.button("Load Sample Batch Test File (25 Machines)"):
            if os.path.exists("data/sample_batch_test.csv"):
                uploaded_file = "data/sample_batch_test.csv"
                
    if uploaded_file is not None:
        try:
            if isinstance(uploaded_file, str):
                df_upload = pd.read_csv(uploaded_file)
            else:
                df_upload = pd.read_csv(uploaded_file)
                
            st.success(f"Successfully uploaded CSV: {len(df_upload)} records detected.")
            
            # Validation
            required_cols = [
                'Air temperature [K]',
                'Process temperature [K]',
                'Rotational speed [rpm]',
                'Torque [Nm]',
                'Tool wear [min]'
            ]
            missing_cols = [c for c in required_cols if c not in df_upload.columns]
            
            if missing_cols:
                st.error(f"Validation Failed! Missing required columns: {missing_cols}")
            else:
                st.info("Data Validation Passed: All mandatory sensor columns present.")
                
                with st.spinner("Executing Batch ML Inference..."):
                    pred_df = predictor.predict_batch(df_upload)
                    
                risk_summary = pred_df['Risk_Category'].value_counts()
                c1, c2, c3 = st.columns(3)
                c1.metric("Healthy Machines", int(risk_summary.get("Healthy", 0)))
                c2.metric("Warning Machines", int(risk_summary.get("Warning", 0)))
                c3.metric("Critical Alerts", int(risk_summary.get("Critical", 0)))
                
                # Show results table
                st.subheader("Annotated Inference Results")
                st.dataframe(
                    pred_df[['Product ID' if 'Product ID' in pred_df.columns else 'Type', 'Rotational speed [rpm]', 'Torque [Nm]', 'Tool wear [min]', 'Failure_Probability', 'Risk_Category']],
                    use_container_width=True
                )
                
                # Download CSV
                csv_data = pred_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Annotated Predictions (CSV)",
                    data=csv_data,
                    file_name="machineguard_predictions.csv",
                    mime="text/csv",
                    type="primary"
                )
        except Exception as e:
            st.error(f"Error processing CSV: {e}")

# -------------------------------------------------------------
# PAGE 5: ANOMALY DETECTION & ALERTS
# -------------------------------------------------------------
elif nav_choice == "5. Anomaly Detection & Alerts":
    st.title("Multivariate Anomaly Detection & Alert History")
    st.write("Unsupervised Isolation Forest + Statistical Z-Score outlier detection across sensor dimensions.")
    
    if dataset is not None:
        sample_df = dataset.sample(800, random_state=42).copy()
        sample_df['Power_W'] = sample_df['Torque [Nm]'] * (sample_df['Rotational speed [rpm]'] * 2 * math.pi / 60)
        sample_df['Temp_diff'] = sample_df['Process temperature [K]'] - sample_df['Air temperature [K]']
        
        # Scatter of power vs temp difference
        fig_anom = px.scatter(
            sample_df, x="Temp_diff", y="Power_W",
            color=sample_df["Machine failure"].map({0: "Nominal", 1: "Failure / Outlier"}),
            color_discrete_map={"Nominal": "#38BDF8", "Failure / Outlier": "#EF4444"},
            title="Operational Manifold: Temperature Difference vs Mechanical Power (W)",
            labels={"Temp_diff": "\u0394T Process - Air (K)", "Power_W": "Power (Watts)"}
        )
        fig_anom.add_hline(y=3500, line_dash="dash", line_color="orange", annotation_text="Min Power Limit (3500W)")
        fig_anom.add_hline(y=9000, line_dash="dash", line_color="orange", annotation_text="Max Power Limit (9000W)")
        fig_anom.add_vline(x=8.6, line_dash="dash", line_color="red", annotation_text="HDF Delta-T Bound (8.6 K)")
        fig_anom.update_layout(template="plotly_dark", height=420)
        st.plotly_chart(fig_anom, use_container_width=True)
        
    st.subheader("Active & Past Alert History (SQLite)")
    alerts = get_alerts(limit=20)
    if alerts:
        alert_df = pd.DataFrame(alerts)
        st.dataframe(alert_df, use_container_width=True)
        
        col_act1, col_act2 = st.columns([1, 3])
        with col_act1:
            alert_id_to_ack = st.number_input("Alert ID to Acknowledge", min_value=1, step=1)
            if st.button("Acknowledge Alert"):
                update_alert_status(int(alert_id_to_ack), "Acknowledged")
                st.success(f"Alert #{alert_id_to_ack} marked as Acknowledged.")
                st.rerun()

# -------------------------------------------------------------
# PAGE 6: MAINTENANCE LOGS & WORK ORDERS
# -------------------------------------------------------------
elif nav_choice == "6. Maintenance Logs & Work Orders":
    st.title("Maintenance Logs & Work Order Management")
    st.write("Log machine repairs, tool replacements, and inspection notes into the SQLite database.")
    
    col_form, col_table = st.columns([1, 1.2])
    
    with col_form:
        st.subheader("Log Maintenance Work Order")
        with st.form("maint_form"):
            m_id = st.text_input("Machine ID", value="M14860")
            tech_name = st.text_input("Technician Name", value="Alex Henderson")
            m_type = st.selectbox("Maintenance Type", [
                "Tool Replacement (TWF)",
                "Cooling System Flush (HDF)",
                "Drive Belt / Motor Calibration (PWF)",
                "Spindle Bearing Overhaul",
                "Routine Inspection"
            ])
            priority = st.selectbox("Priority Level", ["Critical", "High", "Medium", "Low"])
            parts = st.text_input("Parts Replaced", value="12mm Carbide End Mill")
            notes = st.text_area("Work Description & Findings", value="Tool reached wear threshold. Replaced and re-calibrated zero datum.")
            status = st.selectbox("Work Order Status", ["Completed", "In Progress", "Scheduled"])
            
            submitted = st.form_submit_button("Save Maintenance Log", type="primary")
            if submitted:
                add_maintenance_log(m_id, tech_name, m_type, priority, parts, notes, status)
                st.success(f"Work order saved to SQLite for Machine {m_id}!")
                st.rerun()

    with col_table:
        st.subheader("Maintenance Log History")
        logs = get_maintenance_logs(limit=20)
        if logs:
            st.dataframe(pd.DataFrame(logs)[['id', 'machine_id', 'technician_name', 'maintenance_type', 'priority', 'status', 'created_at']], use_container_width=True)
        else:
            st.info("No maintenance logs recorded yet.")

# -------------------------------------------------------------
# PAGE 7: MODEL VERIFICATION & METRICS
# -------------------------------------------------------------
elif nav_choice == "7. Model Verification & Metrics":
    st.title("Model Verification & Academic Benchmark")
    st.write("Genuine evaluation metrics from the trained Scikit-learn Random Forest model on the AI4I 2020 dataset.")
    
    if metrics:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Accuracy", f"{metrics['accuracy']*100:.2f}%")
        c2.metric("ROC-AUC Score", f"{metrics['roc_auc']:.4f}")
        c3.metric("Recall (Failures)", f"{metrics['recall']*100:.2f}%")
        c4.metric("Precision", f"{metrics['precision']*100:.2f}%")
        
        st.markdown("---")
        
        col_cm, col_imp = st.columns(2)
        with col_cm:
            st.subheader("Confusion Matrix (Test Set: 2,000 Records)")
            cm = metrics["confusion_matrix"]
            cm_df = pd.DataFrame(
                cm,
                index=["Actual Healthy (0)", "Actual Failure (1)"],
                columns=["Pred Healthy (0)", "Pred Failure (1)"]
            )
            fig_cm = px.imshow(
                cm_df, text_auto=True, color_continuous_scale="Blues",
                title="Confusion Matrix"
            )
            fig_cm.update_layout(template="plotly_dark", height=320)
            st.plotly_chart(fig_cm, use_container_width=True)
            
        with col_imp:
            st.subheader("Feature Importance Rankings")
            feat_df = pd.DataFrame(
                list(metrics["feature_importance"].items()),
                columns=["Feature", "Importance"]
            ).sort_values("Importance", ascending=True)
            
            fig_imp = px.bar(
                feat_df, x="Importance", y="Feature", orientation="h",
                color="Importance", color_continuous_scale="Teal",
                title="Random Forest Gini Feature Importance"
            )
            fig_imp.update_layout(template="plotly_dark", height=320)
            st.plotly_chart(fig_imp, use_container_width=True)
            
        st.markdown("**Dataset & Model Validation Metadata**")
        st.json(metrics)
    else:
        st.warning("Metrics file not found. Run src/model_trainer.py to generate.")

st.markdown("---")
st.caption("MachineGuard AI \u00b7 Final-Year B.Tech CSE Capstone Project \u00b7 Developed with Python & Streamlit")
