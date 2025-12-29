from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    ChatJoinRequestHandler,
    MessageHandler,
    filters
)

BOT_TOKEN = "8583192474:AAESPvmGIcu8iRLjrqRlgSFL7DsqrWzZ-Rk"
AUTO_ACCEPT = {}

async def bot_added(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for m in update.message.new_chat_members:
        if m.id == context.bot.id:
            AUTO_ACCEPT[update.effective_chat.id] = False
            await update.message.reply_text(
                "🤖 Bot active\n"
                "Status: OFF\n\n"
                "Admin controls:\n"
                "/accept – start auto accept\n"
                "/stop – stop auto accept"
            )

async def accept_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await context.bot.get_chat_member(
        update.effective_chat.id,
        update.effective_user.id
    )
    if member.status not in ("administrator", "creator"):
        return

    AUTO_ACCEPT[update.effective_chat.id] = True
    await update.message.delete()

async def stop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await context.bot.get_chat_member(
        update.effective_chat.id,
        update.effective_user.id
    )
    if member.status not in ("administrator", "creator"):
        return

    AUTO_ACCEPT[update.effective_chat.id] = False
    await update.message.delete()

async def join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.chat_join_request.chat.id
    user_id = update.chat_join_request.from_user.id

    if not AUTO_ACCEPT.get(chat_id, False):
        return

    await context.bot.approve_chat_join_request(
        chat_id=chat_id,
        user_id=user_id
    )

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, bot_added))
app.add_handler(CommandHandler("accept", accept_cmd))
app.add_handler(CommandHandler("stop", stop_cmd))
app.add_handler(ChatJoinRequestHandler(join_request))

app.run_polling()
