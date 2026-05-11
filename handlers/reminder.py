from datetime import datetime
from storage.db import get_conn


def add_reminder(text: str, remind_at: datetime) -> dict:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO reminders (text, remind_at) VALUES (?, ?)",
        (text, remind_at.isoformat()),
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return {"id": row_id, "text": text, "remind_at": remind_at.isoformat()}


def get_due_reminders() -> list[dict]:
    conn = get_conn()
    cur = conn.cursor()
    now = datetime.now().isoformat()
    cur.execute(
        "SELECT id, text, remind_at FROM reminders WHERE sent = 0 AND remind_at <= ?",
        (now,),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def mark_reminder_sent(reminder_id: int) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE reminders SET sent = 1 WHERE id = ?", (reminder_id,))
    conn.commit()
    conn.close()


def list_pending_reminders() -> list[dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, text, remind_at FROM reminders WHERE sent = 0 ORDER BY remind_at ASC"
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def format_reminders(reminders: list[dict]) -> str:
    if not reminders:
        return "No pending reminders."
    lines = []
    for r in reminders:
        dt = datetime.fromisoformat(r["remind_at"])
        lines.append(f"[{r['id']}] {r['text']} — {dt.strftime('%Y-%m-%d %H:%M')}")
    return "\n".join(lines)
