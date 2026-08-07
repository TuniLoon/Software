"""
real_time_detector.py
Real-time anomaly detection with alert integration.
"""

import json
import time
import numpy as np
from pathlib import Path
from typing import Dict, Optional
import sys

sys.path.append(str(Path(__file__).parent.parent))

from ml.feature_extractor import FeatureExtractor
from ml.anomaly_detector import AnomalyDetector

class RealTimeAnomalyDetector:
    """Real-time anomaly detection with alerting."""
    
    def __init__(self, config_path: str = "config/ml_config.json"):
        self.config_path = config_path
        self.load_config()
        
        self.extractor = FeatureExtractor(
            window_size=self.config.get('features', {}).get('window_size', 10)
        )
        
        self.detector = AnomalyDetector(
            contamination=self.config.get('model', {}).get('contamination', 0.05)
        )
        
        self.model_path = self.config.get('training', {}).get(
            'model_save_path', 'ml/models/anomaly_model.pkl'
        )
        
        self.is_initialized = False
        self.alert_count = 0
    
    def load_config(self):
        """Load configuration."""
        try:
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
            print(f"[ML] Config loaded from {self.config_path}")
        except FileNotFoundError:
            print(f"[ML] Config not found, using defaults")
            self.config = {
                'model': {'contamination': 0.05},
                'features': {'window_size': 10},
                'thresholds': {'anomaly_score': 0.1, 'confidence': 0.7}
            }
    
    def initialize(self, training_data_path: Optional[str] = None):
        """
        Initialize the detector by loading or training the model.
        
        Args:
            training_data_path: Path to training data CSV (optional)
        """
        # Try to load existing model
        if Path(self.model_path).exists():
            self.detector.load_model(self.model_path)
            self.is_initialized = True
            print("[ML] Model loaded from disk")
            return
        
        # If no model, train from data
        if training_data_path and Path(training_data_path).exists():
            print(f"[ML] Training model from {training_data_path}")
            import pandas as pd
            df = pd.read_csv(training_data_path)
            
            # Extract features using the feature extractor
            features = []
            for _, row in df.iterrows():
                data = {
                    'altitude': row.get('altitude', 0),
                    'temperature': row.get('temperature', 0),
                    'pressure': row.get('pressure', 0),
                    'humidity': row.get('humidity', 0),
                    'thermal_avg': row.get('thermal_avg', 0)
                }
                f = self.extractor.extract_features(data)
                features.append(f)
            
            features = np.array(features)
            self.detector.train(features)
            self.detector.save_model(self.model_path)
            self.is_initialized = True
            print("[ML] Model trained and saved")
        else:
            # No training data – use random data with CORRECT number of features
            print("[ML] No training data found. Using random model for testing.")
            
            # Generate random training data with 20 features (matches FeatureExtractor output)
            normal_data = np.random.normal(0, 1, (200, 20))
            anomalies = np.random.normal(5, 1, (20, 20))
            all_data = np.vstack([normal_data, anomalies])
            
            self.detector.train(all_data)
            self.is_initialized = True
            print("[ML] Random model initialized (for testing only)")
    
    def process_telemetry(self, data: Dict) -> Dict:
        """
        Process a telemetry data point and check for anomalies.
        
        Args:
            data: Telemetry data dict
        
        Returns:
            Dict with keys:
                - data (original data)
                - is_anomaly (bool)
                - anomaly_score (float)
                - confidence (float)
                - alert_triggered (bool)
        """
        if not self.is_initialized:
            self.initialize()
        
        # Extract features (returns 20 features)
        features = self.extractor.extract_features(data)
        
        # Predict anomaly
        result = self.detector.predict(features)
        
        # Check thresholds
        threshold = self.config.get('thresholds', {})
        confidence_threshold = threshold.get('confidence', 0.7)
        
        is_anomaly = result['is_anomaly']
        confidence = result['confidence']
        anomaly_score = result['anomaly_score']
        
        alert_triggered = False
        
        if is_anomaly and confidence > confidence_threshold:
            alert_triggered = True
            self.alert_count += 1
            print(f"🚨 ANOMALY DETECTED! Score: {anomaly_score:.2f}, "
                  f"Confidence: {confidence:.2f}")
            print(f"   Altitude: {data.get('altitude', 0):.0f}m, "
                  f"Temp: {data.get('temperature', 0):.1f}°C")
        
        return {
            'data': data,
            'is_anomaly': is_anomaly,
            'anomaly_score': anomaly_score,
            'confidence': confidence,
            'alert_triggered': alert_triggered
        }
    
    def reset(self):
        """Reset the feature extractor buffer."""
        self.extractor.reset()
        print("[ML] Detector reset")


if __name__ == "__main__":
    print("=" * 60)
    print("  TuniLoon Real-Time Anomaly Detector")
    print("=" * 60)
    print()
    
    # Initialize the detector
    detector = RealTimeAnomalyDetector()
    detector.initialize()
    
    # Simulate incoming telemetry
    print("[TEST] Simulating telemetry stream...")
    
    test_data = [
        {'altitude': 1000, 'temperature': 20, 'pressure': 1010, 'humidity': 50, 'thermal_avg': 25},
        {'altitude': 1100, 'temperature': 19, 'pressure': 1008, 'humidity': 48, 'thermal_avg': 24},
        {'altitude': 1200, 'temperature': 18, 'pressure': 1006, 'humidity': 46, 'thermal_avg': 23},
        # This should trigger an anomaly (sudden jump)
        {'altitude': 5000, 'temperature': -10, 'pressure': 800, 'humidity': 20, 'thermal_avg': 10},
        {'altitude': 1300, 'temperature': 17, 'pressure': 1004, 'humidity': 44, 'thermal_avg': 22},
    ]
    
    for i, point in enumerate(test_data):
        result = detector.process_telemetry(point)
        status = "🚨 ANOMALY" if result['alert_triggered'] else "✅ Normal"
        print(f"[{i+1}] Alt={point['altitude']}m | {status}")
        time.sleep(1)
    
    print("\n[TEST] ✅ Real-time detector works!")
