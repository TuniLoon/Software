"""
flight_analyzer.py
Compute flight metrics from telemetry data.
"""

import math
from typing import List, Dict
from datetime import datetime

class FlightAnalyzer:
    def __init__(self, data: List[Dict]):
        self.data = data
        self.metrics = {}
        if data:
            self._compute()
    
    def _haversine(self, lat1, lon1, lat2, lon2):
        R = 6371
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c
    
    def _compute(self):
        if not self.data:
            return
        
        altitudes = [d['altitude'] for d in self.data]
        temperatures = [d['temperature'] for d in self.data]
        pressures = [d.get('pressure', 0) for d in self.data]
        
        self.metrics['start_time'] = self.data[0]['timestamp']
        self.metrics['end_time'] = self.data[-1]['timestamp']
        
        start_dt = datetime.fromisoformat(self.data[0]['timestamp'])
        end_dt = datetime.fromisoformat(self.data[-1]['timestamp'])
        duration = (end_dt - start_dt).total_seconds()
        self.metrics['duration_seconds'] = duration
        self.metrics['duration_hours'] = duration / 3600.0
        
        self.metrics['max_altitude'] = max(altitudes)
        self.metrics['min_altitude'] = min(altitudes)
        self.metrics['max_temperature'] = max(temperatures)
        self.metrics['min_temperature'] = min(temperatures)
        self.metrics['avg_temperature'] = sum(temperatures) / len(temperatures)
        self.metrics['max_pressure'] = max(pressures) if pressures else 0
        self.metrics['min_pressure'] = min(pressures) if pressures else 0
        
        peak_idx = altitudes.index(self.metrics['max_altitude'])
        ascent_data = self.data[:peak_idx+1]
        descent_data = self.data[peak_idx:]
        
        if len(ascent_data) > 1:
            alt_diff = ascent_data[-1]['altitude'] - ascent_data[0]['altitude']
            t1 = datetime.fromisoformat(ascent_data[0]['timestamp'])
            t2 = datetime.fromisoformat(ascent_data[-1]['timestamp'])
            time_diff = (t2 - t1).total_seconds()
            self.metrics['avg_ascent_rate'] = alt_diff / time_diff if time_diff > 0 else 0
        else:
            self.metrics['avg_ascent_rate'] = 0
        
        if len(descent_data) > 1:
            alt_diff = descent_data[0]['altitude'] - descent_data[-1]['altitude']
            t1 = datetime.fromisoformat(descent_data[0]['timestamp'])
            t2 = datetime.fromisoformat(descent_data[-1]['timestamp'])
            time_diff = (t2 - t1).total_seconds()
            self.metrics['avg_descent_rate'] = alt_diff / time_diff if time_diff > 0 else 0
        else:
            self.metrics['avg_descent_rate'] = 0
        
        total_dist = 0.0
        for i in range(1, len(self.data)):
            total_dist += self._haversine(
                self.data[i-1]['latitude'],
                self.data[i-1]['longitude'],
                self.data[i]['latitude'],
                self.data[i]['longitude']
            )
        self.metrics['total_distance_km'] = total_dist
        
        last = self.data[-1]
        self.metrics['landing_location'] = (last['latitude'], last['longitude'])
        self.metrics['landing_time'] = last['timestamp']
        
        peak = self.data[peak_idx]
        self.metrics['peak_location'] = (peak['latitude'], peak['longitude'])
        self.metrics['peak_time'] = peak['timestamp']
    
    def get_metrics(self) -> Dict:
        return self.metrics

if __name__ == "__main__":
    test_data = [
        {'timestamp': '2026-08-10T10:00:00', 'altitude': 0, 'temperature': 25, 'latitude': 35.8276, 'longitude': 10.6402},
        {'timestamp': '2026-08-10T10:30:00', 'altitude': 15000, 'temperature': -30, 'latitude': 35.8280, 'longitude': 10.6410},
        {'timestamp': '2026-08-10T11:00:00', 'altitude': 30000, 'temperature': -60, 'latitude': 35.8290, 'longitude': 10.6420},
        {'timestamp': '2026-08-10T11:30:00', 'altitude': 100, 'temperature': 20, 'latitude': 35.8300, 'longitude': 10.6430},
    ]
    analyzer = FlightAnalyzer(test_data)
    print("Flight Analyzer test passed!")
    print(analyzer.get_metrics())
