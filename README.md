# MachineGuard AI — Industrial Predictive Maintenance System

**Final-Year B.Tech Computer Science & Engineering Capstone Project**  
*Academic Project & Enterprise-Grade Predictive Maintenance Platform*

---

## 1. Project Overview & Motivation

In modern Industry 4.0 environments, unexpected machinery failure leads to severe downtime costs, catastrophic tool breakage, and compromised worker safety. **MachineGuard AI** is an end-to-end Predictive Maintenance (PdM) platform engineered using real industrial telemetry data from milling machines. 

The system leverages:
- **Supervised Machine Learning**: Random Forest Classifier trained on 10,000 real machine records from the UCI AI4I 2020 dataset to predict failure probability and classify risk into Healthy, Warning, and Critical alerts.
- **Physics-Informed Root Cause Diagnostics**: Deterministic diagnostic heuristics identifying five distinct failure modes: Tool Wear Failure (TWF), Heat Dissipation Failure (HDF), Power Failure (PWF), Overstrain Failure (OSF), and Random Failure (RNF).
- **Unsupervised Anomaly Detection**: Isolation Forest coupled with statistical multivariate Z-Score anomaly thresholding.
- **Physical Digital Twin**: Physics simulation of CNC spindle dynamics (thermal expansion, torque load, cutter wear, and vibration).
- **Relational Persistence**: SQLite3 database (`machineguard.db`) managing maintenance work orders, telemetry logs, and alert lifecycles.
- **Batch Data Pipeline**: CSV file validation, data cleaning, automated feature engineering, batch inference, and CSV report export.

---

## 2. Project Directory Structure

```text
MachineGuard-AI/
├── data/
│   ├── ai4i2020.csv             # Official UCI AI4I 2020 Predictive Maintenance dataset (10,000 records)
│   └── sample_batch_test.csv    # 25 curated test machine records for batch inference evaluation
├── models/
│   ├── machineguard_rf.joblib   # Trained Scikit-learn Random Forest Classifier (100 estimators)
│   ├── scaler.joblib            # StandardScaler for sensor normalization
│   ├── iso_forest.joblib        # Trained Isolation Forest model for anomaly detection
│   └── metrics.json             # Genuine training & validation evaluation metrics
├── src/
│   ├── __init__.py              # Python package marker
│   ├── model_trainer.py         # Data loading, feature engineering, and model training script
│   ├── predictor.py             # Inference pipeline & physics-based failure mode diagnostics
│   ├── anomaly_detector.py      # Isolation Forest & Z-Score anomaly detection engine
│   ├── digital_twin.py          # CNC Milling Spindle thermodynamic & kinematic digital twin
│   └── database.py              # SQLite database manager for maintenance logs and alerts
├── tests/
│   └── test_model.py            # Comprehensive Pytest test suite (8 test cases)
├── streamlit_app.py             # Streamlit interactive multi-page dashboard
├── requirements.txt             # Python package dependencies
├── machineguard.db              # SQLite relational database
└── README.md                    # Academic documentation and execution guide
```

---

## 3. How to Save and Export Your Complete Project Code

To ensure your academic work is never lost and can be submitted to your college, professor, or GitHub, use any of the following methods:

### Method A: Single-Click ZIP Download from the Web App (Recommended)
1. Open the MachineGuard AI Web interface in your browser.
2. In the top navigation bar or the "Project Code & Export" tab, click **"Download Complete Python Project (.ZIP)"**.
3. A compressed `.zip` file containing every Python script, test file, dataset, SQLite database, and documentation will download immediately to your local computer.

### Method B: Git Version Control (Local or Remote)
Initialize git inside your terminal:
```bash
git init
git add .
git commit -m "Initial commit of MachineGuard AI B.Tech project"
# Push to your personal GitHub repository:
git remote add origin https://github.com/<your-username>/MachineGuard-AI.git
git branch -M main
git push -u origin main
```

### Method C: Create Archive via Terminal
```bash
tar -czvf machineguard_ai_project.tar.gz data/ models/ src/ tests/ streamlit_app.py requirements.txt README.md machineguard.db
```

---

## 4. Dataset: AI4I 2020 Predictive Maintenance

The model is trained on the official **AI4I 2020 Predictive Maintenance Dataset** published by the UCI Machine Learning Repository.

