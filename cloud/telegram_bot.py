import os
import time
import requests
from ground_station.src.config import config

class TelegramBot:
    def __init__(self):
        self.bot_token = config.TELEGRAM_BOT_TOKEN
        self.chat_id = config.TELEGRAM_CHAT_ID
        self.enabled = config.TELEGRAM_ENABLED
        self.last_alert_time = {}
        self.alert_cooldown = config.TELEGRAM_ALERT_COOLDOWN
        if not self.enabled:
            print("[Telegram] Warning: Bot token or chat ID not set. Alerts disabled.")

    def send_message(self, message):
        if not self.enabled:
            return False
        if not self.bot_token:
            return False
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {'chat_id': self.chat_id, 'text': message, 'parse_mode': 'HTML'}
            resp = requests.post(url, json=payload, timeout=10)
            if resp.status_code == 200:
                print("[Telegram] Message sent")
                return True
            else:
                print(f"[Telegram] Error: {resp.status_code} - {resp.text}")
                return False
        except Exception as e:
            print(f"[Telegram] Send error: {e}")
            return False

    def _can_send(self, alert_type, cooldown=None):
        now = time.time()
        cooldown = cooldown or self.alert_cooldown
        if alert_type in self.last_alert_time:
            if now - self.last_alert_time[alert_type] < cooldown:
                return False
        self.last_alert_time[alert_type] = now
        return True

    def check_and_alert(self, data):
        pass

    def reset_state(self):
        self.last_alert_time = {}
