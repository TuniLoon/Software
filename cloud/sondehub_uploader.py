"""
sondehub_uploader.py
Upload telemetry to Sondehub for public tracking.
"""

import json
import time
import threading
from datetime import datetime
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))

try:
    import requests
except ImportError:
    print("[ERROR] requests not installed. Run: pip install requests")
    sys.exit(1)

class SondehubUploader:
    """Upload telemetry to Sondehub."""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or "config/cloud_config.json"
        self.load_config()
        
        self.enabled = self.sondehub_config.get('enabled', False)
        self.callsign = self.sondehub_config.get('callsign', 'TUNILOON')
        self.upload_url = self.sondehub_config.get('upload_url', 'https://api.sondehub.org/v1/telemetry')
        
        self.last_upload_time = 0
        self.upload_interval = 5  # seconds between uploads
    
    def load_config(self):
        """Load Sondehub configuration."""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                self.sondehub_config = config.get('sondehub', {})
                print(f"[INFO] Sondehub config loaded from {self.config_path}")
        except Exception as e:
            print(f"[ERROR] Failed to load config: {e}")
            self.sondehub_config = {'enabled': False}
    
    def upload(self, data: dict) -> bool:
        """
        Upload telemetry to Sondehub.
        
        Args:
            data: Telemetry data dict
        
        Returns:
            True if uploaded successfully
        """
        if not self.enabled:
            return False
        
        # Rate limit
        now = time.time()
        if now - self.last_upload_time < self.upload_interval:
            return False
        
        self.last_upload_time = now
        
        try:
            # Format data for Sondehub
            payload = {
                'callsign': self.callsign,
                'time': datetime.now().isoformat(),
                'lat': data.get('latitude', 0),
                'lon': data.get('longitude', 0),
                'alt': data.get('altitude', 0),
                'temp': data.get('temperature', 0),
                'pressure': data.get('pressure', 0),
                'humidity': data.get('humidity', 0),
                'status': data.get('status', '')
            }
            
            # Add optional fields if available
            if 'speed' in data:
                payload['speed'] = data['speed']
            if 'heading' in data:
                payload['heading'] = data['heading']
            
            response = requests.post(
                self.upload_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"[Sondehub] Upload successful: {data.get('altitude', 0):.0f}m")
                return True
            else:
                print(f"[Sondehub] Error: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"[Sondehub] Upload error: {e}")
            return False
    
    def upload_loop(self, data_generator, interval: int = 5):
        """
        Continuously upload data from a generator.
        
        Args:
            data_generator: Function that yields telemetry data
            interval: Upload interval in seconds
        """
        self.upload_interval = interval
        
        print(f"[Sondehub] Starting upload loop (interval: {interval}s)")
        print(f"[Sondehub] Callsign: {self.callsign}")
        print(f"[Sondehub] Enabled: {self.enabled}")
        
        try:
            while True:
                data = data_generator()
                if data:
                    self.upload(data)
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[Sondehub] Stopped by user")


# Standalone test
if __name__ == "__main__":
    print("=" * 60)
    print("  TuniLoon Sondehub Uploader Test")
    print("=" * 60)
    print()
    
    uploader = SondehubUploader()
    
    if not uploader.enabled:
        print("[WARN] Sondehub is disabled. Edit config/cloud_config.json to enable.")
        print("[WARN] Set 'enabled': true and configure your callsign")
        sys.exit(0)
    
    # Test with sample data
    test_data = {
        'latitude': 36.8442,
        'longitude': 10.1213,
        'altitude': 15234,
        'temperature': 22.5,
        'pressure': 1012.4,
        'humidity': 45.2,
        'status': 'A'
    }
    
    print("[INFO] Uploading test data...")
    uploader.upload(test_data)
    print("[INFO] Test complete. Check Sondehub!")
