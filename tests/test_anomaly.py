"""
test_anomaly.py
Unit tests for anomaly detection.
"""

import sys
import unittest
import numpy as np
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from ml.anomaly_detector import AnomalyDetector
from ml.feature_extractor import FeatureExtractor
from ml.real_time_detector import RealTimeAnomalyDetector


class TestFeatureExtractor(unittest.TestCase):
    def test_extract_features(self):
        extractor = FeatureExtractor(window_size=5)
        
        # Add multiple points to fill buffer
        points = [
            {'altitude': 1000, 'temperature': 20, 'pressure': 1010, 'humidity': 50, 'thermal_avg': 25},
            {'altitude': 1010, 'temperature': 19, 'pressure': 1009, 'humidity': 49, 'thermal_avg': 24},
            {'altitude': 1020, 'temperature': 18, 'pressure': 1008, 'humidity': 48, 'thermal_avg': 23},
            {'altitude': 1030, 'temperature': 17, 'pressure': 1007, 'humidity': 47, 'thermal_avg': 22},
            {'altitude': 1040, 'temperature': 16, 'pressure': 1006, 'humidity': 46, 'thermal_avg': 21},
        ]
        
        for p in points:
            features = extractor.extract_features(p)
        
        # After processing all points, the last feature vector should have altitude = 1040
        self.assertEqual(features[0], 1040)
    
    def test_buffer_increases(self):
        extractor = FeatureExtractor(window_size=3)
        self.assertEqual(len(extractor.buffer), 0)
        
        extractor.extract_features({'altitude': 1000, 'temperature': 20, 
                                   'pressure': 1010, 'humidity': 50, 'thermal_avg': 25})
        self.assertEqual(len(extractor.buffer), 1)
    
    def test_reset(self):
        extractor = FeatureExtractor()
        extractor.extract_features({'altitude': 1000, 'temperature': 20, 
                                   'pressure': 1010, 'humidity': 50, 'thermal_avg': 25})
        self.assertGreater(len(extractor.buffer), 0)
        extractor.reset()
        self.assertEqual(len(extractor.buffer), 0)


class TestAnomalyDetector(unittest.TestCase):
    def test_train_and_predict(self):
        detector = AnomalyDetector(contamination=0.1)
        
        # Generate training data (20 features to match FeatureExtractor)
        np.random.seed(42)
        normal = np.random.normal(0, 1, (100, 20))
        anomalies = np.random.normal(5, 1, (10, 20))
        all_data = np.vstack([normal, anomalies])
        
        detector.train(all_data)
        self.assertTrue(detector.is_trained)
        
        # Test prediction
        test_normal = np.random.normal(0, 1, (1, 20))
        test_anomaly = np.random.normal(6, 1, (1, 20))
        
        result_normal = detector.predict(test_normal)
        result_anomaly = detector.predict(test_anomaly)
        
        self.assertIn('is_anomaly', result_normal)
        self.assertIn('anomaly_score', result_normal)
        self.assertIn('confidence', result_normal)
    
    def test_save_load(self):
        detector = AnomalyDetector()
        np.random.seed(42)
        data = np.random.normal(0, 1, (100, 20))
        detector.train(data)
        
        # Save
        path = "ml/models/test_save.pkl"
        detector.save_model(path)
        
        # Load into new detector
        detector2 = AnomalyDetector()
        detector2.load_model(path)
        self.assertTrue(detector2.is_trained)
        
        # Clean up
        import os
        os.remove(path)
        os.rmdir("ml/models")


class TestRealTimeDetector(unittest.TestCase):
    def test_process_telemetry(self):
        detector = RealTimeAnomalyDetector()
        detector.initialize()
        
        # Process normal data
        data = {'altitude': 1000, 'temperature': 20, 'pressure': 1010, 
                'humidity': 50, 'thermal_avg': 25}
        result = detector.process_telemetry(data)
        
        self.assertIn('is_anomaly', result)
        self.assertIn('alert_triggered', result)
        self.assertEqual(result['data']['altitude'], 1000)
    
    def test_reset(self):
        detector = RealTimeAnomalyDetector()
        detector.initialize()
        
        data = {'altitude': 1000, 'temperature': 20, 'pressure': 1010, 
                'humidity': 50, 'thermal_avg': 25}
        detector.process_telemetry(data)
        self.assertGreater(len(detector.extractor.buffer), 0)
        
        detector.reset()
        self.assertEqual(len(detector.extractor.buffer), 0)


if __name__ == '__main__':
    unittest.main()
