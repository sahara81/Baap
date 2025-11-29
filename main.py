import os
import asyncio
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from random import choice

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
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
PORT = int(os.getenv("PORT", "10000"))  # Render sets PORT

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

# NSFW patterns (extended)
NSFW_PATTERNS = [
    # core english
    "porn", "pornhub", "xvideos", "xnxx", "xhamster", "redtube", "youporn", "brazzers", "bangbros",
    "hentai", "rule34", "xxx", "nsfw", "nude", "nudes", "nudity", "boobs", "tits",
    "pussy", "cock", "dick", "dildo", "vibrator", "cum", "cumshot", "creampie", "squirt",
    "squirting", "fuck", "fucking", "fucker", "asshole", "anal", "bj", "blowjob", "handjob",
    "deepthroat", "fingering", "69", "threesome", "orgy", "fetish", "pegging", "bdsm", "bondage",
    "camsex", "camgirl", "camsoda", "chaturbate", "onlyfans", "fansly", "escort", "callgirl",
    "sex", "sexchat", "sext", "sexting", "hotsex", "leakednudes", "leakednude", "sextape",
    "milf", "teenporn", "stepmom", "stepsis",

    # bypass / stylized
    "s3x", "pr0n", "p0rn", "n00ds", "lewd", "xnx", "fap", "fapping", "jerkoff",

    # hindi / hinglish
    "lund", "loda", "lauda", "gaand", "gand", "chut", "choot",
    "randi", "randiya", "chinal", "bhosdi", "bhosdike",
    "bhenchod", "behenchod", "madarchod", "mc ", " bc ", "lavde",
]

NSFW_EMOJI = ["🍆", "🍑", "💦", "👅", "🔞", "👙", "💋", "🤤"]

SAVAGE_COMMENTS = [
    "XP dekhke lagta hai tu kaafi time se active hai.",
    "Presence strong hai, group tero ko jaanta hai.",
    "Tu message nahi, poori vibe bhejta hai.",
    "Tere bina group chal toh jayega, par maza kam ho jayega.",
    "Consistency OP, aise hi chat garam rakh.",
]

RANK_TIERS = {
    0:    ["Dust Mode", "Background NPC", "Beginner Mode", "Silent Reader"],
    11:   ["Quiet Observer", "Human Buffering", "Slow Starter"],
    51:   ["Active Human Being", "Chat Me Entry Ho Gayi", "Warm-Up Member"],
    151:  ["Chat Enthusiast", "Daily Visitor", "Consistent Texter"],
    301:  ["Vibe Distributor", "Group Regular", "Core Member"],
    701:  ["Friendly Veteran", "Old Soul of Group", "Always-There Member"],
    1500: ["Community Legend", "Mythical OG", "Unskippable Member"],
}

ACHIEVEMENT_TIERS = [
    {
        "xp": 50,
        "title": "Active Human 💬",
        "messages": [
            "Ab group ne finally tujhe notice karna start kiya hai.",
            "Good! Ab tu sirf read-only member nahi raha.",
        ],
    },
    {
        "xp": 150,
        "title": "Chat Enthusiast 🎧",
        "messages": [
            "Chat me energy sahi aa rahi hai, aise hi reply karta reh.",
            "Tera notification rate high lag raha hai 😄",
        ],
    },
    {
        "xp": 300,
        "title": "Vibe Distributor ✨",
        "messages": [
            "Ab group ka mood tumhare messages se set hota hai.",
            "Silent chat ko bhi tu active bana deta hai.",
        ],
    },
    {
        "xp": 600,
        "title": "Friendly Regular ☕",
        "messages": [
            "Tumhare bina chat history adhuri lagti hai.",
            "Ab tumko dekh ke lagta hai permanent seat hai yaha.",
        ],
    },
    {
        "xp": 1000,
        "title": "Meme Specialist 🤣",
        "messages": [
            "Tumhare memes se log genuinely haste hain.",
            "Meme quality stable hai, supply continue rakho.",
        ],
    },
    {
        "xp": 2000,
        "title": "Group Pillar 🧱",
        "messages": [
            "Jab tum kam active hote ho, group ajeeb se quiet ho jata hai.",
            "Tumhare bina group thoda khaali khaali lagta hai.",
        ],
    },
    {
        "xp": 3500,
        "title": "Community Legend 🏅",
        "messages": [
            "Har purane member ko tumhara naam pata hota hai.",
            "Tum conversation ka hamesha hissa rahe ho.",
        ],
    },
    {
        "xp": 6000,
        "title": "Mythical OG 🐉",
        "messages": [
            "Koi nahi jaanta tum kab join huye, bas itna ke tum hamesha se yahi the.",
            "OG level reach kar liya, ye sirf time + patience se possible hai.",
        ],
    },
    {
        "xp": 10000,
        "title": "Immortal WiFi Ghost 👑",
        "messages": [
            "XP dekhke lagta hai tumhare aur group ke beech unlimited data ka contract hai.",
            "Tum chat ka permanent background process ho ab.",
        ],
    },
]

