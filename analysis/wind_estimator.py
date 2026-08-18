"""
wind_estimator.py – Sort data by timestamp before estimation.
"""

import math
from typing import List, Dict, Tuple
from datetime import datetime

class WindEstimator:
    def __init__(self, data: List[Dict] = None):
        print(f"[WindEstimator] __init__ called with {len(data) if data else 0} points")
        self.data = data or []
        # Sort data by timestamp in ascending order (oldest first)
        try:
            self.data.sort(key=lambda x: x.get('timestamp', ''))
        except:
            pass
        self.wind_speed = 0.0
        self.wind_direction = 0.0
        self.confidence = 0.0
        if len(self.data) >= 2:
            self._estimate()
        else:
            print("[WindEstimator] Not enough data (need >=2)")
    
    def _estimate(self):
        print("[WindEstimator] _estimate called")
        if len(self.data) < 2:
            return
        # Use the last two points in sorted order (which are the newest two, but in chronological order)
        p1 = self.data[-2]  # second oldest of the two
        p2 = self.data[-1]  # oldest? Actually after sorting ascending, the newest is last.
        # Now p1 is older than p2? Let's check: after sorting ascending, data[-1] is the latest timestamp.
        # So p1 (data[-2]) is older than p2 (data[-1]). That's correct for dt positive.
        print(f"[WindEstimator] p1 (older): {p1.get('timestamp')}")
        print(f"[WindEstimator] p2 (newer): {p2.get('timestamp')}")
        lat1 = p1.get('latitude', p1.get('lat', None))
        lon1 = p1.get('longitude', p1.get('lon', None))
        lat2 = p2.get('latitude', p2.get('lat', None))
        lon2 = p2.get('longitude', p2.get('lon', None))
        
        if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
            print("[WindEstimator] Missing lat/lon")
            return
        
        try:
            t1 = datetime.fromisoformat(p1['timestamp'])
            t2 = datetime.fromisoformat(p2['timestamp'])
        except Exception as e:
            print(f"[WindEstimator] Timestamp error: {e}")
            return
        
        dt = (t2 - t1).total_seconds()
        if dt <= 0:
            print(f"[WindEstimator] dt <= 0 ({dt})")
            return
        
        dist = self._haversine(lat1, lon1, lat2, lon2)
        if dist == 0:
            print("[WindEstimator] Distance is zero")
            return
        
        self.wind_speed = (dist * 1000) / dt
        self.wind_direction = self._bearing(lat1, lon1, lat2, lon2)
        self.confidence = 1.0
        print(f"[WindEstimator] SUCCESS: speed={self.wind_speed:.2f}, dir={self.wind_direction:.1f}, dist={dist*1000:.1f}m, dt={dt:.1f}s")
    
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
    
    def get_wind(self) -> Tuple[float, float]:
        return (self.wind_speed, self.wind_direction)
    
    def get_wind_with_confidence(self) -> Dict:
        return {
            'speed': self.wind_speed,
            'direction': self.wind_direction,
            'confidence': self.confidence
        }
