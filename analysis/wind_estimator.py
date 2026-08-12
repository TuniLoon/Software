"""
wind_estimator.py
Estimate wind speed and direction from GPS drift (live telemetry).
"""

import math
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta

class WindEstimator:
    def __init__(self, data: List[Dict] = None):
        self.data = data or []
        self.wind_speed = 0.0
        self.wind_direction = 0.0
        self.confidence = 0.0
        if len(self.data) >= 2:
            self._estimate()
    
    def _haversine(self, lat1, lon1, lat2, lon2):
        R = 6371
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c
    
    def _bearing(self, lat1, lon1, lat2, lon2):
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlon = lon2 - lon1
        x = math.sin(dlon) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        bearing = math.degrees(math.atan2(x, y))
        return (bearing + 360) % 360
    
    def _estimate(self):
        """Compute wind from telemetry data (average over last N points)."""
        if len(self.data) < 2:
            return
        
        # Use last N points (max 10) for smooth estimation
        window = min(len(self.data), 10)
        points = self.data[-window:]
        
        total_speed = 0.0
        total_dir = 0.0
        count = 0
        
        for i in range(1, len(points)):
            p1 = points[i-1]
            p2 = points[i]
            try:
                dt = (datetime.fromisoformat(p2['timestamp']) - 
                      datetime.fromisoformat(p1['timestamp'])).total_seconds()
                if dt <= 0:
                    continue
                distance = self._haversine(p1['latitude'], p1['longitude'],
                                          p2['latitude'], p2['longitude'])
                speed = (distance * 1000) / dt  # m/s
                bearing = self._bearing(p1['latitude'], p1['longitude'],
                                       p2['latitude'], p2['longitude'])
                # Weight by distance (longer distances = more reliable)
                weight = distance
                total_speed += speed * weight
                total_dir += bearing * weight
                count += weight
            except:
                continue
        
        if count > 0:
            self.wind_speed = total_speed / count
            self.wind_direction = total_dir / count
            self.confidence = min(1, len(points) / 10)
    
    def get_wind(self) -> Tuple[float, float]:
        return (self.wind_speed, self.wind_direction)
    
    def get_wind_with_confidence(self) -> Dict:
        return {
            'speed': self.wind_speed,
            'direction': self.wind_direction,
            'confidence': self.confidence
        }
    
    def update(self, data: List[Dict]):
        """Add new data and re‑estimate."""
        self.data = data
        if len(data) >= 2:
            self._estimate()
        return self.get_wind_with_confidence()
