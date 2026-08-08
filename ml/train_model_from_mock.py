"""
train_model_from_mock.py
Generate training data from the mock payload and train the anomaly detector.
Includes ALL flight phases (launch, ascent, peak, descent, landing).
"""

import sys
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from payload_simulator.src.MockPayload import MockPayload
from payload_simulator.src.SensorSimulator import SensorSimulator
from feature_extractor import FeatureExtractor
from anomaly_detector import AnomalyDetector

def generate_training_data(num_flights: int = 3):
    """
    Generate training data from multiple mock flights (full flight).
    
    Args:
        num_flights: Number of flights to simulate
    
    Returns:
        np.ndarray: Feature matrix (n_samples, n_features)
    """
    extractor = FeatureExtractor(window_size=10)
    sensor_sim = SensorSimulator()
    all_features = []
    
    for flight_idx in range(num_flights):
        print(f"[ML] Generating flight {flight_idx + 1}/{num_flights}...")
        payload = MockPayload(continuous=False)
        payload.generate_flight()
        
        # Use ALL points (0m → 30,000m → 0m)
        for point in payload.flight_path:
            altitude = point['altitude']
            sensors = sensor_sim.update(altitude, point['timestamp_seconds'])
            
            data = {
                'altitude': altitude,
                'temperature': sensors['temperature'],
                'pressure': sensors['pressure'],
                'humidity': sensors['humidity'],
                'thermal_avg': sensors['thermal_avg']
            }
            
            features = extractor.extract_features(data)
            all_features.append(features)
    
    return np.array(all_features)

if __name__ == "__main__":
    print("=" * 60)
    print("  Training Anomaly Detector on Full Flight Data")
    print("  (Includes launch, ascent, peak, descent, landing)")
    print("=" * 60)
    print()
    
    print("[ML] Generating training data...")
    X = generate_training_data(num_flights=3)
    print(f"[ML] Generated {X.shape[0]} samples with {X.shape[1]} features")
    
    print("[ML] Training Isolation Forest...")
    # Lower contamination to reduce false positives; 0.01 = 1% expected anomalies
    detector = AnomalyDetector(contamination=0.01)
    detector.train(X)
    
    model_dir = Path("ml/models")
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / "anomaly_model.pkl"
    detector.save_model(str(model_path))
    print(f"[ML] Model saved to {model_path}")
    
    print("[ML] Done!")
