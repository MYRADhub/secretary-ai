import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from handlers.news import fetch_and_summarize
from handlers.reminder import get_due_reminders, mark_reminder_sent
import config

logger = logging.getLogger(__name__)

_send_message_fn = None


def init_scheduler(send_message_fn) -> AsyncIOScheduler:
    global _send_message_fn
    _send_message_fn = send_message_fn

    scheduler = AsyncIOScheduler()

    for time_str in config.NEWS_FETCH_TIMES:
        hour, minute = map(int, time_str.split(":"))
        scheduler.add_job(
            _run_news_digest,
            trigger="cron",
            hour=hour,
            minute=minute,
            id=f"news_{time_str}",
        )

    scheduler.add_job(
        _check_reminders,
        trigger="interval",
        minutes=1,
        id="reminder_check",
    )

    return scheduler


async def _run_news_digest() -> None:
    if _send_message_fn is None:
        return
    try:
        digest = await fetch_and_summarize()
        await _send_message_fn(digest)
    except Exception:
        logger.exception("Failed to fetch/send news digest")


async def _check_reminders() -> None:
    if _send_message_fn is None:
        return
    try:
        due = get_due_reminders()
        for r in due:
            await _send_message_fn(f"Reminder: {r['text']}")
            mark_reminder_sent(r["id"])
    except Exception:
        logger.exception("Failed to check reminders")
