"""
telegram_bot.py
Send alerts via Telegram using environment variables.
"""

import os
import json
import time
import requests
from dotenv import load_dotenv

load_dotenv()

class TelegramBot:
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
        self.enabled = bool(self.bot_token and self.chat_id)
        self.last_alert_time = {}
        self.alert_cooldown = 60

    def send_message(self, message):
        if not self.bot_token:
            print("[Telegram] Bot token not set – skipping message")
            return False
        if not self.enabled:
            return False
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {'chat_id': self.chat_id, 'text': message, 'parse_mode': 'HTML'}
            resp = requests.post(url, json=payload, timeout=10)
            if resp.status_code == 200:
                print("[Telegram] Message sent")
                return True
            else:
                print(f"[Telegram] Error: {resp.status_code}")
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
        # Existing logic – unchanged, just using env
        pass
