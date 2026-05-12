import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from handlers.news import fetch_and_summarize
from handlers.reminder import get_due_reminders, mark_reminder_sent
from handlers.briefing import morning_briefing, midday_briefing
from handlers.curriculum import deliver_next_lesson, get_next_lesson
from zoneinfo import ZoneInfo
import config

TZ = ZoneInfo("America/New_York")

logger = logging.getLogger(__name__)

_send_message_fn = None


def init_scheduler(send_message_fn) -> AsyncIOScheduler:
    global _send_message_fn
    _send_message_fn = send_message_fn

    scheduler = AsyncIOScheduler(timezone=TZ)

    for time_str in config.NEWS_FETCH_TIMES:
        hour, minute = map(int, time_str.split(":"))
        scheduler.add_job(
            _run_tech_digest,
            trigger="cron",
            hour=hour,
            minute=minute,
            id=f"news_tech_{time_str}",
        )
        scheduler.add_job(
            _run_finance_digest,
            trigger="cron",
            hour=hour,
            minute=minute,
            id=f"news_finance_{time_str}",
        )

    scheduler.add_job(
        _check_reminders,
        trigger="interval",
        minutes=1,
        id="reminder_check",
    )

    scheduler.add_job(
        _run_morning_briefing,
        trigger="cron",
        hour=9,
        minute=0,
        id="morning_briefing",
    )

    scheduler.add_job(
        _run_midday_briefing,
        trigger="cron",
        hour=15,
        minute=0,
        id="midday_briefing",
    )

    scheduler.add_job(
        _check_due_soon,
        trigger="cron",
        hour=8,
        minute=0,
        id="due_soon_check",
    )

    scheduler.add_job(
        _deliver_daily_lesson,
        trigger="cron",
        hour=12,
        minute=0,
        id="daily_lesson",
    )

    return scheduler


async def _run_tech_digest() -> None:
    if _send_message_fn is None:
        return
    try:
        digest = await fetch_and_summarize("tech")
        await _send_message_fn(digest)
    except Exception:
        logger.exception("Failed to fetch/send tech digest")


async def _run_finance_digest() -> None:
    if _send_message_fn is None:
        return
    try:
        digest = await fetch_and_summarize("finance")
        await _send_message_fn(digest)
    except Exception:
        logger.exception("Failed to fetch/send finance digest")


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


async def _run_morning_briefing() -> None:
    if _send_message_fn is None:
        return
    try:
        text = await morning_briefing()
        await _send_message_fn(text)
    except Exception:
        logger.exception("Failed to send morning briefing")


async def _run_midday_briefing() -> None:
    if _send_message_fn is None:
        return
    try:
        text = await midday_briefing()
        await _send_message_fn(text)
    except Exception:
        logger.exception("Failed to send midday briefing")


async def _check_due_soon() -> None:
    if _send_message_fn is None:
        return
    try:
        from handlers.todo import get_due_soon, format_todo_list
        due = get_due_soon(days=1)
        if due:
            text = "Tasks due today or tomorrow:\n" + format_todo_list(due)
            await _send_message_fn(text)
    except Exception:
        logger.exception("Failed to check due soon")


async def _deliver_daily_lesson() -> None:
    if _send_message_fn is None:
        return
    try:
        if get_next_lesson() is None:
            return
        text = await deliver_next_lesson(mark_done=True)
        await _send_message_fn(text)
    except Exception:
        logger.exception("Failed to deliver daily lesson")
