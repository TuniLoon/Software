"""
wind_estimator.py
Estimate wind speed and direction from GPS drift.
"""

import math
from typing import List, Dict, Tuple
from datetime import datetime

class WindEstimator:
    def __init__(self, data: List[Dict]):
        self.data = data
        self.wind_speed = 0.0
        self.wind_direction = 0.0
        if len(data) >= 2:
            self._estimate()
    
    def _haversine(self, lat1, lon1, lat2, lon2):
        R = 6371
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c
    
    def _estimate(self):
        start = self.data[0]
        end = self.data[-1]
        distance = self._haversine(start['latitude'], start['longitude'],
                                   end['latitude'], end['longitude'])
        t1 = datetime.fromisoformat(start['timestamp'])
        t2 = datetime.fromisoformat(end['timestamp'])
        duration = (t2 - t1).total_seconds()
        if duration > 0:
            self.wind_speed = (distance * 1000) / duration  # m/s
        else:
            self.wind_speed = 0.0
        
        # Bearing from start to end
        lat1, lon1 = math.radians(start['latitude']), math.radians(start['longitude'])
        lat2, lon2 = math.radians(end['latitude']), math.radians(end['longitude'])
        dlon = lon2 - lon1
        x = math.sin(dlon) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        bearing = math.atan2(x, y)
        bearing = math.degrees(bearing)
        self.wind_direction = (bearing + 360) % 360
    
    def get_wind(self) -> Tuple[float, float]:
        return (self.wind_speed, self.wind_direction)

if __name__ == "__main__":
    test_data = [
        {'timestamp': '2026-08-10T10:00:00', 'latitude': 35.8276, 'longitude': 10.6402},
        {'timestamp': '2026-08-10T11:00:00', 'latitude': 35.8300, 'longitude': 10.6430},
    ]
    wind = WindEstimator(test_data)
    speed, direction = wind.get_wind()
    print(f"Wind speed: {speed:.1f} m/s, Direction: {direction:.1f}°")
