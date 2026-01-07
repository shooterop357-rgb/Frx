# ================= SMART MODERATION BOT (FINAL FIXED) =================

import asyncio
import json
import re
import signal
import sys
import os
from datetime import datetime, timedelta, time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters
)

# ================= CONFIG =================
BOT_TOKEN = os.getenv("8437918087:AAEkAr2ZmCrQNF6UC2jde0REClfmiIglSRE")
if not BOT_TOKEN:
    print("BOT_TOKEN missing")
    sys.exit(1)

BOT_USERNAME = "SafeTalkFilterBot"
OWNER_ID = 5436530930
IGNORE_USER_ID = 5436530930

WORDS_FILE = "words.json"
GROUPS_FILE = "groups.json"

# ================= DATA =================
DEFAULT_BAD_WORDS = {
    # English
    "fuck","fucker","fucking","bitch","asshole","bastard","slut",
    "dick","pussy","boobs","porn","sex","nude","horny","rape","nsfw",

    # Hindi (roman)
    "madarchod","behenchod","chutiya","gandu","harami","kamina",
    "randi","saala","kutte","kameena","lodu","lund","gaand",

    # Short slangs
    "bc","mc","bsdk","bkl","mkc","mkl"
}

SLANG_REGEX = re.compile(
    r"\b(b[\W_]*c|m[\W_]*c|b[\W_]*s[\W_]*d[\W_]*k|"
    r"m[\W_]*k[\W_]*c|l[\W_]*o[\W_]*d|l[\W_]*u[\W_]*n[\W_]*d)\b",
    re.IGNORECASE
)

EMOJI_ABUSE_PATTERN = re.compile(r"[🍆🍑💦🖕🤬🤮]")

CUSTOM_BAD_WORDS = set()
GROUP_STATS = {}
USER_WARNED = {}  # (chat_id, user_id): timestamp
WARN_COOLDOWN = 3600  # 1 hour

# ================= FILE UTILS =================
def load_json(path, default):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except:
        return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f)

def load_words():
    global CUSTOM_BAD_WORDS
    CUSTOM_BAD_WORDS = set(load_json(WORDS_FILE, []))

def save_words():
    save_json(WORDS_FILE, list(CUSTOM_BAD_WORDS))

def load_groups():
    global GROUP_STATS
    GROUP_STATS = load_json(GROUPS_FILE, {})

def save_groups():
    save_json(GROUPS_FILE, GROUP_STATS)

# ================= UTILS =================
def is_owner(uid):
    return uid == OWNER_ID

def is_ignored(uid):
    return uid == IGNORE_USER_ID

def is_admin(member):
    return member.status in ("administrator", "creator")

def contains_abuse(text: str) -> bool:
    text = text.lower()

    words = re.findall(r"\b[a-z]{2,}\b", text)
    for w in words:
        if w in DEFAULT_BAD_WORDS or w in CUSTOM_BAD_WORDS:
            return True

    if SLANG_REGEX.search(text):
        return True

    if EMOJI_ABUSE_PATTERN.search(text):
        return True

    return False

# ================= START =================
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("➕ Add to Group", url=f"https://t.me/{BOT_USERNAME}?startgroup=true")],
            [InlineKeyboardButton("Support", url="https://t.me/Frx_Shooter")]
        ]
    )

    await update.message.reply_text(
        "<b>🤖 Smart Moderation Bot</b>\n\n"
        "• Hindi + English + Slang Filter\n"
        "• False delete fixed\n"
        "• Daily report enabled\n\n"
        "<b>Status:</b> Active",
        parse_mode="HTML",
        reply_markup=keyboard
    )

# ================= OWNER COMMANDS =================
async def add_word(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    for w in ctx.args:
        CUSTOM_BAD_WORDS.add(w.lower())
    save_words()
    await update.message.reply_text("✅ Word added")

async def remove_word(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    for w in ctx.args:
        CUSTOM_BAD_WORDS.discard(w.lower())
    save_words()
    await update.message.reply_text("🗑️ Word removed")

async def list_words(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    words = sorted(DEFAULT_BAD_WORDS.union(CUSTOM_BAD_WORDS))
    await update.message.reply_text(
        "<b>🚫 Banned Words List</b>\n\n" + ", ".join(words),
        parse_mode="HTML"
    )

# ================= FILTER =================
async def bad_word_filter(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    if update.message.text.startswith("/"):
        return

    # Mention safe
    if update.message.entities:
        for e in update.message.entities:
            if e.type in ("mention", "text_mention"):
                return

    chat_id = str(update.effective_chat.id)
    user = update.effective_user

    if chat_id not in GROUP_STATS:
        GROUP_STATS[chat_id] = 0

    if is_owner(user.id) or is_ignored(user.id):
        return

    try:
        member = await ctx.bot.get_chat_member(update.effective_chat.id, user.id)
    except:
        return

    if not contains_abuse(update.message.text):
        return

    try:
        await update.message.delete()
    except:
        return

    GROUP_STATS[chat_id] += 1
    save_groups()

    if is_admin(member):
        return

    key = (chat_id, user.id)
    now = datetime.now().timestamp()

    if key not in USER_WARNED or now - USER_WARNED[key] > WARN_COOLDOWN:
        USER_WARNED[key] = now
        await ctx.bot.send_message(
            update.effective_chat.id,
            "⚠️ Abusive language detected.\nNext time message will be deleted silently."
        )

# ================= DAILY REPORT =================
async def daily_report_loop(app):
    while True:
        now = datetime.now()
        target = datetime.combine(now.date(), time(23, 59))
        if now >= target:
            target += timedelta(days=1)

        await asyncio.sleep((target - now).total_seconds())

        for gid, count in GROUP_STATS.items():
            try:
                await app.bot.send_message(
                    int(gid),
                    f"<b>📊 Daily Moderation Report</b>\n\n"
                    f"Deleted messages today: <b>{count}</b>",
                    parse_mode="HTML"
                )
                GROUP_STATS[gid] = 0
            except:
                pass

        save_groups()

async def on_startup(app):
    app.create_task(daily_report_loop(app))

# ================= SHUTDOWN =================
def shutdown(sig, frame):
    save_groups()
    save_words()
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)

# ================= RUN =================
load_words()
load_groups()

app = (
    ApplicationBuilder()
    .token(BOT_TOKEN)
    .post_init(on_startup)
    .build()
)

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("addword", add_word))
app.add_handler(CommandHandler("removeword", remove_word))
app.add_handler(CommandHandler("list", list_words))

app.add_handler(
    MessageHandler(
        filters.TEXT & (filters.ChatType.GROUPS | filters.ChatType.SUPERGROUP),
        bad_word_filter
    )
)

print("Smart Moderation Bot running...")
app.run_polling()
