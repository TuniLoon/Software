"""
telegram_bot.py
Send alerts to Telegram.
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

class TelegramBot:
    """Send alerts via Telegram bot."""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or "config/cloud_config.json"
        self.load_config()
        
        self.enabled = self.telegram_config.get('enabled', False)
        self.bot_token = self.telegram_config.get('bot_token', '')
        self.chat_id = self.telegram_config.get('chat_id', '')
        
        self.last_alert_time = {}
        self.alert_cooldown = 60  # seconds between same alerts
    
    def load_config(self):
        """Load Telegram configuration."""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                self.telegram_config = config.get('telegram', {})
                print(f"[INFO] Telegram config loaded from {self.config_path}")
        except Exception as e:
            print(f"[ERROR] Failed to load config: {e}")
            self.telegram_config = {'enabled': False}
    
    def send_message(self, message: str) -> bool:
        """
        Send a message via Telegram.
        
        Args:
            message: Message text
        
        Returns:
            True if sent successfully
        """
        if not self.enabled:
            return False
        
        if not self.bot_token or not self.chat_id:
            print("[Telegram] Missing bot_token or chat_id")
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                print(f"[Telegram] Message sent: {message[:50]}...")
                return True
            else:
                print(f"[Telegram] Error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"[Telegram] Send error: {e}")
            return False
    
    def send_alert(self, alert_type: str, data: dict) -> bool:
        """
        Send an alert based on type.
        
        Args:
            alert_type: Type of alert (landing, max_altitude, status_change, error)
            data: Telemetry data
        
        Returns:
            True if sent successfully
        """
        if not self.enabled:
            return False
        
        # Check cooldown
        now = time.time()
        if alert_type in self.last_alert_time:
            if now - self.last_alert_time[alert_type] < self.alert_cooldown:
                return False
        
        self.last_alert_time[alert_type] = now
        
        # Format message based on alert type
        if alert_type == 'landing':
            message = (
                f"🛬 <b>TuniLoon Has Landed!</b>\n\n"
                f"📍 Location: {data.get('latitude', 0):.6f}, {data.get('longitude', 0):.6f}\n"
                f"📏 Altitude: {data.get('altitude', 0):.0f}m\n"
                f"🌡️ Temperature: {data.get('temperature', 0):.1f}°C\n"
                f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
        elif alert_type == 'max_altitude':
            message = (
                f"🎈 <b>TuniLoon at Peak Altitude!</b>\n\n"
                f"📏 Altitude: {data.get('altitude', 0):.0f}m\n"
                f"📍 Location: {data.get('latitude', 0):.6f}, {data.get('longitude', 0):.6f}\n"
                f"🌡️ Temperature: {data.get('temperature', 0):.1f}°C\n"
                f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
        elif alert_type == 'status_change':
            status_map = {'A': 'Ascent', 'D': 'Descent', 'L': 'Landing', 'E': 'Error', 'F': 'Cut-down'}
            status_text = status_map.get(data.get('status'), data.get('status', 'Unknown'))
            message = (
                f"🔄 <b>Status Changed</b>\n\n"
                f"📊 New Status: {status_text}\n"
                f"📏 Altitude: {data.get('altitude', 0):.0f}m\n"
                f"📍 Location: {data.get('latitude', 0):.6f}, {data.get('longitude', 0):.6f}"
            )
        else:
            message = (
                f"📡 <b>TuniLoon Telemetry</b>\n\n"
                f"📏 Altitude: {data.get('altitude', 0):.0f}m\n"
                f"📍 Location: {data.get('latitude', 0):.6f}, {data.get('longitude', 0):.6f}\n"
                f"🌡️ Temperature: {data.get('temperature', 0):.1f}°C\n"
                f"📊 Status: {data.get('status', 'Unknown')}"
            )
        
        return self.send_message(message)
    
    def send_landing_alert(self, data: dict) -> bool:
        """Send landing alert."""
        return self.send_alert('landing', data)
    
    def send_max_altitude_alert(self, data: dict) -> bool:
        """Send max altitude alert."""
        return self.send_alert('max_altitude', data)
    
    def send_status_change_alert(self, data: dict) -> bool:
        """Send status change alert."""
        return self.send_alert('status_change', data)
    
    def send_error_alert(self, error_message: str) -> bool:
        """Send error alert."""
        return self.send_message(f"⚠️ <b>TuniLoon Error</b>\n\n{error_message}")


# Standalone test
if __name__ == "__main__":
    print("=" * 60)
    print("  TuniLoon Telegram Bot Test")
    print("=" * 60)
    print()
    
    bot = TelegramBot()
    
    if not bot.enabled:
        print("[WARN] Telegram is disabled. Edit config/cloud_config.json to enable.")
        print("[WARN] Set 'enabled': true and add your bot_token and chat_id")
        sys.exit(0)
    
    # Send a test message
    test_data = {
        'altitude': 15234,
        'latitude': 36.8442,
        'longitude': 10.1213,
        'temperature': 22.5,
        'status': 'A'
    }
    
    print("[INFO] Sending test messages...")
    bot.send_landing_alert(test_data)
    time.sleep(1)
    bot.send_max_altitude_alert(test_data)
    
    print("[INFO] Test complete. Check your Telegram!")
