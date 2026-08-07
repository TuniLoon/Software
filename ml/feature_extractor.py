"""
feature_extractor.py
Feature engineering for anomaly detection.
Extracts rolling averages, derivatives, and volatility from telemetry data.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional

class FeatureExtractor:
    def __init__(self, window_size: int = 10):
        self.window_size = window_size
        self.buffer = []
        self.feature_names = []
    
    def extract_features(self, data_point: Dict) -> np.ndarray:
        """
        Extract features from a single data point, using historical buffer.
        
        Args:
            data_point: Telemetry data dict with keys:
                - altitude, temperature, pressure, humidity, thermal_avg
        
        Returns:
            np.ndarray: Feature vector
        """
        # Add to buffer
        self.buffer.append(data_point)
        
        # Keep only last window_size points
        if len(self.buffer) > self.window_size:
            self.buffer.pop(0)
        
        # If buffer is too small, use what we have
        if len(self.buffer) < 2:
            return self._get_zero_features()
        
        # Extract current values
        current = {
            'altitude': data_point.get('altitude', 0),
            'temperature': data_point.get('temperature', 0),
            'pressure': data_point.get('pressure', 0),
            'humidity': data_point.get('humidity', 0),
            'thermal_avg': data_point.get('thermal_avg', 0)
        }
        
        # Extract rolling features
        features = []
        
        # 1. Raw values
        features.extend([current['altitude'], current['temperature'], 
                        current['pressure'], current['humidity'], 
                        current['thermal_avg']])
        
        # 2. Rolling means
        if len(self.buffer) >= 3:
            df = pd.DataFrame(self.buffer)
            features.extend([
                df['altitude'].tail(3).mean(),
                df['temperature'].tail(3).mean(),
                df['pressure'].tail(3).mean(),
                df['humidity'].tail(3).mean(),
                df['thermal_avg'].tail(3).mean()
            ])
        else:
            features.extend([0, 0, 0, 0, 0])
        
        # 3. Derivatives (rate of change)
        if len(self.buffer) >= 2:
            prev = self.buffer[-2]
            dt = 1  # Assuming 1 second interval
            features.extend([
                (current['altitude'] - prev.get('altitude', 0)) / dt,
                (current['temperature'] - prev.get('temperature', 0)) / dt,
                (current['pressure'] - prev.get('pressure', 0)) / dt,
                (current['humidity'] - prev.get('humidity', 0)) / dt,
                (current['thermal_avg'] - prev.get('thermal_avg', 0)) / dt
            ])
        else:
            features.extend([0, 0, 0, 0, 0])
        
        # 4. Volatility (std dev) if enough data
        if len(self.buffer) >= 5:
            df = pd.DataFrame(self.buffer)
            features.extend([
                df['altitude'].tail(5).std(),
                df['temperature'].tail(5).std(),
                df['pressure'].tail(5).std(),
                df['humidity'].tail(5).std(),
                df['thermal_avg'].tail(5).std()
            ])
        else:
            features.extend([0, 0, 0, 0, 0])
        
        self.feature_names = [
            'altitude', 'temperature', 'pressure', 'humidity', 'thermal_avg',
            'alt_rolling_mean', 'temp_rolling_mean', 'press_rolling_mean', 
            'hum_rolling_mean', 'thermal_rolling_mean',
            'alt_derivative', 'temp_derivative', 'press_derivative',
            'hum_derivative', 'thermal_derivative',
            'alt_volatility', 'temp_volatility', 'press_volatility',
            'hum_volatility', 'thermal_volatility'
        ]
        
        return np.array(features)
    
    def _get_zero_features(self) -> np.ndarray:
        """Return zero features when buffer is empty."""
        return np.zeros(20)
    
    def reset(self):
        """Reset the buffer."""
        self.buffer = []


if __name__ == "__main__":
    # Test the feature extractor
    extractor = FeatureExtractor(window_size=10)
    
    # Simulate a flight
    test_data = [
        {'altitude': 1000, 'temperature': 20, 'pressure': 1010, 'humidity': 50, 'thermal_avg': 25},
        {'altitude': 1100, 'temperature': 19, 'pressure': 1008, 'humidity': 48, 'thermal_avg': 24},
        {'altitude': 1200, 'temperature': 18, 'pressure': 1006, 'humidity': 46, 'thermal_avg': 23},
    ]
    
    for point in test_data:
        features = extractor.extract_features(point)
        print(f"[TEST] Extracted {len(features)} features: {features[:5].round(2)}...")
    
    print(f"[TEST] Feature names: {extractor.feature_names[:5]}...")
