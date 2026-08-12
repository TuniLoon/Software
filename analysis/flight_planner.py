"""
flight_planner.py
Simulate a balloon flight using forecasted wind data.
"""

import math
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Optional

class FlightPlanner:
    def __init__(self, weather_service):
        self.weather = weather_service
        self.ascent_rate = 5.0      # m/s
        self.descent_rate = 15.0    # m/s
        self.max_altitude = 30000   # m

    def simulate(self, lat: float, lon: float, launch_time: datetime, duration: int = 7200) -> List[Dict]:
        """
        Simulate a flight from launch to landing.
        Args:
            lat, lon: launch coordinates
            launch_time: datetime of launch (UTC)
            duration: flight duration in seconds (default 2h)
        Returns:
            List of dicts: [{'time': seconds, 'lat':, 'lon':, 'alt':}, ...]
        """
        points = []
        dt = 30  # seconds per step
        steps = duration // dt
        time_sec = 0
        alt = 0
        ascent_duration = self.max_altitude / self.ascent_rate
        total_flight = ascent_duration + (self.max_altitude / self.descent_rate)

        # Current position
        cur_lat = lat
        cur_lon = lon

        for step in range(steps):
            t = step * dt
            # Determine altitude
            if t < ascent_duration:
                alt = min(self.ascent_rate * t, self.max_altitude)
            elif t < total_flight:
                desc_time = t - ascent_duration
                alt = max(self.max_altitude - self.descent_rate * desc_time, 0)
            else:
                alt = 0

            # Get wind at this altitude and time
            wind = self._get_wind_at(cur_lat, cur_lon, alt, launch_time + timedelta(seconds=t))
            if wind:
                # Convert wind speed m/s to lat/lon change over dt
                speed = wind.get('speed', 0)
                direction = wind.get('deg', 0)  # degrees clockwise from north
                # Convert to radians
                dir_rad = math.radians(direction)
                dx = speed * dt * math.sin(dir_rad) / (111320 * math.cos(math.radians(cur_lat)))
                dy = speed * dt * math.cos(dir_rad) / 111320
                cur_lat += dy
                cur_lon += dx

            points.append({
                'time': t,
                'latitude': cur_lat,
                'longitude': cur_lon,
                'altitude': round(alt, 0),
                'phase': self._get_phase(alt)
            })

            if alt == 0 and t > 300:  # landed
                break

        return points

    def _get_phase(self, alt: float) -> str:
        if alt < 10: return 'L'
        if alt > 25000: return 'D'
        return 'A'

    def _get_wind_at(self, lat, lon, alt, time_dt):
        """
        Fetch wind from weather service for a specific time and altitude.
        For simplicity, we use forecast data and interpolate vertically.
        """
        # For now, use the current or forecast wind at surface (since OpenWeatherMap doesn't give altitude layers)
        # A more advanced version would use GFS data, but we'll approximate:
        # wind speed increases with altitude up to a point.
        forecast = self.weather.get_forecast(lat, lon, cnt=8)  # 3-hour steps for 24h
        if not forecast:
            return None
        # Find the closest forecast time
        best = None
        for item in forecast.get('list', []):
            ft = datetime.fromtimestamp(item['dt'])
            if abs((ft - time_dt).total_seconds()) < 7200:  # within 2 hours
                best = item
                break
        if not best:
            best = forecast['list'][0]
        wind = best.get('wind', {'speed': 0, 'deg': 0})
        # Scale wind with altitude (very rough model)
        alt_factor = min(1, alt / 5000) * 1.5  # up to 1.5x at 5km
        return {
            'speed': wind.get('speed', 0) * (1 + alt_factor * 0.5),
            'deg': wind.get('deg', 0)
        }

    def predict_landing(self, lat: float, lon: float, launch_time: datetime) -> Dict:
        """Run simulation and return landing prediction."""
        points = self.simulate(lat, lon, launch_time)
        if not points:
            return {'error': 'No trajectory'}
        last = points[-1]
        return {
            'landing_lat': last['latitude'],
            'landing_lon': last['longitude'],
            'landing_time': launch_time + timedelta(seconds=last['time']),
            'duration': last['time'],
            'max_altitude': max(p['altitude'] for p in points),
            'trajectory': points
        }
