from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters
)

BOT_TOKEN = "8437918087:AAEkAr2ZmCrQNF6UC2jde0REClfmiIglSRE"

# hidden default words
DEFAULT_BAD_WORDS = {
    "sex", "porn", "fuck", "fucking", "bitch", "asshole",
    "nude", "nudes", "xxx", "boobs", "dick", "pussy",
    "slut", "horny", "nsfw", "rape"
}

# manually added words (only these will show)
CUSTOM_BAD_WORDS = set()

def is_admin(member):
    return member.status in ("administrator", "creator")

# /start – EXACT welcome text
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Smart Moderation Bot\n\n"
        "Keeps your group clean, safe, and respectful.\n\n"
        "Features:\n"
        "• Auto-deletes abusive or restricted words\n"
        "• Admin messages are protected\n"
        "• Works silently in background\n\n"
        "Admin Commands:\n"
        "/addword <word> – Add blocked word\n"
        "/delword <word> – Remove blocked word\n"
        "/listwords      – View blocked words"
    )

# filter (ignore commands)
async def bad_word_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    if update.message.text.startswith("/"):
        return

    member = await context.bot.get_chat_member(
        update.effective_chat.id,
        update.effective_user.id
    )

    if is_admin(member):
        return

    text = update.message.text.lower()
    for word in DEFAULT_BAD_WORDS.union(CUSTOM_BAD_WORDS):
        if word in text:
            await update.message.delete()
            break

# add word
async def add_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await context.bot.get_chat_member(
        update.effective_chat.id,
        update.effective_user.id
    )

    if not is_admin(member):
        await update.message.reply_text(
            "🤚 I am listening only for Administrations in this group."
        )
        return

    if not context.args or len(context.args) > 10:
        return

    for word in context.args:
        CUSTOM_BAD_WORDS.add(word.lower().strip())

    await update.message.reply_text("✅ Added")

# remove word
async def del_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await context.bot.get_chat_member(
        update.effective_chat.id,
        update.effective_user.id
    )

    if not is_admin(member):
        await update.message.reply_text(
            "🤚 I am listening only for Administrations in this group."
        )
        return

    if not context.args:
        return

    for word in context.args:
        CUSTOM_BAD_WORDS.discard(word.lower().strip())

    await update.message.reply_text("🗑️ Removed")

# list only manual words
async def list_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await context.bot.get_chat_member(
        update.effective_chat.id,
        update.effective_user.id
    )

    if not is_admin(member):
        await update.message.reply_text(
            "🤚 I am listening only for Administrations in this group."
        )
        return

    if not CUSTOM_BAD_WORDS:
        await update.message.reply_text("Nothing added")
        return

    await update.message.reply_text(
        ", ".join(sorted(CUSTOM_BAD_WORDS))
    )

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("addword", add_word))
app.add_handler(CommandHandler("delword", del_word))
app.add_handler(CommandHandler("listwords", list_words))
app.add_handler(
    MessageHandler(
        filters.TEXT & (filters.ChatType.GROUPS | filters.ChatType.SUPERGROUP),
        bad_word_filter
    )
)

print("Smart Moderation Bot running...")
app.run_polling()
