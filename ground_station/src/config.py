"""
config.py
Central configuration loaded from environment variables.
All settings can be overridden via .env file or system environment.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file (if present)
load_dotenv()

class Config:
    # ------------------------- Project -------------------------
    PROJECT_NAME = os.getenv('PROJECT_NAME', 'TuniLoon')
    PROJECT_VERSION = os.getenv('PROJECT_VERSION', '1.0.0')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

    # ------------------------- Paths -------------------------
    BASE_DIR = Path(__file__).parent.parent.parent
    DATA_DIR = Path(os.getenv('DATA_DIR', BASE_DIR / 'data'))
    LOG_DIR = Path(os.getenv('LOG_DIR', BASE_DIR / 'logs'))
    MODELS_DIR = Path(os.getenv('MODELS_DIR', BASE_DIR / 'ml/models'))
    CONFIG_DIR = Path(os.getenv('CONFIG_DIR', BASE_DIR / 'config'))
    STATIC_DIR = Path(os.getenv('STATIC_DIR', BASE_DIR / 'ground_station/web/static'))
    TEMPLATE_DIR = Path(os.getenv('TEMPLATE_DIR', BASE_DIR / 'ground_station/web/templates'))

    # Ensure directories exist
    for d in [DATA_DIR, LOG_DIR, MODELS_DIR, CONFIG_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    # ------------------------- Database -------------------------
    DB_PATH = DATA_DIR / os.getenv('DB_FILENAME', 'telemetry.db')
    DB_CONNECTION_TIMEOUT = int(os.getenv('DB_CONNECTION_TIMEOUT', '10'))

    # ------------------------- Logging -------------------------
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
    LOG_FILE = LOG_DIR / os.getenv('LOG_FILENAME', 'tuniloon.log')
    LOG_MAX_BYTES = int(os.getenv('LOG_MAX_BYTES', '10485760'))  # 10 MB
    LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', '5'))

    # ------------------------- Weather (OpenWeatherMap) -------------------------
    OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY', '')
    OPENWEATHER_URL = os.getenv('OPENWEATHER_URL', 'https://api.openweathermap.org/data/2.5/weather')
    OPENWEATHER_FORECAST_URL = os.getenv('OPENWEATHER_FORECAST_URL', 'https://api.openweathermap.org/data/2.5/forecast')
    OPENWEATHER_UNITS = os.getenv('OPENWEATHER_UNITS', 'metric')
    WEATHER_CACHE_DURATION = int(os.getenv('WEATHER_CACHE_DURATION', '600'))  # seconds

    # ------------------------- MQTT -------------------------
    MQTT_BROKER = os.getenv('MQTT_BROKER', 'broker.hivemq.com')
    MQTT_PORT = int(os.getenv('MQTT_PORT', '8883'))
    MQTT_USERNAME = os.getenv('MQTT_USERNAME', '')
    MQTT_PASSWORD = os.getenv('MQTT_PASSWORD', '')
    MQTT_TOPIC = os.getenv('MQTT_TOPIC', 'tuniloon/telemetry')
    MQTT_CLIENT_ID = os.getenv('MQTT_CLIENT_ID', f'tuniloon_{os.getpid()}')
    MQTT_TLS = os.getenv('MQTT_TLS', 'True').lower() == 'true'

    # ------------------------- Telegram -------------------------
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
    TELEGRAM_ENABLED = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
    TELEGRAM_ALERT_COOLDOWN = int(os.getenv('TELEGRAM_ALERT_COOLDOWN', '60'))  # seconds

    # ------------------------- Sondehub -------------------------
    SONDEHUB_ENABLED = os.getenv('SONDEHUB_ENABLED', 'False').lower() == 'true'
    SONDEHUB_CALLSIGN = os.getenv('SONDEHUB_CALLSIGN', 'TUNILOON')
    SONDEHUB_URL = os.getenv('SONDEHUB_URL', 'https://api.sondehub.org/v1/telemetry')

    # ------------------------- Simulation -------------------------
    SIMULATION_INTERVAL = int(os.getenv('SIMULATION_INTERVAL', '1'))  # seconds between packets
    REAL_TIME_MODE = os.getenv('REAL_TIME_MODE', 'False').lower() == 'true'
    MAX_ALTITUDE = int(os.getenv('MAX_ALTITUDE', '30000'))
    ASCENT_RATE = float(os.getenv('ASCENT_RATE', '5.0'))
    DESCENT_RATE = float(os.getenv('DESCENT_RATE', '15.0'))

    # ------------------------- ML Anomaly Detection -------------------------
    ANOMALY_CONFIDENCE_THRESHOLD = float(os.getenv('ANOMALY_CONFIDENCE_THRESHOLD', '0.7'))
    ANOMALY_CONTAMINATION = float(os.getenv('ANOMALY_CONTAMINATION', '0.02'))
    ANOMALY_MODEL_PATH = MODELS_DIR / os.getenv('ANOMALY_MODEL_FILENAME', 'anomaly_model.pkl')
    FEATURE_WINDOW_SIZE = int(os.getenv('FEATURE_WINDOW_SIZE', '10'))

    # ------------------------- Flask -------------------------
    FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    FLASK_PORT = int(os.getenv('FLASK_PORT', '5000'))
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

    # ------------------------- Rate Limiting -------------------------
    RATE_LIMIT_DEFAULT = os.getenv('RATE_LIMIT_DEFAULT', '200 per day, 50 per hour')
    RATE_LIMIT_STRICT = os.getenv('RATE_LIMIT_STRICT', '5 per minute')

    @classmethod
    def to_dict(cls):
        """Return all settings as a dictionary (for debugging)."""
        return {k: getattr(cls, k) for k in dir(cls) if not k.startswith('_') and not callable(getattr(cls, k))}


# Create a singleton instance for convenience
config = Config()