DEMON_QUOTES = [
    ("Tanjiro Kamado 🌊", "Girna galti nahi… ruk jana hota hai."),
    ("Nezuko Kamado 🔥", "Kabhi kabhi chup rehna bhi jawab hota hai."),
    ("Zenitsu ⚡", "Darr normal hai… rukna galat."),
    ("Inosuke 🐗", "Raasta nahi? Toh naya tod ke bana."),
    ("Rengoku 🔥", "Jab tak dil dhadke, haar nahi hoti."),
    ("Shinobu 🦋", "Muskurana kabhi kabhi strength bhi hota hai."),
    ("Muzan 💀", "Power dikhayi nahi, feel karayi jati hai."),
    ("Akaza ⚔️", "Strong banna hai toh pain se dosti kar."),
]

# ---------- HTTP KEEPALIVE SERVER (UPTIMEROBOT / RENDER) ----------

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Telegram auto-delete bot running.\n")

    def log_message(self, format, *args):
        return  # avoid console spam


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


async def reply_autodelete(message, context: ContextTypes.DEFAULT_TYPE, text: str, reply_markup=None):
    delay = context.chat_data.get("delay", DELETE_DELAY)
    sent = await message.reply_text(text, reply_markup=reply_markup)
    asyncio.create_task(delete_after(context.bot, sent.chat.id, sent.message_id, delay))
    return sent


async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    chat = update.effective_chat
    if not chat or not user:
        return False
    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
    except Exception:
        return False
    return member.status in ("administrator", "creator")


def get_random_rank(xp: int) -> str:
    level = max(k for k in RANK_TIERS.keys() if xp >= k)
    return choice(RANK_TIERS[level])


def get_random_comment() -> str:
    return choice(SAVAGE_COMMENTS)


async def force_delete(message, context: ContextTypes.DEFAULT_TYPE):
    """Instant delete for NSFW/promo."""
    try:
        await context.bot.delete_message(message.chat.id, message.message_id)
    except Exception:
        pass