- **Source**: UCI Machine Learning Repository (DOI: 10.24432/C5HS5C)
- **Total Instances**: 10,000 milling machine records
- **Class Distribution**:
  - Healthy (0): 9,661 records (96.61%)
  - Failure (1): 339 records (3.39%)
- **Product Types**:
  - `L` (Low Quality): 50% of records
  - `M` (Medium Quality): 30% of records
  - `H` (High Quality): 20% of records

### Mathematical Failure Mode Definitions:
1. **Tool Wear Failure (TWF)**: Occurs when tool wear reaches between 200 and 240 minutes.
2. **Heat Dissipation Failure (HDF)**: Occurs when temperature difference $\Delta T = T_{process} - T_{air} < 8.6\text{ K}$ and spindle speed $< 1380\text{ RPM}$.
3. **Power Failure (PWF)**: Occurs when mechanical power $P = \tau \times \omega < 3500\text{ W}$ or $> 9000\text{ W}$, where $\omega = \text{RPM} \times \frac{2\pi}{60}$.
4. **Overstrain Failure (OSF)**: Occurs when the product of Tool Wear and Torque exceeds:
   - $11,000\text{ min}\cdot\text{Nm}$ for Type L
   - $12,000\text{ min}\cdot\text{Nm}$ for Type M
   - $13,000\text{ min}\cdot\text{Nm}$ for Type H
5. **Random Failure (RNF)**: Background random failure process with $0.1\%$ probability.

---

## 5. Model Validation & Verified Results

Evaluation performed on an 80/20 stratified train-test split (8,000 training records, 2,000 held-out test records):

| Metric | Verified Value | Description |
| :--- | :--- | :--- |
| **Accuracy** | **98.50%** | Overall correct classification rate |
| **ROC-AUC Score** | **0.9749** | Area under the Receiver Operating Characteristic curve |
| **Recall (Failure Class)** | **83.82%** | Successfully detected 57 out of 68 real failures in test split |
| **Precision** | **75.00%** | 75% of flagged failures are true critical conditions |
| **F1-Score** | **0.7917** | Harmonic mean of precision and recall on imbalanced data |

### Confusion Matrix on Test Set ($N = 2,000$):
```text
                  Predicted Healthy    Predicted Failure
Actual Healthy          1,913                 19
Actual Failure            11                  57
```

---

## 6. Local Setup and Execution Instructions

### Prerequisites
- Python 3.10+ or Python 3.11+
- pip package manager

### Step 1: Clone or Extract the Project
```bash
cd MachineGuard-AI
```

### Step 2: Create a Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate    # On Windows: venv\Scripts\activate
```

### Step 3: Install Required Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Retrain the Model (Optional)
```bash
python3 src/model_trainer.py
```

### Step 5: Run the Pytest Test Suite
```bash
pytest tests/test_model.py -v
```
All 8 automated tests should pass.

### Step 6: Launch the Streamlit Web Application
```bash
streamlit run streamlit_app.py
```
Open `http://localhost:8501` in your browser.

---

## 7. Automated Test Verification Summary

The test suite in `tests/test_model.py` rigorously validates:
1. `test_dataset_exists_and_valid`: Confirms 10,000 records and all required sensor columns exist.
2. `test_predictor_nominal_machine`: Validates low failure probability for baseline operational parameters.
3. `test_predictor_tool_wear_failure_twf`: Validates tool wear $\ge 200\text{ min}$ triggers TWF diagnostic.
4. `test_predictor_heat_dissipation_failure_hdf`: Validates $\Delta T < 8.6\text{ K}$ and $\text{RPM} < 1380$ triggers HDF.
5. `test_predictor_overstrain_failure_osf`: Validates overstrain threshold triggers OSF.
6. `test_anomaly_detector`: Validates statistical Z-score and Isolation Forest outlier detection.
7. `test_database_crud`: Validates SQLite maintenance log insertions and alert status updates.
8. `test_digital_twin_simulation`: Validates spindle kinematic steps and scenario response.

---

## 8. Academic Citations

```bibtex
@misc{ai4i2020,
  author = {Matzka, Stephan},
  title = {AI4I 2020 Predictive Maintenance Dataset},
  year = {2020},
  publisher = {UCI Machine Learning Repository},
  doi = {10.24432/C5HS5C}
}
```
