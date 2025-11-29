import os
import asyncio
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from random import choice

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)

# ---------- LOGGING ----------
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------- CONFIG ----------
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DELETE_DELAY = int(os.getenv("DELETE_DELAY", "300"))
PORT = int(os.getenv("PORT", "10000"))  # Render ka PORT yahi hota hai

PROMO_PATTERNS = [
    "t.me/",
    "telegram.me/",
    "discord.gg/",
    "chat.whatsapp.com/",
    "youtube.com/",
    "youtu.be/",
    "instagram.com/",
    "facebook.com/",
    "bit.ly/",
    "tinyurl.com/",
    "goo.gl/",
]

SAVAGE_COMMENTS = [
    "XP dekhke lagta hai real life me free ho 💀",
    "Bhai typing kam attitude zyada 😂",
    "Tu message nahi spam bhejta hai 😭",
    "Group tere bina bhi khush tha 😏",
    "XP toh strong hai, bas logic weak hai 😭",
    "Tu silently active rehke bhi toxicity faila raha 💀",
]

RANK_TIERS = {
    0:    ["🧹 Dust Mode", "🫠 Background NPC", "👶 Beginner Baby Mode", "😂 Offline Player"],
    11:   ["🎭 Side Character", "👀 Always Online No Typing", "🚶 Human Buffering Mode"],
    51:   ["🎬 Main Character Entry", "⚡ Plot Warming Up", "🗿 Almost Active"],
    151:  ["⚔️ Certified Chaos Maker", "🧨 Trigger Machine", "🐍 Useful Toxic"],
    301:  ["👑 Elite Member", "🎖 OG Contributor", "🛡 Veteran"],
    701:  ["🦅 Boss Level", "💎 Guild Master", "🐉 Big Energy"],
    1500: ["⚡ LEGEND MODE", "💀 Final Boss Energy", "🌋 Group Myth"],
}

# ---------- HTTP KEEPALIVE SERVER (UPTIMEROBOT / RENDER) ----------

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Simple health endpoint
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Telegram auto-delete bot running.\n")

    # Console pe har request ka log spam avoid karne ke liye
    def log_message(self, format, *args):
        return


def run_http_server():
    port = PORT
    with HTTPServer(("", port), HealthHandler) as httpd:
        logger.info(f"HTTP health server running on port {port}")
        httpd.serve_forever()


# ---------- HELPERS ----------

async def delete_after(bot, chat_id: int, msg_id: int, delay: int):
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id, msg_id)
    except Exception:
        pass


async def reply_autodelete(message, context: ContextTypes.DEFAULT_TYPE, text: str):
    delay = context.chat_data.get("delay", DELETE_DELAY)
    sent = await message.reply_text(text)
    asyncio.create_task(delete_after(context.bot, sent.chat.id, sent.message_id, delay))
    return sent


async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    chat = update.effective_chat
    member = await context.bot.get_chat_member(chat.id, user.id)
    return member.status in ("administrator", "creator")


def get_random_rank(xp: int) -> str:
    level = max(k for k in RANK_TIERS.keys() if xp >= k)
    return choice(RANK_TIERS[level])


def get_random_comment() -> str:
    return choice(SAVAGE_COMMENTS)


# ---------- MAIN MESSAGE HANDLER ----------

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user = update.effective_user
    chat_id = msg.chat.id
    text = (msg.text or msg.caption or "").lower()

    # Har message auto-delete (admin + user + bot replies sab)
    delay = context.chat_data.get("delay", DELETE_DELAY)
    asyncio.create_task(delete_after(context.bot, chat_id, msg.message_id, delay))

    # Bot users ke liye: sirf delete, XP/filter/promo ignore
    if user.is_bot:
        return

    # --- PROMO / LINK / @ SPAM ---
    promo_mentions_enabled = context.chat_data.get("promo_mentions", True)
    is_link = any(pat in text for pat in PROMO_PATTERNS)
    is_tag_spam = promo_mentions_enabled and "@" in text

    if is_link or is_tag_spam:
        await reply_autodelete(
            msg,
            context,
            "🚫 Oye free promotion band kar, group koi billboard nahi. 😒",
        )
        asyncio.create_task(delete_after(context.bot, chat_id, msg.message_id, 1))
        return

    # --- KEYWORD FILTERS (word -> reply) ---
    filters_map = context.chat_data.get("filters", {})
    for word, response in filters_map.items():
        if word and word.lower() in text:
            await reply_autodelete(msg, context, response)
            break

    # --- XP SYSTEM ---
    xp_data = context.chat_data.get("xp", {})
    entry = xp_data.get(user.id, {"xp": 0, "name": user.full_name})
    entry["xp"] += 1
    entry["name"] = user.full_name
    xp_data[user.id] = entry
    context.chat_data["xp"] = xp_data


