import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
from bot.dispatcher import dispatch
from handlers.news import fetch_and_summarize
import config

logger = logging.getLogger(__name__)

_app: Application | None = None


def get_allowed_user_id() -> int | None:
    if config.TELEGRAM_ALLOWED_USER_ID:
        return int(config.TELEGRAM_ALLOWED_USER_ID)
    return None


async def _handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    allowed_id = get_allowed_user_id()
    if allowed_id and update.effective_user.id != allowed_id:
        return

    text = update.message.text
    if not text:
        return

    try:
        response = await dispatch(text, send_news_fn=fetch_and_summarize)
        await update.message.reply_text(response)
    except Exception:
        logger.exception("Error handling message")
        await update.message.reply_text("Something went wrong. Try again.")


async def _handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Secretary online. You can:\n"
        "- Add todos: 'add buy milk to my list'\n"
        "- Set reminders: 'remind me at 3pm to call John'\n"
        "- Store rules: 'remember that...'\n"
        "- Ask for news: 'what's the latest in tech?'\n"
        "- Just talk to me naturally."
    )


def build_app() -> Application:
    global _app
    _app = (
        Application.builder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .build()
    )
    _app.add_handler(CommandHandler("start", _handle_start))
    _app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _handle_message))
    return _app


async def send_message(text: str) -> None:
    allowed_id = get_allowed_user_id()
    if _app is None or allowed_id is None:
        logger.warning("Cannot send proactive message: app or user ID not configured")
        return
    await _app.bot.send_message(chat_id=allowed_id, text=text)