# ---------- MAIN MESSAGE HANDLER ----------

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user = update.effective_user

    if not msg or not user:
        return

    chat_id = msg.chat.id
    raw_text = (msg.text or msg.caption or "")

    text = raw_text.lower()

    # brutal cleaning for NSFW detection
    clean = (
        text.replace(" ", "")
            .replace(".", "")
            .replace("*", "")
            .replace("_", "")
            .replace("-", "")
            .replace("•", "")
            .replace("/", "")
            .replace("\\", "")
            .replace("|", "")
            .replace("$", "s")
            .replace("5", "s")
            .replace("@", "a")
            .replace("4", "a")
            .replace("3", "e")
            .replace("1", "i")
            .replace("!", "i")
            .replace("0", "o")
            .replace("€", "e")
            .replace("🍆", "dick")
            .replace("🍑", "ass")
            .replace("💦", "cum")
    )

    # Auto delete every message (after delay)
    delay = context.chat_data.get("delay", DELETE_DELAY)
    asyncio.create_task(delete_after(context.bot, chat_id, msg.message_id, delay))

    # Ignore other bots for XP/filter/NSFW (sirf delete scheduled)
    if user.is_bot:
        return

    # --- Anti NSFW (if enabled) ---
    if context.chat_data.get("nsfw_enabled", True):
        if any(nw in clean for nw in NSFW_PATTERNS) or any(e in text for e in NSFW_EMOJI):
            await force_delete(msg, context)
            warn = await msg.reply_text("🚫 NSFW detected. Message removed.")
            asyncio.create_task(delete_after(context.bot, warn.chat.id, warn.message_id, 5))
            return

    # --- Anti promo / links / @ spam ---
    promo_mentions_enabled = context.chat_data.get("promo_mentions", True)
    is_link = any(pat in text for pat in PROMO_PATTERNS)
    is_tag_spam = promo_mentions_enabled and "@" in text

    if is_link or is_tag_spam:
        await force_delete(msg, context)
        warn = await msg.reply_text("🚫 Free promotion allowed nahi. Chill.")
        asyncio.create_task(delete_after(context.bot, warn.chat.id, warn.message_id, 5))
        return

    # --- Keyword filters (word -> reply) ---
    filters_map = context.chat_data.get("filters", {})
    for word, response in filters_map.items():
        if word and word.lower() in text:
            await reply_autodelete(msg, context, response)
            break

    # --- XP system + achievements ---
    xp_data = context.chat_data.get("xp", {})
    entry = xp_data.get(user.id, {"xp": 0, "name": user.full_name})

    prev_xp = entry["xp"]
    entry["xp"] = prev_xp + 1
    entry["name"] = user.full_name
    new_xp = entry["xp"]

    xp_data[user.id] = entry
    context.chat_data["xp"] = xp_data

    # Achievements per user
    ach_data = context.chat_data.get("achievements", {})
    user_achs = ach_data.get(user.id, [])

    for ach in ACHIEVEMENT_TIERS:
        threshold = ach["xp"]
        if prev_xp < threshold <= new_xp and threshold not in user_achs:
            title = ach["title"]
            msg_text = choice(ach["messages"])
            text_ach = (
                "🎉 Achievement Unlocked!\n\n"
                f"🏆 {title}\n"
                f"⭐ XP: {new_xp}\n\n"
                f"{msg_text}"
            )
            await reply_autodelete(msg, context, text_ach)

            user_achs.append(threshold)
            ach_data[user.id] = user_achs
            context.chat_data["achievements"] = ach_data
            break  # ek achievement per message


# ---------- COMMANDS ----------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    is_admin_user = await is_admin(update, context)

    # ----- ADMIN VIEW -----
    if is_admin_user:
        delay = context.chat_data.get("delay", DELETE_DELAY)
        promo_mentions_enabled = context.chat_data.get("promo_mentions", True)
        nsfw_enabled = context.chat_data.get("nsfw_enabled", True)

        text = (
            "⚔️ Savage Auto-Delete Bot (Admin Mode)\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"⏳ Auto-Delete: {delay}s\n"
            f"📛 Promo Filter: {'ON' if promo_mentions_enabled else 'OFF'}\n"
            f"🔞 NSFW: {'ON' if nsfw_enabled else 'OFF'}\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🛠 Admin Commands:\n"
            "• /menu\n"
            "• /delay <sec>\n"
            "• /filter word -> reply\n"
            "• /filterlist\n"
            "• /filterdel <word>\n"
            "• /promomentions on/off\n"
            "• /nsfw on/off/status\n"
            "• /rank /top\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "You're the handler here. 😎"
        )
        await reply_autodelete(update.message, context, text)
        return

    # ----- NORMAL USER VIEW -----
    name, quote = choice(DEMON_QUOTES)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Join Our Group", url="https://t.me/yourGroupLink")]
    ])

    text = f"🩸 {name}\n\n“{quote}”"

    sent = await update.message.reply_text(text, reply_markup=keyboard)
    delay = context.chat_data.get("delay", DELETE_DELAY)
    asyncio.create_task(delete_after(context.bot, sent.chat.id, sent.message_id, delay))


