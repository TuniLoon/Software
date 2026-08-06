"""
Config.py
Configuration loader for ground station.
"""

import json
import os
from pathlib import Path

class Config:
    """Configuration manager for ground station."""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or "config/settings.json"
        self.data = {}
        self.load()
    
    def load(self):
        """Load configuration from file."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    self.data = json.load(f)
                print(f"[INFO] Config loaded from {self.config_path}")
            else:
                print(f"[WARN] Config file not found, using defaults")
                self.data = self.get_defaults()
        except json.JSONDecodeError:
            print(f"[ERROR] Invalid JSON in config file, using defaults")
            self.data = self.get_defaults()
    
    def get_defaults(self):
        """Return default configuration."""
        return {
            'communication': {
                'virtual_com_port': 'COM10',
                'baud_rate': 115200,
                'packet_timeout': 60
            },
            'logging': {
                'data_dir': 'data/',
                'csv_filename': 'flight_data.csv',
                'log_interval': 1
            },
            'ground_station': {
                'web_port': 5000,
                'update_interval': 1
            },
            'cloud': {
                'mqtt_broker': 'broker.hivemq.com',
                'mqtt_port': 1883,
                'topic': 'tuniloon/telemetry'
            }
        }
    
    def get(self, key: str, default=None):
        """Get a configuration value using dot notation."""
        keys = key.split('.')
        value = self.data
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def set(self, key: str, value):
        """Set a configuration value using dot notation."""
        keys = key.split('.')
        target = self.data
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value
        self.save()
    
    def save(self):
        """Save configuration to file."""
        with open(self.config_path, 'w') as f:
            json.dump(self.data, f, indent=4)
        print(f"[INFO] Config saved to {self.config_path}")
    
    def get_com_port(self):
        """Get the configured COM port."""
        return self.get('communication.virtual_com_port', 'COM10')
    
    def get_baud_rate(self):
        """Get the configured baud rate."""
        return self.get('communication.baud_rate', 115200)
    
    def get_data_dir(self):
        """Get the data directory path."""
        dir_path = self.get('logging.data_dir', 'data/')
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        return dir_path


if __name__ == "__main__":
    # Test the config
    config = Config()
    print(f"[INFO] COM Port: {config.get_com_port()}")
    print(f"[INFO] Baud Rate: {config.get_baud_rate()}")
    print(f"[INFO] Data Directory: {config.get_data_dir()}")
    print(f"[INFO] Full config: {json.dumps(config.data, indent=2)}")
