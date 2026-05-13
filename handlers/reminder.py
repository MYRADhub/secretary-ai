from datetime import datetime
from storage.db import get_conn
import psycopg2.extras


def add_reminder(text: str, remind_at: datetime) -> dict:
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "INSERT INTO reminders (text, remind_at) VALUES (%s, %s) RETURNING id",
        (text, remind_at),
    )
    row_id = cur.fetchone()["id"]
    conn.commit()
    cur.close()
    conn.close()
    return {"id": row_id, "text": text, "remind_at": remind_at.isoformat()}


def get_due_reminders() -> list[dict]:
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT id, text, remind_at FROM reminders "
        "WHERE sent = 0 AND remind_at <= NOW() "
        "AND (snoozed_until IS NULL OR snoozed_until <= NOW())",
    )
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return rows


def snooze_reminder(reminder_id: int, minutes: int) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE reminders SET sent = 0, snoozed_until = NOW() + (%s * INTERVAL '1 minute') "
        "WHERE id = %s",
        (minutes, reminder_id),
    )
    affected = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    return affected > 0


def mark_reminder_sent(reminder_id: int) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE reminders SET sent = 1 WHERE id = %s", (reminder_id,))
    conn.commit()
    cur.close()
    conn.close()


def list_pending_reminders() -> list[dict]:
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT id, text, remind_at FROM reminders WHERE sent = 0 ORDER BY remind_at ASC"
    )
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return rows


def format_reminders(reminders: list[dict]) -> str:
    if not reminders:
        return "No pending reminders."
    from zoneinfo import ZoneInfo
    from datetime import timezone
    TZ = ZoneInfo("America/New_York")
    lines = []
    for r in reminders:
        dt = r["remind_at"]
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt_local = dt.astimezone(TZ)
        lines.append(f"[{r['id']}] {r['text']} — {dt_local.strftime('%Y-%m-%d %H:%M %Z')}")
    return "\n".join(lines)