async def cmd_delay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if not await is_admin(update, context):
        return await reply_autodelete(update.message, context, "Only admins allowed.")

    if not context.args:
        d = context.chat_data.get("delay", DELETE_DELAY)
        return await reply_autodelete(update.message, context, f"Current delay: {d}s")

    try:
        value = int(context.args[0])
        context.chat_data["delay"] = value
        await reply_autodelete(update.message, context, f"Delay updated to {value}s.")
    except ValueError:
        await reply_autodelete(update.message, context, "Invalid format. Example: /delay 30")


async def cmd_filter_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if not await is_admin(update, context):
        return await reply_autodelete(update.message, context, "Only admins allowed.")

    text = update.message.text
    if "->" not in text:
        return await reply_autodelete(update.message, context, "Format:\n/filter hello -> reply text")

    payload = text[len("/filter"):].strip()
    word, reply_text = map(str.strip, payload.split("->", 1))

    filters_map = context.chat_data.get("filters", {})
    filters_map[word.lower()] = reply_text
    context.chat_data["filters"] = filters_map

    await reply_autodelete(update.message, context, f"Filter added: {word}")


async def cmd_filter_del(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if not await is_admin(update, context):
        return await reply_autodelete(update.message, context, "Only admins allowed.")

    if not context.args:
        return await reply_autodelete(update.message, context, "Usage: /filterdel <word>")

    word = context.args[0].lower()
    filters_map = context.chat_data.get("filters", {})

    if word in filters_map:
        del filters_map[word]
        context.chat_data["filters"] = filters_map
        await reply_autodelete(update.message, context, f"Removed filter: {word}")
    else:
        await reply_autodelete(update.message, context, "Filter not found.")


async def cmd_filter_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    filters_map = context.chat_data.get("filters", {})
    if not filters_map:
        return await reply_autodelete(update.message, context, "No filters set.")

    lines = [f"{w} -> {r}" for w, r in filters_map.items()]
    await reply_autodelete(update.message, context, "Filters:\n" + "\n".join(lines))


async def cmd_rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    user = update.effective_user
    xp_data = context.chat_data.get("xp", {})
    entry = xp_data.get(user.id, {"xp": 0, "name": user.full_name})
    xp = entry["xp"]
    rank = get_random_rank(xp)
    comment = get_random_comment()

    text = (
        f"👤 {user.full_name}\n"
        f"XP: {xp}\n"
        f"Rank: {rank}\n\n"
        f"Status: {comment}"
    )
    await reply_autodelete(update.message, context, text)


async def cmd_top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    xp_data = context.chat_data.get("xp", {})
    if not xp_data:
        return await reply_autodelete(update.message, context, "Empty leaderboard.")

    ranked = sorted(xp_data.values(), key=lambda x: x["xp"], reverse=True)[:10]
    lines = [
        f"{i+1}. {u['name']} — {u['xp']} XP"
        for i, u in enumerate(ranked)
    ]
    await reply_autodelete(update.message, context, "Top Users:\n" + "\n".join(lines))


async def cmd_promomentions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if not await is_admin(update, context):
        return await reply_autodelete(update.message, context, "Only admins allowed.")

    if not context.args or context.args[0].lower() not in ("on", "off"):
        return await reply_autodelete(update.message, context, "Usage: /promomentions on/off")

    state = context.args[0].lower() == "on"
    context.chat_data["promo_mentions"] = state
    await reply_autodelete(update.message, context, f"Promo tag filter: {'ON' if state else 'OFF'}")


async def cmd_promostatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    state = context.chat_data.get("promo_mentions", True)
    await reply_autodelete(update.message, context, f"Promo tag filter: {'ON' if state else 'OFF'}")


async def cmd_nsfw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if not await is_admin(update, context):
        return await reply_autodelete(update.message, context, "Only admins allowed.")

    if not context.args or context.args[0].lower() not in ("on", "off", "status"):
        return await reply_autodelete(update.message, context, "Usage: /nsfw on | off | status")

    mode = context.args[0].lower()

    if mode == "status":
        current = context.chat_data.get("nsfw_enabled", True)
        return await reply_autodelete(update.message, context, f"NSFW Filter: {'ON' if current else 'OFF'}")

    if mode == "on":
        context.chat_data["nsfw_enabled"] = True
        return await reply_autodelete(update.message, context, "NSFW filter activated.")

    if mode == "off":
        context.chat_data["nsfw_enabled"] = False
        return await reply_autodelete(update.message, context, "NSFW filter disabled.")


# ---------- BUTTON MENU ----------

async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    keyboard = [
        [
            InlineKeyboardButton("Top Users", callback_data="menu_top"),
            InlineKeyboardButton("My Rank", callback_data="menu_rank"),
        ],
        [
            InlineKeyboardButton("Settings", callback_data="menu_settings"),
        ],
    ]
    markup = InlineKeyboardMarkup(keyboard)
    msg = await update.message.reply_text("Menu:", reply_markup=markup)
    delay = context.chat_data.get("delay", DELETE_DELAY)
    asyncio.create_task(delete_after(context.bot, msg.chat.id, msg.message_id, delay))


async def cb_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    await query.answer()
    data = query.data
    user = query.from_user

    if data == "menu_top":
        xp_data = context.chat_data.get("xp", {})
        if not xp_data:
            await reply_autodelete(query.message, context, "Empty leaderboard.")
        else:
            ranked = sorted(xp_data.values(), key=lambda x: x["xp"], reverse=True)[:10]
            lines = [f"{i+1}. {u['name']} — {u['xp']} XP" for i, u in enumerate(ranked)]
            await reply_autodelete(query.message, context, "Top Users:\n" + "\n".join(lines))

    elif data == "menu_rank":
        xp_data = context.chat_data.get("xp", {})
        entry = xp_data = context.chat_data.get("xp", {})
        entry = xp_data.get(user.id, {"xp": 0, "name": user.full_name})
        xp = entry["xp"]
        rank = get_random_rank(xp)
        comment = get_random_comment()
        text = (
            f"👤 {user.full_name}\n"
            f"XP: {xp}\n"
            f"Rank: {rank}\n\n"
            f"Status: {comment}"
        )
        await reply_autodelete(query.message, context, text)

    elif data == "menu_settings":
        delay = context.chat_data.get("delay", DELETE_DELAY)
        promo_state = "ON" if context.chat_data.get("promo_mentions", True) else "OFF"
        nsfw_state = "ON" if context.chat_data.get("nsfw_enabled", True) else "OFF"
        text = (
            "Settings:\n"
            f"- Auto-delete delay: {delay}s\n"
            f"- Promo tag filter: {promo_state}\n"
            f"- NSFW filter: {nsfw_state}"
        )
        await reply_autodelete(query.message, context, text)


# ---------- MAIN (NO EVENT-LOOP CONFLICT) ----------

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN env var not set.")

    # HTTP server for Render/UptimeRobot
    server_thread = threading.Thread(target=run_http_server, daemon=True)
    server_thread.start()

    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Commands
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("menu", cmd_menu))
    application.add_handler(CommandHandler("delay", cmd_delay))
    application.add_handler(CommandHandler("filter", cmd_filter_add))
    application.add_handler(CommandHandler("filterdel", cmd_filter_del))
    application.add_handler(CommandHandler("filterlist", cmd_filter_list))
    application.add_handler(CommandHandler("rank", cmd_rank))
    application.add_handler(CommandHandler("top", cmd_top))
    application.add_handler(CommandHandler("promomentions", cmd_promomentions))
    application.add_handler(CommandHandler("promostatus", cmd_promostatus))
    application.add_handler(CommandHandler("nsfw", cmd_nsfw))

    # Menu callbacks
    application.add_handler(CallbackQueryHandler(cb_menu, pattern=r"^menu_"))

    # All messages handler
    application.add_handler(MessageHandler(filters.ALL, on_message))

    logger.info("Starting Telegram bot polling…")
    application.run_polling()


if __name__ == "__main__":
    main()
