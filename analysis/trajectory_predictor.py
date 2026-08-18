"""
trajectory_predictor.py
Predict future balloon trajectory using wind model.
"""

import math
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional

class TrajectoryPredictor:
    def __init__(self, weather_service, wind_config: dict = None):
        self.weather = weather_service
        self.wind_config = wind_config or {}
        self.max_altitude = self.wind_config.get('max_altitude', 30000)
    
    def _get_wind_at_altitude(self, lat, lon, alt, time_dt):
        """Get forecast wind at altitude (scaled from surface)."""
        # Get surface forecast
        forecast = self.weather.get_forecast(lat, lon, cnt=8)
        if not forecast:
            return None
        
        # Find closest forecast time
        best = None
        for item in forecast.get('list', []):
            ft = datetime.fromtimestamp(item['dt'])
            if abs((ft - time_dt).total_seconds()) < 7200:
                best = item
                break
        if not best:
            best = forecast['list'][0]
        
        wind = best.get('wind', {'speed': 0, 'deg': 0})
        speed = wind.get('speed', 0)
        direction = wind.get('deg', 0)
        
        # Scale wind with altitude (simplified: increases up to 5000m, then constant)
        altitude_factor = min(1, alt / 5000) * 1.5
        speed = speed * (1 + altitude_factor)
        return {'speed': speed, 'deg': direction}
    
    def predict(self, start_lat, start_lon, start_alt, start_time, duration=3600, step=60):
        """
        Predict trajectory for the next `duration` seconds.
        Returns list of points with lat, lon, alt, time.
        """
        points = []
        cur_lat, cur_lon = start_lat, start_lon
        cur_alt = start_alt
        cur_time = start_time
        total_time = 0
        
        while total_time < duration:
            # Get wind at current position
            wind = self._get_wind_at_altitude(cur_lat, cur_lon, cur_alt, cur_time)
            if not wind:
                break
            
            speed = wind.get('speed', 0)
            direction = wind.get('deg', 0)
            dir_rad = math.radians(direction)
            
            # Convert to lat/lon change
            dt = step
            dx = speed * dt * math.sin(dir_rad) / (111320 * math.cos(math.radians(cur_lat)))
            dy = speed * dt * math.cos(dir_rad) / 111320
            
            cur_lat += dy
            cur_lon += dx
            cur_time += timedelta(seconds=dt)
            total_time += dt
            
            # Altitude continues from current ascent/descent profile
            # We'll use the same profile as FlightPlanner for simplicity
            ascent_duration = self.max_altitude / 5.0  # 5 m/s ascent
            if total_time < ascent_duration:
                cur_alt = min(5.0 * total_time, self.max_altitude)
            else:
                desc_time = total_time - ascent_duration
                cur_alt = max(self.max_altitude - 15.0 * desc_time, 0)
            
            points.append({
                'time': total_time,
                'latitude': cur_lat,
                'longitude': cur_lon,
                'altitude': cur_alt,
                'wind_speed': speed,
                'wind_direction': direction
            })
            
            if cur_alt <= 0 and total_time > 600:
                break
        
        return points
    
    def predict_landing(self, start_lat, start_lon, start_alt, start_time, duration=7200):
        """Run prediction and return landing location."""
        points = self.predict(start_lat, start_lon, start_alt, start_time, duration)
        if not points:
            return None
        last = points[-1]
        return {
            'landing_lat': last['latitude'],
            'landing_lon': last['longitude'],
            'landing_time': start_time + timedelta(seconds=last['time']),
            'duration': last['time'],
            'trajectory': points
        }

if __name__ == "__main__":
    # Test
    from ground_station.src.weather_service import WeatherService
    ws = WeatherService()
    predictor = TrajectoryPredictor(ws)
    from datetime import datetime
    result = predictor.predict_landing(35.8276, 10.6402, 0, datetime.now())
    if result:
        print(f"Landing: {result['landing_lat']:.4f}, {result['landing_lon']:.4f}")
        print(f"Duration: {result['duration']:.0f}s")

    def _get_wind_at_altitude(self, lat, lon, alt, time_dt):
        """Get forecast wind at altitude (scaled from surface)."""
        # Get surface forecast
        forecast = self.weather.get_forecast(lat, lon, cnt=8)
        if not forecast:
            return None
        # Find closest forecast time
        best = None
        for item in forecast.get('list', []):
            ft = datetime.fromtimestamp(item['dt'])
            if abs((ft - time_dt).total_seconds()) < 7200:
                best = item
                break
        if not best:
            best = forecast['list'][0]
        wind = best.get('wind', {'speed': 0, 'deg': 0})
        speed = wind.get('speed', 0)
        direction = wind.get('deg', 0)
        
        # More realistic altitude scaling:
        # Speed increases up to 5000m, then gradually decreases in stratosphere
        if alt <= 5000:
            factor = 1 + (alt / 5000) * 1.5   # up to 2.5x at 5000m
        elif alt <= 15000:
            factor = 2.5  # constant high speed in troposphere
        else:
            factor = 2.5 * (1 - (alt - 15000) / 15000)  # decrease to zero at 30000m
        speed = speed * max(0.5, factor)
        return {'speed': speed, 'deg': direction}
