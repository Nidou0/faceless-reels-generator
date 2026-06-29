"""Telegram notifications for pipeline events — posting success/failure."""
import json
import urllib.request

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


def send(message: str) -> None:
    """Best-effort notify — never lets a notification failure break the pipeline."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    payload = json.dumps({'chat_id': TELEGRAM_CHAT_ID, 'text': message}).encode()
    req = urllib.request.Request(
        url, data=payload, headers={'Content-Type': 'application/json'}, method='POST'
    )
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass
