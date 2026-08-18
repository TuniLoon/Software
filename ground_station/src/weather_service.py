"""
weather_service.py
Fetch weather data from OpenWeatherMap (primary) with fallback to Open-Meteo.
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

    def _fetch_openmeteo(self, lat, lon):
        """Fetch current weather from Open-Meteo (free, no API key)."""
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            'latitude': lat,
            'longitude': lon,
            'current_weather': 'true',
            'temperature_unit': 'celsius',
            'wind_speed_unit': 'ms',
            'timezone': 'auto'
        }
        try:
            resp = requests.get(url, params=params, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                current = data.get('current_weather', {})
                return {
                    'main': {
                        'temp': current.get('temperature', 25),
                        'pressure': 1013,  # Not provided, use default
                        'humidity': 60     # Not provided, use default
                    },
                    'wind': {
                        'speed': current.get('windspeed', 0),
                        'deg': current.get('winddirection', 0)
                    },
                    'weather': [{
                        'description': current.get('weathercode', 0)  # code, we'll map later
                    }]
                }
            else:
                return None
        except:
            return None

    def _fetch_openmeteo_forecast(self, lat, lon, cnt=8):
        """Fetch 24‑hour forecast from Open-Meteo."""
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            'latitude': lat,
            'longitude': lon,
            'hourly': 'temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m',
            'forecast_days': 1,
            'timezone': 'auto'
        }
        try:
            resp = requests.get(url, params=params, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                hourly = data.get('hourly', {})
                times = hourly.get('time', [])[:cnt]
                temps = hourly.get('temperature_2m', [])[:cnt]
                winds = hourly.get('wind_speed_10m', [])[:cnt]
                wind_dir = hourly.get('wind_direction_10m', [])[:cnt]
                hum = hourly.get('relative_humidity_2m', [])[:cnt]
                # Build list of 3‑hour steps
                result = {'list': []}
                for i in range(0, min(len(times), cnt), 3):
                    if i >= len(times):
                        break
                    dt = times[i]
                    try:
                        ts = int(datetime.fromisoformat(dt).timestamp())
                    except:
                        ts = int(datetime.now().timestamp()) + i*3600
                    result['list'].append({
                        'dt': ts,
                        'wind': {
                            'speed': winds[i] if i < len(winds) else 5,
                            'deg': wind_dir[i] if i < len(wind_dir) else 180
                        },
                        'main': {
                            'temp': temps[i] if i < len(temps) else 25,
                            'humidity': hum[i] if i < len(hum) else 60,
                            'pressure': 1013
                        }
                    })
                return result
            else:
                return None
        except:
            return None

    def get_current_weather(self, lat, lon):
        cache_key = f"current_{lat:.4f}_{lon:.4f}"
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]['data']

        # Try OpenWeatherMap
        if self.api_key:
            url = config.OPENWEATHER_URL
            params = {'lat': lat, 'lon': lon, 'appid': self.api_key, 'units': config.OPENWEATHER_UNITS}
            try:
                resp = requests.get(url, params=params, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    self.cache[cache_key] = {'timestamp': datetime.now().timestamp(), 'data': data}
                    self._save_cache()
                    return data
            except:
                pass

        # Fallback to Open-Meteo
        data = self._fetch_openmeteo(lat, lon)
        if data:
            self.cache[cache_key] = {'timestamp': datetime.now().timestamp(), 'data': data}
            self._save_cache()
            return data

        # Ultimate fallback: mock data
        mock = {
            'main': {'temp': 25, 'pressure': 1013, 'humidity': 60},
            'wind': {'speed': 5, 'deg': 180},
            'weather': [{'description': 'Clear sky'}]
        }
        self.cache[cache_key] = {'timestamp': datetime.now().timestamp(), 'data': mock}
        self._save_cache()
        return mock

    def get_forecast(self, lat, lon, cnt=8):
        cache_key = f"forecast_{lat:.4f}_{lon:.4f}_{cnt}"
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]['data']

        # Try OpenWeatherMap
        if self.api_key:
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
                pass

        # Fallback to Open-Meteo
        data = self._fetch_openmeteo_forecast(lat, lon, cnt)
        if data:
            self.cache[cache_key] = {'timestamp': datetime.now().timestamp(), 'data': data}
            self._save_cache()
            return data

        # Ultimate fallback: mock forecast
        mock = {
            'list': [
                {
                    'dt': int((datetime.now() + timedelta(hours=i*3)).timestamp()),
                    'wind': {'speed': 5 + i*0.5, 'deg': 180 + i*10},
                    'main': {'temp': 25 - i*0.5, 'humidity': 60 - i*2, 'pressure': 1013}
                }
                for i in range(cnt)
            ]
        }
        self.cache[cache_key] = {'timestamp': datetime.now().timestamp(), 'data': mock}
        self._save_cache()
        return mock

    def get_wind(self, lat, lon):
        data = self.get_current_weather(lat, lon)
        if data and 'wind' in data:
            return {'speed': data['wind'].get('speed', 0), 'deg': data['wind'].get('deg', 0)}
        return None
