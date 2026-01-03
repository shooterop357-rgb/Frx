# ================= SMART MODERATION BOT (FINAL LOCKED BUILD) =================

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
    ChatMemberHandler,
    filters
)

# ================= FINAL CONFIG =================
BOT_TOKEN = "8437918087:AAEkAr2ZmCrQNF6UC2jde0REClfmiIglSRE"

OWNER_ID = 5436530930          # special user (full control)
IGNORE_USER_ID = 5436530930   # fully ignored by moderation

WORDS_FILE = "words.json"
GROUPS_FILE = "groups.json"

MAX_WARNINGS = 5
TIMEOUT_MINUTES = 5

# ================= DATA =================
DEFAULT_BAD_WORDS = {
    "sex","porn","fuck","bitch","asshole","nude","xxx",
    "boobs","dick","pussy","slut","horny","nsfw","rape"
}

SLANG_PATTERNS = [
    r"\b(m[\W_]*c)\b",
    r"\b(b[\W_]*c)\b",
    r"\b(m[\W_]*d[\W_]*r)\b",
    r"\b(r[\W_]*n[\W_]*d)\b",
    r"\b(c[\W_]*h[\W_]*t)\b",
    r"\b(l[\W_]*o[\W_]*d)\b",
    r"\b(g[\W_]*a[\W_]*n[\W_]*d)\b",
]

CUSTOM_BAD_WORDS = set()
WARNINGS = {}
GROUP_STATS = {}

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

# ================= BOT ADDED TO GROUP =================
async def on_bot_added(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat = update.chat_member.chat
    new = update.chat_member.new_chat_member
    if new.user.is_bot and new.user.id == ctx.bot.id:
        gid = str(chat.id)
        if gid not in GROUP_STATS:
            GROUP_STATS[gid] = 0
            save_groups()

# ================= /START =================
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Support", url="https://t.me/Frx_Shooter")]]
    )

    await update.message.reply_text(
        "<b>Smart Moderation Bot</b>\n\n"
        "<b>Purpose</b>\n"
        "• Maintain respectful communication\n"
        "• Automatically block abusive language\n"
        "• Apply warnings before action\n\n"
        "<b>How it Works</b>\n"
        "• Silent background monitoring\n"
        "• 5 warnings trigger a 5-minute timeout\n"
        "• Live second-by-second countdown\n"
        "• Automatic cleanup after timeout\n"
        "• Daily group-wise moderation report\n\n"
        "<b>Status</b>: Active",
        parse_mode="HTML",
        reply_markup=keyboard
    )

# ================= OWNER COMMANDS =================
async def addwrod(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return
    if not ctx.args or len(ctx.args) > 20:
        return
    for w in ctx.args:
        CUSTOM_BAD_WORDS.add(w.lower().strip())
    save_words()
    await update.message.reply_text("Added")

async def removeword(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return
    if not ctx.args or len(ctx.args) > 20:
        return
    for w in ctx.args:
        CUSTOM_BAD_WORDS.discard(w.lower().strip())
    save_words()
    await update.message.reply_text("Removed")

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
    if is_admin(member):
        return

    text = update.message.text.lower()
    clean = normalize(text)

    for word in DEFAULT_BAD_WORDS.union(CUSTOM_BAD_WORDS):
        if word in clean:
            await update.message.delete()
            GROUP_STATS[chat_id] += 1
            save_groups()
            await handle_violation(ctx, update.effective_chat.id, user)
            return

    for pattern in SLANG_PATTERNS:
        if re.search(pattern, text):
            await update.message.delete()
            GROUP_STATS[chat_id] += 1
            save_groups()
            await handle_violation(ctx, update.effective_chat.id, user)
            return

async def handle_violation(ctx, chat_id, user):
    WARNINGS[user.id] = WARNINGS.get(user.id, 0) + 1
    if WARNINGS[user.id] < MAX_WARNINGS:
        await ctx.bot.send_message(
            chat_id,
            "Please maintain respectful and professional language."
        )
    else:
        WARNINGS.pop(user.id, None)
        await mute_with_countdown(ctx, chat_id, user)

# ================= MUTE WITH LIVE COUNTDOWN =================
async def mute_with_countdown(ctx, chat_id, user):
    until = datetime.utcnow() + timedelta(minutes=TIMEOUT_MINUTES)

    await ctx.bot.restrict_chat_member(
        chat_id,
        user.id,
        permissions={},
        until_date=until
    )

    msg = await ctx.bot.send_message(
        chat_id,
        f"{user.first_name} muted.\nTime remaining: 05:00"
    )

    async def countdown():
        seconds = TIMEOUT_MINUTES * 60
        while seconds > 0:
            m, s = divmod(seconds, 60)
            await asyncio.sleep(1)
            seconds -= 1
            try:
                await msg.edit_text(
                    f"{user.first_name} muted.\nTime remaining: {m:02d}:{s:02d}"
                )
            except:
                pass
        try:
            await msg.delete()
        except:
            pass

    asyncio.create_task(countdown())

# ================= DAILY REPORT =================
async def daily_report(ctx: ContextTypes.DEFAULT_TYPE):
    for gid, count in list(GROUP_STATS.items()):
        try:
            await ctx.bot.send_message(
                int(gid),
                "<b>📊 Daily Moderation Report</b>\n\n"
                f"• Total abusive messages blocked today: <b>{count}</b>\n\n"
                "System status: Active",
                parse_mode="HTML"
            )
            GROUP_STATS[gid] = 0
        except:
            pass
    save_groups()

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

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(ChatMemberHandler(on_bot_added, ChatMemberHandler.MY_CHAT_MEMBER))
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("addwrod", addwrod))
app.add_handler(CommandHandler("removeword", removeword))

app.add_handler(
    MessageHandler(
        filters.TEXT & (filters.ChatType.GROUPS | filters.ChatType.SUPERGROUP),
        bad_word_filter
    )
)

app.job_queue.run_daily(
    daily_report,
    time=time(hour=23, minute=59)
)

print("Smart Moderation Bot running...")
app.run_polling()
