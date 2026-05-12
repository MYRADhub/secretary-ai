from datetime import datetime, date
from zoneinfo import ZoneInfo
from handlers.todo import list_todos, format_todo_list, get_due_soon
from handlers.reminder import list_pending_reminders

TZ = ZoneInfo("America/New_York")


async def _get_calendar_events(days: int) -> str:
    try:
        from handlers.calendar import list_events, format_events
        events = await list_events(days=days)
        return format_events(events)
    except Exception:
        return ""


def _reminders_due_today() -> list[dict]:
    today = date.today()
    reminders = list_pending_reminders()
    return [r for r in reminders if r["remind_at"].date() == today]


async def morning_briefing() -> str:
    now = datetime.now(TZ)
    todos = list_todos()
    due_soon = get_due_soon(days=1)
    todays_reminders = _reminders_due_today()
    calendar_text = await _get_calendar_events(days=1)

    lines = [f"Good morning! Here's your briefing for {now.strftime('%A, %B %d')}.\n"]

    if calendar_text and calendar_text != "No upcoming events.":
        lines.append(f"Today's calendar:\n{calendar_text}")

    if todos:
        lines.append(f"\nTasks ({len(todos)} pending):\n" + format_todo_list(todos))
    else:
        lines.append("\nNo pending tasks.")

    if due_soon:
        lines.append("\nDue today or tomorrow:\n" + format_todo_list(due_soon))

    if todays_reminders:
        reminder_lines = "\n".join(
            f"- {r['text']} at {r['remind_at'].astimezone(TZ).strftime('%I:%M %p')}"
            for r in todays_reminders
        )
        lines.append(f"\nReminders today:\n{reminder_lines}")
    else:
        lines.append("\nNo reminders today.")

    return "\n".join(lines)


async def midday_briefing() -> str:
    now = datetime.now(TZ)
    todos = list_todos()
    due_soon = get_due_soon(days=0)
    todays_reminders = _reminders_due_today()
    upcoming_reminders = [
        r for r in todays_reminders
        if r["remind_at"].astimezone(TZ) > now
    ]
    calendar_text = await _get_calendar_events(days=1)

    lines = [f"Midday check-in — {now.strftime('%I:%M %p')}.\n"]

    if calendar_text and calendar_text != "No upcoming events.":
        lines.append(f"Remaining today:\n{calendar_text}")

    if todos:
        lines.append(f"\n{len(todos)} task(s) still pending:\n" + format_todo_list(todos))
    else:
        lines.append("\nAll clear — no pending tasks.")

    if due_soon:
        lines.append("\nDue today:\n" + format_todo_list(due_soon))

    if upcoming_reminders:
        reminder_lines = "\n".join(
            f"- {r['text']} at {r['remind_at'].astimezone(TZ).strftime('%I:%M %p')}"
            for r in upcoming_reminders
        )
        lines.append(f"\nUpcoming reminders:\n{reminder_lines}")

    return "\n".join(lines)