# ---------- COMMANDS ----------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    delay = context.chat_data.get("delay", DELETE_DELAY)
    promo_mentions_enabled = context.chat_data.get("promo_mentions", True)
    await reply_autodelete(
        update.message,
        context,
        f"🤖 Savage Auto-Delete Bot Active\n"
        f"⏳ Auto-delete: {delay}s\n"
        f"📛 Anti @ spam: {'ON' if promo_mentions_enabled else 'OFF'}\n\n"
        "Commands:\n"
        "/delay <sec>\n"
        "/filter word -> reply\n"
        "/filterlist\n"
        "/filterdel <word>\n"
        "/rank\n"
        "/top\n"
        "/promomentions on/off\n"
        "/promostatus",
    )


async def cmd_delay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await reply_autodelete(update.message, context, "❌ Only admins.")

    if not context.args:
        d = context.chat_data.get("delay", DELETE_DELAY)
        return await reply_autodelete(update.message, context, f"Current delay: {d}s")

    try:
        value = int(context.args[0])
        context.chat_data["delay"] = value
        await reply_autodelete(update.message, context, f"✔ Delay updated to {value}s.")
    except ValueError:
        await reply_autodelete(update.message, context, "❌ Invalid format. Example: /delay 30")


async def cmd_filter_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await reply_autodelete(update.message, context, "❌ Only admins.")

    text = update.message.text
    if "->" not in text:
        return await reply_autodelete(update.message, context, "Format:\n/filter hello -> reply text")

    payload = text[len("/filter"):].strip()
    word, reply_text = map(str.strip, payload.split("->", 1))

    filters_map = context.chat_data.get("filters", {})
    filters_map[word.lower()] = reply_text
    context.chat_data["filters"] = filters_map

    await reply_autodelete(update.message, context, f"✔ Filter added: {word}")


async def cmd_filter_del(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await reply_autodelete(update.message, context, "❌ Only admins.")

    if not context.args:
        return await reply_autodelete(update.message, context, "Usage: /filterdel <word>")

    word = context.args[0].lower()
    filters_map = context.chat_data.get("filters", {})

    if word in filters_map:
        del filters_map[word]
        context.chat_data["filters"] = filters_map
        await reply_autodelete(update.message, context, f"❌ Removed filter: {word}")
    else:
        await reply_autodelete(update.message, context, "Filter not found.")


async def cmd_filter_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    filters_map = context.chat_data.get("filters", {})
    if not filters_map:
        return await reply_autodelete(update.message, context, "No filters set.")

    lines = [f"{w} → {r}" for w, r in filters_map.items()]
    await reply_autodelete(update.message, context, "📌 Filters:\n" + "\n".join(lines))


async def cmd_rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    xp_data = context.chat_data.get("xp", {})
    entry = xp_data.get(user.id, {"xp": 0})
    xp = entry["xp"]
    rank = get_random_rank(xp)
    comment = get_random_comment()

    await reply_autodelete(
        update.message,
        context,
        f"👤 {user.full_name}\nXP: {xp}\nRank: {rank}\n\n💬 {comment}",
    )


async def cmd_top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    xp_data = context.chat_data.get("xp", {})
    if not xp_data:
        return await reply_autodelete(update.message, context, "Empty leaderboard.")

    ranked = sorted(xp_data.values(), key=lambda x: x["xp"], reverse=True)[:10]
    lines = [
        f"{i+1}. {u['name']} — {u['xp']} XP"
        for i, u in enumerate(ranked)
    ]
    await reply_autodelete(update.message, context, "🏆 Top Users:\n" + "\n".join(lines))


async def cmd_promomentions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await reply_autodelete(update.message, context, "❌ Only admins.")

    if not context.args or context.args[0].lower() not in ("on", "off"):
        return await reply_autodelete(update.message, context, "Usage: /promomentions on/off")

    state = context.args[0].lower() == "on"
    context.chat_data["promo_mentions"] = state
    await reply_autodelete(update.message, context, f"📛 Promo tag filter: {'ON' if state else 'OFF'}")


async def cmd_promostatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.chat_data.get("promo_mentions", True)
    await reply_autodelete(update.message, context, f"📛 Promo tag filter: {'ON' if state else 'OFF'}")


# ---------- MAIN (NO EVENT-LOOP CONFLICT) ----------

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN env var not set.")

    # HTTP health server ko background thread me start karo
    server_thread = threading.Thread(target=run_http_server, daemon=True)
    server_thread.start()

    # Telegram bot normal sync run_polling se chalega
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("delay", cmd_delay))
    application.add_handler(CommandHandler("filter", cmd_filter_add))
    application.add_handler(CommandHandler("filterdel", cmd_filter_del))
    application.add_handler(CommandHandler("filterlist", cmd_filter_list))
    application.add_handler(CommandHandler("rank", cmd_rank))
    application.add_handler(CommandHandler("top", cmd_top))
    application.add_handler(CommandHandler("promomentions", cmd_promomentions))
    application.add_handler(CommandHandler("promostatus", cmd_promostatus))

    application.add_handler(MessageHandler(filters.ALL, on_message))

    logger.info("Starting Telegram bot polling…")
    application.run_polling()  # yahan koi asyncio.run nahi, isliye event-loop error nahi aayega


if __name__ == "__main__":
    main()
