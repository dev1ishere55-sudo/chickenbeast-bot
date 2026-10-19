"""@chickenbeastbot responder (runs on GitHub Actions).

Long-polls Telegram getUpdates and replies to /start, /play, /help, /contest.
The bot token comes from the TELEGRAM_BOT_TOKEN Actions secret, never from code.
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
APP_URL = "https://beastly-point-tap-v2-kyariball2910-8168s-projects.vercel.app/"

PLAY = {"inline_keyboard": [
    [{"text": "🐓 PLAY CHICKENBEAST", "web_app": {"url": APP_URL}}],
    [{"text": "💪 How it works", "callback_data": "help"}],
    [{"text": "🏆 Meme Contest", "callback_data": "contest"}],
]}

CONTEST = (
    "<b>🐓 CHICKENBEAST MEME CONTEST</b>\n\n"
    "Creativity builds the community. The community builds the BEAST!\n\n"
    "<b>$60 donated prize pool</b> (awarded in SOL)\n"
    "1st $20 · 2nd $15 · 3rd $10 · 4th–8th $5 to $1\n\n"
    "📅 Oct 19–24, 2026 — Submissions open\n"
    "🏆 Sunday Oct 25 — Winners selected\n\n"
    "Post in the <b>MEME CONTEST</b> topic. Max 5 entries/day. Label your category.\n\n"
    "Categories: Best Animation, Best Halloween, Best Comedy, Best Artistic/Marketable.\n"
    "Quality over quantity. Five great memes beat fifty forgettable ones.\n\n"
    "t.me/ChickenBeast"
)


def welcome(name: str) -> str:
    return (
        f"🐓💪 <b>Welcome to the gym, {html.escape(name)}!</b>\n\n"
        "<b>Chickenbeast is TOO JACKED TO RUG.</b>\n\n"
        "Tap the beast to earn <b>Beast Points</b>, claim your passive gains, "
        "buy upgrades and climb the leaderboard.\n\n"
        "🔗 Link your Phantom or Solflare wallet to your gym card\n"
        "👥 Join a clan and tip your flock\n"
        "🏆 Ranks from Scrawny Chick → Apex Beast\n\n"
        "Built around <b>$CBEAST</b> on Solana. Tap PLAY 👇"
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


def setup_bot() -> None:
    api("setMyCommands", {"commands": [
        {"command": "start", "description": "Open the gym"},
        {"command": "play", "description": "Play Chickenbeast"},
        {"command": "help", "description": "How it works"},
        {"command": "contest", "description": "Meme contest rules"},
    ]})
    api("setChatMenuButton", {"menu_button": {"type": "web_app", "text": "PLAY", "web_app": {"url": APP_URL}}})


def play_markup(ref: str = "") -> dict:
    url = APP_URL + (f"?ref={ref}" if ref else "")
    return {"inline_keyboard": [
        [{"text": "🐓 PLAY CHICKENBEAST", "web_app": {"url": url}}],
        [{"text": "💪 How it works", "callback_data": "help"}],
        [{"text": "🏆 Meme Contest", "callback_data": "contest"}],
    ]}


def handle(update: dict) -> None:
    msg = update.get("message")
    if msg and isinstance(msg.get("text"), str) and msg.get("chat", {}).get("id"):
        cmd = msg["text"].strip().split()[0].split("@")[0].lower() if msg["text"].strip() else ""
        chat = msg["chat"]["id"]
        name = (msg.get("from") or {}).get("first_name") or "beast"
        if cmd == "/contest":
            text = CONTEST
        elif cmd == "/help":
            text = HELP
        else:
            text = welcome(name)
        parts = msg["text"].strip().split()
        ref = ""
        if cmd == "/start" and len(parts) > 1 and parts[1].startswith("ref_"):
            ref = "".join(c for c in parts[1][4:] if c.isalnum())[:16]
            print(f"referral start ref={ref}", flush=True)
        r = api("sendMessage", {"chat_id": chat, "text": text, "parse_mode": "HTML", "reply_markup": play_markup(ref)})
        print(f"reply {cmd or 'text'} -> ok={r.get('ok')}", flush=True)
    cb = update.get("callback_query")
    if cb and cb.get("id"):
        api("answerCallbackQuery", {"callback_query_id": cb["id"]})
        chat = (cb.get("message") or {}).get("chat", {}).get("id")
        data = cb.get("data")
        if data == "help" and chat:
            r = api("sendMessage", {"chat_id": chat, "text": HELP, "parse_mode": "HTML", "reply_markup": PLAY})
            print(f"reply help-button -> ok={r.get('ok')}", flush=True)
        elif data == "contest" and chat:
            r = api("sendMessage", {"chat_id": chat, "text": CONTEST, "parse_mode": "HTML", "reply_markup": PLAY})
            print(f"reply contest-button -> ok={r.get('ok')}", flush=True)


def main() -> int:
    if not TOKEN:
        print("::error::TELEGRAM_BOT_TOKEN secret is missing - add it in Settings > Secrets and variables > Actions", file=sys.stderr)
        return 1
    me = api("getMe", {})
    if not me.get("ok"):
        print(f"::error::getMe failed (bad token or Telegram unreachable): {me}", file=sys.stderr)
        return 1
    print(f"bot @{me['result']['username']} polling for {RUN_SECONDS}s", flush=True)
    info = api("getWebhookInfo", {}).get("result", {})
    if info.get("url"):
        print(f"WARNING: webhook was set to {info['url']}; removing it so polling works", flush=True)
    api("deleteWebhook", {"drop_pending_updates": False})
    setup_bot()
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
            if res.get("error_code") == 409:
                time.sleep(10)
            else:
                time.sleep(3)
            continue
        for u in res["result"]:
            offset = u["update_id"] + 1
            try:
                handle(u)
                handled += 1
            except Exception as e:
                print(f"update {u.get('update_id')} failed: {e}", flush=True)
    if offset is not None:
        api("getUpdates", {"offset": offset, "timeout": 0})
    print(f"done, handled {handled} updates", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
