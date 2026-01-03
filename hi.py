# ================= SMART MODERATION BOT (FINAL WORKING BUILD) =================

import asyncio
import json
import re
import signal
import sys
from datetime import datetime, timedelta, time

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters
)

# ================= CONFIG =================
BOT_TOKEN = "8437918087:AAEkAr2ZmCrQNF6UC2jde0REClfmiIglSRE"

OWNER_ID = 5436530930          # special user
IGNORE_USER_ID = 5436530930   # ignored from moderation

WORDS_FILE = "words.json"
GROUPS_FILE = "groups.json"

# ================= DATA =================
DEFAULT_BAD_WORDS = {
    "sex","porn","fuck","bitch","asshole","nude","xxx",
    "boobs","dick","pussy","slut","horny","nsfw","rape"
}

SLANG_PATTERNS = [
    r"\b(m[\W_]*c)\b",
    r"\b(b[\W_]*c)\b",
    r"\b(m[\W_]*d[\W_]*r)\b",
    r"\b(r[\W_]*n[\W_]*n[\W_]*d)\b",
    r"\b(l[\W_]*o[\W_]*d)\b",
]

EMOJI_ABUSE_PATTERN = re.compile(r"[🍑🍆💦🤬🤮🤢🖕]", re.UNICODE)

CUSTOM_BAD_WORDS = set()
GROUP_STATS = {}      # chat_id : count
USER_WARNED = {}      # user_id : True

# ================= FILE UTILS =================
def load_words():
    global CUSTOM_BAD_WORDS
    try:
        with open(WORDS_FILE, "r") as f:
            CUSTOM_BAD_WORDS = set(json.load(f))
    except:
        CUSTOM_BAD_WORDS = set()

def save_words():
    with open(WORDS_FILE, "w") as f:
        json.dump(list(CUSTOM_BAD_WORDS), f)

def load_groups():
    global GROUP_STATS
    try:
        with open(GROUPS_FILE, "r") as f:
            GROUP_STATS = json.load(f)
    except:
        GROUP_STATS = {}

def save_groups():
    with open(GROUPS_FILE, "w") as f:
        json.dump(GROUP_STATS, f)

# ================= UTILS =================
def is_owner(uid):
    return uid == OWNER_ID

def is_ignored(uid):
    return uid == IGNORE_USER_ID

def is_admin(member):
    return member.status in ("administrator", "creator")

def normalize(text):
    return re.sub(r"[^a-z]", "", text.lower())

# ================= /START =================
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Support", url="https://t.me/Frx_Shooter")]]
    )

    await update.message.reply_text(
        "<b>🤖 Smart Moderation Bot</b>\n\n"
        "<b>🎯 Purpose</b>\n"
        "• Maintain respectful communication\n"
        "• Automatically block abusive language\n\n"
        "<b>⚙️ How it Works</b>\n"
        "• Silent background monitoring\n"
        "• First violation shows a warning\n"
        "• Further violations are deleted automatically\n"
        "• Daily group-wise moderation report\n\n"
        "<b>🟢 Status:</b> Active",
        parse_mode="HTML",
        reply_markup=keyboard
    )

# ================= OWNER COMMANDS =================
async def add_word(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    if not ctx.args or len(ctx.args) > 20:
        return
    for w in ctx.args:
        CUSTOM_BAD_WORDS.add(w.lower().strip())
    save_words()
    await update.message.reply_text("✅ Added")

async def remove_word(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    if not ctx.args or len(ctx.args) > 20:
        return
    for w in ctx.args:
        CUSTOM_BAD_WORDS.discard(w.lower().strip())
    save_words()
    await update.message.reply_text("🗑️ Removed")

# ================= FILTER =================
async def bad_word_filter(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    if update.message.text.startswith("/"):
        return

    chat_id = str(update.effective_chat.id)
    user = update.effective_user

    if chat_id not in GROUP_STATS:
        GROUP_STATS[chat_id] = 0
        save_groups()

    if is_owner(user.id) or is_ignored(user.id):
        return

    member = await ctx.bot.get_chat_member(update.effective_chat.id, user.id)

    text = update.message.text.lower()
    clean = normalize(text)

    matched = False

    for word in DEFAULT_BAD_WORDS.union(CUSTOM_BAD_WORDS):
        if word in clean:
            matched = True
            break

    if not matched:
        for pattern in SLANG_PATTERNS:
            if re.search(pattern, text):
                matched = True
                break

    if not matched and EMOJI_ABUSE_PATTERN.search(update.message.text):
        matched = True

    if not matched:
        return

    # delete abusive message
    await update.message.delete()
    GROUP_STATS[chat_id] += 1
    save_groups()

    # admin → silent delete
    if is_admin(member):
        return

    uid = user.id

    # first time warning
    if not USER_WARNED.get(uid):
        USER_WARNED[uid] = True
        await ctx.bot.send_message(
            update.effective_chat.id,
            "⚠️ Abusive language detected.\n"
            "Further messages like this will be deleted automatically."
        )

# ================= DAILY REPORT LOOP =================
async def daily_report_loop(app):
    while True:
        now = datetime.now()
        target = datetime.combine(now.date(), time(23, 59))
        if now >= target:
            target += timedelta(days=1)

        await asyncio.sleep((target - now).total_seconds())

        for gid, count in list(GROUP_STATS.items()):
            try:
                await app.bot.send_message(
                    int(gid),
                    "<b>📊 Daily Moderation Report</b>\n\n"
                    f"• Total abusive messages removed today: <b>{count}</b>\n\n"
                    "System status: Active",
                    parse_mode="HTML"
                )
                GROUP_STATS[gid] = 0
            except:
                pass

        save_groups()

# ================= STARTUP HOOK =================
async def on_startup(app):
    app.create_task(daily_report_loop(app))

# ================= SAFE SHUTDOWN =================
def shutdown_handler(sig, frame):
    save_groups()
    save_words()
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)

# ================= RUN =================
load_words()
load_groups()

app = (
    ApplicationBuilder()
    .token(BOT_TOKEN)
    .post_init(on_startup)
    .build()
)

app.add_handler(CommandHandler(["addword", "addd"], add_word))
app.add_handler(CommandHandler("removeword", remove_word))
app.add_handler(CommandHandler("start", start))

app.add_handler(
    MessageHandler(
        filters.TEXT & (filters.ChatType.GROUPS | filters.ChatType.SUPERGROUP),
        bad_word_filter
    )
)

print("Smart Moderation Bot running...")
app.run_polling()
