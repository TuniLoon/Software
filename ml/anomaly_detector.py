"""
anomaly_detector.py
Machine Learning anomaly detection using Isolation Forest.
"""

import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from typing import Dict, Optional, List
from pathlib import Path

class AnomalyDetector:
    """Anomaly detection using Isolation Forest."""
    
    def __init__(self, contamination: float = 0.05, random_state: int = 42):
        self.contamination = contamination
        self.random_state = random_state
        self.model = IsolationForest(
            contamination=contamination,
            random_state=random_state,
            n_estimators=100
        )
        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_names = []
    
    def train(self, features: np.ndarray) -> 'AnomalyDetector':
        """
        Train the model on historical data.
        
        Args:
            features: Feature matrix (n_samples, n_features)
        
        Returns:
            self (for chaining)
        """
        # Scale features
        features_scaled = self.scaler.fit_transform(features)
        
        # Train Isolation Forest
        self.model.fit(features_scaled)
        self.is_trained = True
        
        print(f"[ML] Model trained on {features.shape[0]} samples")
        return self
    
    def train_from_dataframe(self, df: pd.DataFrame, feature_columns: List[str]) -> 'AnomalyDetector':
        """
        Train from a pandas DataFrame.
        
        Args:
            df: DataFrame containing training data
            feature_columns: List of column names to use as features
        
        Returns:
            self (for chaining)
        """
        self.feature_names = feature_columns
        features = df[feature_columns].values
        return self.train(features)
    
    def predict(self, features: np.ndarray) -> Dict:
        """
        Predict if a sample is an anomaly.
        
        Args:
            features: Feature vector (1D or 2D array)
        
        Returns:
            Dict with keys:
                - is_anomaly (bool)
                - anomaly_score (float)
                - confidence (float)
        """
        if not self.is_trained:
            raise ValueError("Model not trained. Call train() first.")
        
        # Ensure 2D
        if features.ndim == 1:
            features = features.reshape(1, -1)
        
        # Scale
        features_scaled = self.scaler.transform(features)
        
        # Predict (-1 = anomaly, 1 = normal)
        predictions = self.model.predict(features_scaled)
        scores = self.model.score_samples(features_scaled)
        
        # Convert to results
        is_anomaly = predictions[0] == -1
        anomaly_score = scores[0]
        
        # Confidence (normalized to 0-1)
        confidence = min(1, abs(anomaly_score) / 0.5)
        
        return {
            'is_anomaly': is_anomaly,
            'anomaly_score': anomaly_score,
            'confidence': confidence
        }
    
    def save_model(self, path: str = "ml/models/anomaly_model.pkl"):
        """Save the trained model."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({
            'model': self.model,
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'contamination': self.contamination,
            'random_state': self.random_state
        }, path)
        print(f"[ML] Model saved to {path}")
    
    def load_model(self, path: str = "ml/models/anomaly_model.pkl"):
        """Load a trained model."""
        data = joblib.load(path)
        self.model = data['model']
        self.scaler = data['scaler']
        self.feature_names = data.get('feature_names', [])
        self.contamination = data.get('contamination', 0.05)
        self.random_state = data.get('random_state', 42)
        self.is_trained = True
        print(f"[ML] Model loaded from {path}")


if __name__ == "__main__":
    # Test the anomaly detector
    print("[TEST] Training anomaly detector on random data...")
    
    # Generate normal data
    np.random.seed(42)
    normal_data = np.random.normal(0, 1, (100, 5))
    
    # Generate some anomalies
    anomalies = np.random.normal(5, 1, (10, 5))
    all_data = np.vstack([normal_data, anomalies])
    
    # Train
    detector = AnomalyDetector(contamination=0.1)
    detector.train(all_data)
    detector.save_model("ml/models/test_model.pkl")
    
    # Test prediction
    test_normal = np.random.normal(0, 1, (1, 5))
    test_anomaly = np.random.normal(6, 1, (1, 5))
    
    result_normal = detector.predict(test_normal)
    result_anomaly = detector.predict(test_anomaly)
    
    print(f"[TEST] Normal sample: {result_normal}")
    print(f"[TEST] Anomaly sample: {result_anomaly}")
    
    # Clean up
    import os
    os.remove("ml/models/test_model.pkl")
    os.rmdir("ml/models")
    
    print("[TEST] ✅ Anomaly detector works!")
