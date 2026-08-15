"""
weather_service.py
Fetch weather data from OpenWeatherMap using environment variables.
"""

import os
import requests
import json
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class WeatherService:
    def __init__(self, cache_file="data/weather_cache.json"):
        self.api_key = os.getenv('OPENWEATHER_API_KEY', '')
        if not self.api_key:
            print("[Weather] Warning: OPENWEATHER_API_KEY not set in .env")
        self.cache_file = Path(cache_file)
        self.cache = self._load_cache()
        self.cache_duration = 600  # 10 minutes

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

        # If no API key, return mock data
        if not self.api_key:
            mock = {
                'main': {'temp': 25, 'pressure': 1013, 'humidity': 60},
                'wind': {'speed': 5, 'deg': 180},
                'weather': [{'description': 'Clear sky'}]
            }
            self.cache[cache_key] = {'timestamp': datetime.now().timestamp(), 'data': mock}
            self._save_cache()
            return mock

        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {'lat': lat, 'lon': lon, 'appid': self.api_key, 'units': 'metric'}
        try:
            resp = requests.get(url, params=params, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                self.cache[cache_key] = {'timestamp': datetime.now().timestamp(), 'data': data}
                self._save_cache()
                return data
            else:
                print(f"[Weather] API error: {resp.status_code}")
                return None
        except requests.exceptions.Timeout:
            print("[Weather] Request timed out")
            return None
        except Exception as e:
            print(f"[Weather] Error: {e}")
            return None

    def get_wind(self, lat, lon):
        data = self.get_current_weather(lat, lon)
        if data and 'wind' in data:
            return {'speed': data['wind'].get('speed', 0), 'deg': data['wind'].get('deg', 0)}
        return None

    def get_forecast(self, lat, lon, cnt=8):
        cache_key = f"forecast_{lat:.4f}_{lon:.4f}_{cnt}"
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]['data']

        if not self.api_key:
            # mock forecast
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

        url = "https://api.openweathermap.org/data/2.5/forecast"
        params = {'lat': lat, 'lon': lon, 'appid': self.api_key, 'units': 'metric', 'cnt': cnt}
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
