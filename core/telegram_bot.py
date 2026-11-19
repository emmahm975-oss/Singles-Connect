import os
import django
import requests
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'singlesconnect.settings')
django.setup()

from django.conf import settings

# This function is called by the website to send a notification to Telegram
def send_telegram_notification(message):
    bot_token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_ADMIN_CHAT_ID
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Failed to send notification: {e}")

# Tiny web server to keep Render awake (required for the bot to run)
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print(f"Starting health check server on port {port}...")
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()