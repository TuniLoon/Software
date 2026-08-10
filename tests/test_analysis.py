import sys
import unittest
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from analysis.flight_analyzer import FlightAnalyzer
from analysis.wind_estimator import WindEstimator
from analysis.report_generator import ReportGenerator

class TestAnalysis(unittest.TestCase):
    def setUp(self):
        self.data = [
            {'timestamp': '2026-08-10T10:00:00', 'altitude': 0, 'temperature': 25, 
             'latitude': 35.8276, 'longitude': 10.6402},
            {'timestamp': '2026-08-10T10:30:00', 'altitude': 15000, 'temperature': -30, 
             'latitude': 35.8280, 'longitude': 10.6410},
            {'timestamp': '2026-08-10T11:00:00', 'altitude': 30000, 'temperature': -60, 
             'latitude': 35.8290, 'longitude': 10.6420},
            {'timestamp': '2026-08-10T11:30:00', 'altitude': 100, 'temperature': 20, 
             'latitude': 35.8300, 'longitude': 10.6430},
        ]
    
    def test_flight_analyzer(self):
        analyzer = FlightAnalyzer(self.data)
        metrics = analyzer.get_metrics()
        self.assertAlmostEqual(metrics['max_altitude'], 30000, places=0)
        self.assertAlmostEqual(metrics['min_temperature'], -60, places=1)
        self.assertGreater(metrics['duration_hours'], 0)
    
    def test_wind_estimator(self):
        wind = WindEstimator(self.data)
        speed, direction = wind.get_wind()
        self.assertGreater(speed, 0)
        self.assertGreaterEqual(direction, 0)
        self.assertLessEqual(direction, 360)
    
    def test_report_generator(self):
        metrics = {'max_altitude': 30000, 'duration_hours': 2.0}
        report = ReportGenerator(metrics, wind_speed=10, wind_direction=90)
        md = report.generate_markdown()
        self.assertIn('30000', md)

if __name__ == '__main__':
    unittest.main()
