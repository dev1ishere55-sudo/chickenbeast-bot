"""@chickenbeastbot responder (runs on GitHub Actions, no server/Supabase needed).

Long-polls Telegram getUpdates and replies to /start, /play, /help and the
"How it works" button with a PLAY button that opens the Chickenbeast Mini App.
The bot token comes from the TELEGRAM_BOT_TOKEN Actions secret, never from code.
Runs for RUN_SECONDS, then exits so the next scheduled run takes over.
"""
import html
import json
import os
import sys
import time
import urllib.error
import urllib.request

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
RUN_SECONDS = int(os.environ.get("RUN_SECONDS", str(5 * 3600 + 40 * 60)))
APP_URL = "https://dev1ishere55-sudo.github.io/chickenbeast-site/"

PLAY = {"inline_keyboard": [
    [{"text": "🐔 PLAY CHICKENBEAST", "web_app": {"url": APP_URL}}],
    [{"text": "💪 How it works", "callback_data": "help"}],
]}


def welcome(name: str) -> str:
    return (
        f"🐔💪 <b>Welcome to the gym, {html.escape(name)}!</b>\n\n"
        "<b>Chickenbeast is TOO JACKED TO RUG.</b>\n\n"
        "Tap the beast to earn <b>Beast Points</b>, claim your passive gains, "
        "buy upgrades and climb the leaderboard.\n\n"
        "🔗 Link your Phantom or Solflare wallet to your gym card\n"
        "👥 Join a clan and tip your flock\n"
        "🏆 Ranks from Scrawny Chick → Apex Beast\n\n"
        "Built around <b>$CHICKY</b> on Solana. Tap PLAY 👇"
    )


HELP = (
    "<b>How Chickenbeast works</b>\n\n"
    "1. Tap <b>PLAY</b> to open the gym\n"
    "2. Tap the beast: every tap = Beast Points (BP). 12 fast taps = Frenzy (2× BP)\n"
    "3. Claim incubation: passive BP builds up for up to 8 hours\n"
    "4. Spend BP on Whey, Creatine, Pre-Workout and Mega Flex\n"
    "5. Sign in to save progress, then connect Phantom or Solflare\n\n"
    "Beast Points are in-game points. Connecting a wallet never moves funds."
)


def api(method: str, body: dict, timeout: int = 30) -> dict:
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TOKEN}/{method}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:300]
        print(f"{method} HTTP {e.code}: {detail}", flush=True)
        if e.code == 401:
            raise SystemExit("Bot token rejected (401) - update the TELEGRAM_BOT_TOKEN secret")
        return {"ok": False, "error_code": e.code, "description": detail}


def handle(update: dict) -> None:
    msg = update.get("message")
    if msg and isinstance(msg.get("text"), str) and msg.get("chat", {}).get("id"):
        cmd = msg["text"].strip().split()[0].split("@")[0].lower() if msg["text"].strip() else ""
        chat = msg["chat"]["id"]
        name = (msg.get("from") or {}).get("first_name") or "beast"
        text = HELP if cmd == "/help" else welcome(name)
        r = api("sendMessage", {"chat_id": chat, "text": text, "parse_mode": "HTML", "reply_markup": PLAY})
        print(f"reply {cmd or 'text'} -> ok={r.get('ok')}", flush=True)
    cb = update.get("callback_query")
    if cb and cb.get("id"):
        api("answerCallbackQuery", {"callback_query_id": cb["id"]})
        chat = (cb.get("message") or {}).get("chat", {}).get("id")
        if cb.get("data") == "help" and chat:
            r = api("sendMessage", {"chat_id": chat, "text": HELP, "parse_mode": "HTML", "reply_markup": PLAY})
            print(f"reply help-button -> ok={r.get('ok')}", flush=True)


def main() -> int:
    if not TOKEN:
        print("TELEGRAM_BOT_TOKEN secret is missing", file=sys.stderr)
        return 1
    me = api("getMe", {})
    if not me.get("ok"):
        print(f"getMe failed: {me}", file=sys.stderr)
        return 1
    print(f"bot @{me['result']['username']} polling for {RUN_SECONDS}s", flush=True)
    api("deleteWebhook", {"drop_pending_updates": False})  # polling needs no webhook
    deadline = time.time() + RUN_SECONDS
    offset = None
    handled = 0
    while time.time() < deadline:
        wait = int(max(1, min(50, deadline - time.time())))
        body = {"timeout": wait, "allowed_updates": ["message", "callback_query"]}
        if offset is not None:
            body["offset"] = offset
        try:
            res = api("getUpdates", body, timeout=wait + 15)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            print(f"network error: {e}; retrying", flush=True)
            time.sleep(3)
            continue
        if not res.get("ok"):
            if res.get("error_code") == 409:  # another run still polling
                time.sleep(10)
            else:
                time.sleep(3)
            continue
        for u in res["result"]:
            offset = u["update_id"] + 1
            try:
                handle(u)
                handled += 1
            except Exception as e:  # one bad update must not stop the bot
                print(f"update {u.get('update_id')} failed: {e}", flush=True)
    if offset is not None:
        api("getUpdates", {"offset": offset, "timeout": 0})  # confirm handled updates
    print(f"done, handled {handled} updates", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
