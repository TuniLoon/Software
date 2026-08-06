"""
test_logger.py
Unit tests for the TelemetryLogger.
"""

import sys
import os
import json
import unittest
import tempfile
import shutil
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from ground_station.src.Logger import TelemetryLogger


class TestLogger(unittest.TestCase):
    """Test suite for TelemetryLogger."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.logger = TelemetryLogger(data_dir=self.test_dir, filename="test_log")
    
    def tearDown(self):
        """Clean up test environment."""
        self.logger.close()
        shutil.rmtree(self.test_dir)
    
    def test_csv_creation(self):
        """Test CSV file is created."""
        self.assertTrue(os.path.exists(self.logger.csv_path))
    
    def test_log_single(self):
        """Test logging a single data point."""
        data = {
            'timestamp': '2026-08-06T10:00:00',
            'timestamp_unix': 1786006800,
            'identifier': 'TUN',
            'latitude': 36.8442,
            'longitude': 10.1213,
            'altitude': 15234,
            'pressure': 1012.4,
            'temperature': 22.5,
            'humidity': 45.2,
            'thermal_avg': 28.7,
            'checksum': 5977,
            'status': 'A',
            'status_description': 'Ascent'
        }
        
        result = self.logger.log(data)
        self.assertTrue(result)
        
        # Check CSV content
        with open(self.logger.csv_path, 'r') as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 2)  # Header + 1 data row
    
    def test_log_batch(self):
        """Test logging multiple data points."""
        data_list = [
            {
                'timestamp': '2026-08-06T10:00:00',
                'timestamp_unix': 1786006800,
                'identifier': 'TUN',
                'latitude': 36.8442 + i * 0.001,
                'longitude': 10.1213 + i * 0.001,
                'altitude': 15234 + i * 100,
                'pressure': 1012.4 - i * 0.5,
                'temperature': 22.5 - i * 0.5,
                'humidity': 45.2 - i * 0.5,
                'thermal_avg': 28.7 - i * 0.5,
                'checksum': 5977 + i,
                'status': 'A',
                'status_description': 'Ascent'
            }
            for i in range(5)
        ]
        
        count = self.logger.log_batch(data_list)
        self.assertEqual(count, 5)
        
        # Check CSV content
        with open(self.logger.csv_path, 'r') as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 6)  # Header + 5 data rows
    
    def test_json_save(self):
        """Test saving to JSON."""
        data = {
            'timestamp': '2026-08-06T10:00:00',
            'timestamp_unix': 1786006800,
            'identifier': 'TUN',
            'latitude': 36.8442,
            'longitude': 10.1213,
            'altitude': 15234,
            'pressure': 1012.4,
            'temperature': 22.5,
            'humidity': 45.2,
            'thermal_avg': 28.7,
            'checksum': 5977,
            'status': 'A',
            'status_description': 'Ascent'
        }
        
        self.logger.log(data)
        json_path = self.logger.save_json()
        
        self.assertTrue(os.path.exists(json_path))
        
        with open(json_path, 'r') as f:
            saved_data = json.load(f)
            self.assertEqual(len(saved_data), 1)
            self.assertEqual(saved_data[0]['latitude'], 36.8442)
    
    def test_get_stats(self):
        """Test getting statistics."""
        # Log some data
        for i in range(5):
            data = {
                'timestamp': f'2026-08-06T10:00:{i:02d}',
                'timestamp_unix': 1786006800 + i * 30,
                'identifier': 'TUN',
                'latitude': 36.8442 + i * 0.001,
                'longitude': 10.1213 + i * 0.001,
                'altitude': 1000 + i * 500,
                'pressure': 1012.4 - i * 0.5,
                'temperature': 22.5 - i * 0.5,
                'humidity': 45.2 - i * 0.5,
                'thermal_avg': 28.7 - i * 0.5,
                'checksum': 5977 + i,
                'status': 'A' if i < 3 else 'D',
                'status_description': 'Ascent' if i < 3 else 'Descent'
            }
            self.logger.log(data)
        
        stats = self.logger.get_stats()
        self.assertEqual(stats['count'], 5)
        self.assertEqual(stats['min_altitude'], 1000)
        self.assertEqual(stats['max_altitude'], 3000)
        self.assertEqual(stats['status_counts']['Ascent'], 3)
        self.assertEqual(stats['status_counts']['Descent'], 2)


if __name__ == '__main__':
    unittest.main()
