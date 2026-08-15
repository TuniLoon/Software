"""
weather_service.py
Fetch weather data using config.
"""

import requests
import json
from datetime import datetime, timedelta
from pathlib import Path
from ground_station.src.config import config

class WeatherService:
    def __init__(self):
        self.api_key = config.OPENWEATHER_API_KEY
        self.cache_file = config.DATA_DIR / "weather_cache.json"
        self.cache = self._load_cache()
        self.cache_duration = config.WEATHER_CACHE_DURATION

    def _load_cache(self):
        if self.cache_file.exists():
            try:
                with open(self.cache_file) as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_cache(self):
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f, indent=2)

    def _is_cache_valid(self, key):
        if key not in self.cache:
            return False
        timestamp = self.cache[key].get('timestamp', 0)
        return (datetime.now().timestamp() - timestamp) < self.cache_duration

    def get_current_weather(self, lat, lon):
        cache_key = f"current_{lat:.4f}_{lon:.4f}"
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]['data']

        if not self.api_key:
            # mock data
            mock = {
                'main': {'temp': 25, 'pressure': 1013, 'humidity': 60},
                'wind': {'speed': 5, 'deg': 180},
                'weather': [{'description': 'Clear sky'}]
            }
            self.cache[cache_key] = {'timestamp': datetime.now().timestamp(), 'data': mock}
            self._save_cache()
            return mock

        url = config.OPENWEATHER_URL
        params = {'lat': lat, 'lon': lon, 'appid': self.api_key, 'units': config.OPENWEATHER_UNITS}
        try:
            resp = requests.get(url, params=params, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                self.cache[cache_key] = {'timestamp': datetime.now().timestamp(), 'data': data}
                self._save_cache()
                return data
            else:
                return None
        except:
            return None

    def get_forecast(self, lat, lon, cnt=8):
        cache_key = f"forecast_{lat:.4f}_{lon:.4f}_{cnt}"
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]['data']
        if not self.api_key:
            from datetime import timedelta
            mock = {
                'list': [
                    {
                        'dt': int((datetime.now() + timedelta(hours=i*3)).timestamp()),
                        'wind': {'speed': 5 + i*0.5, 'deg': 180 + i*10}
                    }
                    for i in range(cnt)
                ]
            }
            self.cache[cache_key] = {'timestamp': datetime.now().timestamp(), 'data': mock}
            self._save_cache()
            return mock
        url = config.OPENWEATHER_FORECAST_URL
        params = {'lat': lat, 'lon': lon, 'appid': self.api_key, 'units': config.OPENWEATHER_UNITS, 'cnt': cnt}
        try:
            resp = requests.get(url, params=params, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                self.cache[cache_key] = {'timestamp': datetime.now().timestamp(), 'data': data}
                self._save_cache()
                return data
        except:
            return None
        return None

    def get_wind(self, lat, lon):
        data = self.get_current_weather(lat, lon)
        if data and 'wind' in data:
            return {'speed': data['wind'].get('speed', 0), 'deg': data['wind'].get('deg', 0)}
        return None
