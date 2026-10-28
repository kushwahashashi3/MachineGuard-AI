"""
MachineGuard AI - Industrial Digital Twin Simulation Model
Simulates physical telemetry of a CNC milling spindle in real-time,
tracking thermodynamic, kinematic, and degradation dynamics.
"""

import math
import random
import time

class DigitalTwinSpindle:
    def __init__(self, machine_id="CNC-DT-01", product_type="M"):
        self.machine_id = machine_id
        self.product_type = product_type
        
        # State variables
        self.air_temp = 298.5          # Ambient Kelvin (~25.35 C)
        self.process_temp = 308.7      # Tool-workpiece interface Kelvin (~35.55 C)
        self.rpm = 1520.0              # Rotational speed (RPM)
        self.torque = 41.2             # Torque (Nm)
        self.tool_wear = 85.0          # Tool wear (min)
        
        # Derived telemetry
        self.vibration_rms = 1.8       # mm/s RMS
        self.power_w = 6560.0          # Watts
        self.is_running = True
        self.scenario = "nominal"      # nominal, thermal_stress, over_torque, tool_degraded
        self.step_count = 0

    def set_scenario(self, scenario_name):
        valid = ["nominal", "thermal_stress", "over_torque", "tool_degraded", "emergency_stop"]
        if scenario_name in valid:
            self.scenario = scenario_name
            
    def update_tick(self, delta_time_sec=1.0):
        self.step_count += 1
        
        if not self.is_running or self.scenario == "emergency_stop":
            self.rpm = max(0.0, self.rpm * 0.7)
            self.torque = max(0.0, self.torque * 0.5)
            self.vibration_rms = max(0.2, self.vibration_rms * 0.8)
            self.process_temp = max(self.air_temp, self.process_temp - 0.2)
            return self.get_telemetry()
            
        noise_rpm = random.gauss(0, 8.0)
        noise_torque = random.gauss(0, 0.6)
        noise_temp = random.gauss(0, 0.05)
        
        if self.scenario == "nominal":
            target_rpm = 1530.0
            target_torque = 40.0
            self.rpm += (target_rpm - self.rpm) * 0.1 + noise_rpm
            self.torque += (target_torque - self.torque) * 0.1 + noise_torque
            target_temp = self.air_temp + 10.2
            self.process_temp += (target_temp - self.process_temp) * 0.05 + noise_temp
            self.vibration_rms = 1.6 + random.uniform(-0.15, 0.15)
            self.tool_wear += 0.08 * (delta_time_sec / 1.0)
            
        elif self.scenario == "thermal_stress":
            # Coolant failure simulation: low temp difference or extreme thermal buildup
            self.air_temp += 0.05
            self.process_temp += 0.45 + noise_temp  # Rapid heating
            self.rpm = max(1150.0, self.rpm - 15.0)  # Struggling spindle motor
            self.torque += 0.35
            self.vibration_rms = 3.2 + random.uniform(-0.3, 0.3)
            self.tool_wear += 0.15
            
        elif self.scenario == "over_torque":
            # Excessive feed rate or hardened inclusion: high torque & low RPM
            self.torque = min(78.0, self.torque + 2.5 + noise_torque)
            self.rpm = max(1200.0, self.rpm - 25.0)
            self.vibration_rms = 4.6 + random.uniform(-0.4, 0.4)
            self.tool_wear += 0.25
            self.process_temp += 0.2
            
        elif self.scenario == "tool_degraded":
            # Tool nearing expiration (>= 210 min)
            self.tool_wear = max(self.tool_wear, 215.0) + 0.12
            self.vibration_rms = 3.9 + random.uniform(-0.25, 0.25)
            self.torque = 52.0 + noise_torque
            
        # Physical bounds
        self.rpm = max(0.0, min(2800.0, self.rpm))
        self.torque = max(3.0, min(85.0, self.torque))
        angular_vel = self.rpm * (2 * math.pi / 60)
        self.power_w = self.torque * angular_vel
        
        return self.get_telemetry()
        
    def get_telemetry(self):
        temp_diff = self.process_temp - self.air_temp
        overstrain = self.tool_wear * self.torque
        
        return {
            "machine_id": self.machine_id,
            "product_type": self.product_type,
            "scenario": self.scenario,
            "air_temp_K": round(self.air_temp, 2),
            "air_temp_C": round(self.air_temp - 273.15, 2),
            "process_temp_K": round(self.process_temp, 2),
            "process_temp_C": round(self.process_temp - 273.15, 2),
            "temp_diff_K": round(temp_diff, 2),
            "rotational_speed_rpm": round(self.rpm, 1),
            "torque_Nm": round(self.torque, 2),
            "tool_wear_min": round(self.tool_wear, 1),
            "vibration_rms": round(self.vibration_rms, 2),
            "power_W": round(self.power_w, 1),
            "overstrain_min_Nm": round(overstrain, 1),
            "step_count": self.step_count,
            "timestamp": time.time()
        }

    def reset_tool(self):
        self.tool_wear = 0.0
        self.scenario = "nominal"
        self.process_temp = self.air_temp + 10.0
        self.vibration_rms = 1.4
