from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters
)

BOT_TOKEN = "8437918087:AAEkAr2ZmCrQNF6UC2jde0REClfmiIglSRE"

BAD_WORDS = {
    "sex", "porn", "fuck", "fucking", "bitch", "asshole",
    "nude", "nudes", "xxx", "boobs", "dick", "pussy",
    "slut", "horny", "nsfw", "rape"
}

def is_admin(member):
    return member.status in ("administrator", "creator")

# /start – professional help
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Smart Moderation Bot\n\n"
        "This bot helps maintain a clean, safe, and respectful group environment.\n\n"
        "🔹 Features:\n"
        "• Automatically deletes restricted or abusive words\n"
        "• Admin messages are always protected\n"
        "• Operates silently in the background\n\n"
        "🔹 Available Commands:\n"
        "/addword <word>  – Add a word to the blocked list (Admin only)\n"
        "/delword <word>  – Remove a word from the blocked list (Admin only)\n"
        "/listwords       – View blocked words (Admin only)\n\n"
        "Designed for professional group moderation."
    )

# bad word detector (admin safe)
async def bad_word_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    member = await context.bot.get_chat_member(
        update.effective_chat.id,
        update.effective_user.id
    )

    # ignore admins
    if is_admin(member):
        return

    text = update.message.text.lower()
    for word in BAD_WORDS:
        if word in text:
            await update.message.delete()
            break

# add word (admin only)
async def add_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await context.bot.get_chat_member(
        update.effective_chat.id, update.effective_user.id
    )
    if not is_admin(member) or not context.args:
        return

    BAD_WORDS.add(context.args[0].lower())
    await update.message.delete()

# remove word (admin only)
async def del_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await context.bot.get_chat_member(
        update.effective_chat.id, update.effective_user.id
    )
    if not is_admin(member) or not context.args:
        return

    BAD_WORDS.discard(context.args[0].lower())
    await update.message.delete()

# list words (admin only)
async def list_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await context.bot.get_chat_member(
        update.effective_chat.id, update.effective_user.id
    )
    if not is_admin(member):
        return

    await update.message.reply_text(
        "🚫 Blocked words:\n" + ", ".join(sorted(BAD_WORDS))
    )

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(
    MessageHandler(filters.TEXT & filters.ChatType.GROUPS, bad_word_filter)
)
app.add_handler(CommandHandler("addword", add_word))
app.add_handler(CommandHandler("delword", del_word))
app.add_handler(CommandHandler("listwords", list_words))

print("Smart Moderation Bot running (welcome removed)...")
app.run_polling()
