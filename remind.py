"""Simple scheduled reminders for Chicken Beast.

Run via GitHub Action (cron). Sends a daily streak nudge and Pump warning
to a configured chat or channel. Token from TELEGRAM_BOT_TOKEN secret.
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.environ.get("NOTIFY_CHAT_ID", "").strip()  # group or channel id
APP_URL = "https://beastly-point-tap.vercel.app/"

def send(text: str) -> None:
    if not TOKEN or not CHAT_ID:
        print("missing TOKEN or NOTIFY_CHAT_ID")
        return
    body = json.dumps({
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": {"inline_keyboard": [[{"text": "🐓 PLAY", "web_app": {"url": APP_URL}}]]}
    }).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        print(json.load(r).get("ok"))

def main() -> int:
    if not TOKEN or not CHAT_ID:
        print("Set TELEGRAM_BOT_TOKEN and NOTIFY_CHAT_ID")
        return 1
    now = datetime.now(timezone.utc)
    hour = now.hour
    # Daily streak reminder around 12:00 UTC
    if hour == 12:
        send("🔥 <b>Daily Streak reminder</b>\n\nClaim your reward today to keep the chain going.\nOpen the app → Home → Claim Daily Reward.")
    # Pump warning 10 min before 18:00 UTC window
    if hour == 17 and now.minute >= 50:
        send("⚡ <b>Global Pump in ~10 min</b>\n\nEnergy goes infinite and taps earn 5×.\nGet ready.")
    print("remind check done")
    return 0

if __name__ == "__main__":
    sys.exit(main())
