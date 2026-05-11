import asyncio
import logging
import config
from storage.db import init_db
from bot.telegram import build_app, send_message
from scheduler.jobs import init_scheduler

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def validate_config() -> None:
    missing = []
    if not config.OPENAI_API_KEY:
        missing.append("OPENAI_API_KEY")
    if not config.TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not config.TELEGRAM_ALLOWED_USER_ID:
        missing.append("TELEGRAM_ALLOWED_USER_ID")
    if missing:
        raise RuntimeError(f"Missing required config: {', '.join(missing)}")


async def main() -> None:
    validate_config()
    init_db()

    app = build_app()
    scheduler = init_scheduler(send_message)
    scheduler.start()
    logger.info("Scheduler started")

    logger.info("Starting Telegram bot (polling)")
    await app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
