import os
from dotenv import load_dotenv
import requests

load_dotenv()

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

print(f"Token: {TOKEN[:5]}... (first 5 chars)")  # Don't print full token
print(f"Chat ID: {CHAT_ID}")
print(f"Token length: {len(TOKEN) if TOKEN else 0}")

if not TOKEN or not CHAT_ID:
    print("❌ Token or Chat ID missing in .env")
    exit(1)

# Test getMe
url = f"https://api.telegram.org/bot{TOKEN}/getMe"
resp = requests.get(url)
print(f"getMe status: {resp.status_code}")
print(f"getMe response: {resp.text}")

# Test sendMessage (if getMe works)
if resp.status_code == 200:
    url2 = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': 'Test from TuniLoon'}
    resp2 = requests.post(url2, json=payload)
    print(f"sendMessage status: {resp2.status_code}")
    print(f"sendMessage response: {resp2.text}")
