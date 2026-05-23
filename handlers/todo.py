from datetime import date, timedelta
from storage.db import get_conn
import psycopg2.extras

RECURRENCE_RULES = {"daily", "weekly", "monthly", "weekdays"}

PRIORITIES = {"high", "medium", "normal", "low"}
PRIORITY_LABEL = {"high": "!", "medium": "~", "normal": "", "low": "v"}


def _normalize_tags(tags: list[str] | str | None) -> str:
    if not tags:
        return ""
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.replace(",", " ").split()]
    return ",".join(t.lstrip("#").lower() for t in tags if t)


def _get_ordered(include_done: bool = False) -> list[dict]:
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if include_done:
        cur.execute("SELECT id, text, done, priority, order_index, tags, due_date, recurrence_rule, recurrence_interval FROM todos ORDER BY order_index ASC")
    else:
        cur.execute("SELECT id, text, done, priority, order_index, tags, due_date, recurrence_rule, recurrence_interval FROM todos WHERE done = 0 ORDER BY order_index ASC")
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return rows


def _next_due_date(current: date, rule: str, interval: int) -> date:
    if rule == "daily":
        return current + timedelta(days=interval)
    if rule == "weekly":
        return current + timedelta(weeks=interval)
    if rule == "monthly":
        month = current.month - 1 + interval
        year = current.year + month // 12
        month = month % 12 + 1
        day = min(current.day, [31,29,31,30,31,30,31,31,30,31,30,31][month-1])
        return current.replace(year=year, month=month, day=day)
    if rule == "weekdays":
        next_day = current + timedelta(days=1)
        while next_day.weekday() >= 5:
            next_day += timedelta(days=1)
        return next_day
    return current + timedelta(days=interval)


def add_todo(
    text: str,
    priority: str = "normal",
    tags: list[str] | str | None = None,
    due_date: str | None = None,
    recurrence_rule: str | None = None,
    recurrence_interval: int = 1,
) -> dict:
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT MAX(order_index) FROM todos")
    row = cur.fetchone()
    max_order = row["max"] if row["max"] is not None else 0
    order_index = max_order + 1
    tags_str = _normalize_tags(tags)
    parsed_due = None
    if due_date:
        try:
            parsed_due = date.fromisoformat(due_date)
        except ValueError:
            pass
    rule = recurrence_rule if recurrence_rule in RECURRENCE_RULES else None
    cur.execute(
        "INSERT INTO todos (text, priority, order_index, tags, due_date, recurrence_rule, recurrence_interval) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (text, priority if priority in PRIORITIES else "normal", order_index, tags_str, parsed_due, rule, recurrence_interval),
    )
    row_id = cur.fetchone()["id"]
    conn.commit()
    cur.close()
    conn.close()
    return {"id": row_id, "text": text, "priority": priority, "tags": tags_str, "due_date": parsed_due, "recurrence_rule": rule}


def list_todos(include_done: bool = False) -> list[dict]:
    rows = _get_ordered(include_done)
    for i, row in enumerate(rows):
        row["position"] = i + 1
    return rows


def list_by_tag(tag: str) -> list[dict]:
    tag = tag.lstrip("#").lower()
    rows = _get_ordered(include_done=False)
    matched = [r for r in rows if tag in [t for t in r.get("tags", "").split(",") if t]]
    for i, row in enumerate(matched):
        row["position"] = rows.index(row) + 1
    return matched


def _get_by_position(position: int, include_done: bool = True) -> dict | None:
    rows = _get_ordered(include_done)
    if 1 <= position <= len(rows):
        return rows[position - 1]
    return None


def complete_todo(position: int) -> dict:
    row = _get_by_position(position)
    if not row:
        return {"success": False}
    if row.get("done"):
        return {"success": True, "next_due": None, "already_done": True}
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE todos SET done = 1 WHERE id = %s", (row["id"],))
    conn.commit()
    cur.close()
    conn.close()

    result = {"success": True, "next_due": None}
    rule = row.get("recurrence_rule")
    if rule:
        interval = row.get("recurrence_interval") or 1
        current_due = row.get("due_date") or date.today()
        if isinstance(current_due, str):
            current_due = date.fromisoformat(current_due)
        next_due = _next_due_date(current_due, rule, interval)
        add_todo(
            text=row["text"],
            priority=row.get("priority", "normal"),
            tags=row.get("tags", ""),
            due_date=next_due.isoformat(),
            recurrence_rule=rule,
            recurrence_interval=interval,
        )
        result["next_due"] = next_due
    return result


def uncomplete_todo(position: int) -> bool:
    row = _get_by_position(position)
    if not row:
        return False
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE todos SET done = 0 WHERE id = %s", (row["id"],))
    conn.commit()
    cur.close()
    conn.close()
    return True


def set_recurrence(position: int, rule: str | None, interval: int = 1) -> bool:
    if rule is not None and rule not in RECURRENCE_RULES:
        return False
    row = _get_by_position(position)
    if not row:
        return False
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE todos SET recurrence_rule = %s, recurrence_interval = %s WHERE id = %s",
        (rule, interval, row["id"]),
    )
    conn.commit()
    cur.close()
    conn.close()
    return True


def delete_todo(position: int) -> bool:
    row = _get_by_position(position)
    if not row:
        return False
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM todos WHERE id = %s", (row["id"],))
    conn.commit()
    cur.close()
    conn.close()
    return True


def rename_todo(position: int, new_text: str) -> bool:
    row = _get_by_position(position)
    if not row:
        return False
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE todos SET text = %s WHERE id = %s", (new_text, row["id"]))
    conn.commit()
    cur.close()
    conn.close()
    return True


def set_priority(position: int, priority: str) -> bool:
    if priority not in PRIORITIES:
        return False
    row = _get_by_position(position)
    if not row:
        return False
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE todos SET priority = %s WHERE id = %s", (priority, row["id"]))
    conn.commit()
    cur.close()
    conn.close()
    return True


def set_due_date(position: int, due_date: str | None) -> bool:
    row = _get_by_position(position)
    if not row:
        return False
    parsed_due = None
    if due_date:
        try:
            parsed_due = date.fromisoformat(due_date)
        except ValueError:
            return False
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE todos SET due_date = %s WHERE id = %s", (parsed_due, row["id"]))
    conn.commit()
    cur.close()
    conn.close()
    return True


def get_due_soon(days: int = 1) -> list[dict]:
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT id, text, priority, tags, due_date FROM todos WHERE done = 0 AND due_date IS NOT NULL AND due_date <= CURRENT_DATE + %s ORDER BY due_date ASC",
        (days,),
    )
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return rows


def set_tags(position: int, tags: list[str] | str) -> bool:
    row = _get_by_position(position)
    if not row:
        return False
    tags_str = _normalize_tags(tags)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE todos SET tags = %s WHERE id = %s", (tags_str, row["id"]))
    conn.commit()
    cur.close()
    conn.close()
    return True


def move_todo(from_position: int, to_position: int) -> bool:
    rows = _get_ordered()
    if not (1 <= from_position <= len(rows)) or not (1 <= to_position <= len(rows)):
        return False
    if from_position == to_position:
        return True
    rows.insert(to_position - 1, rows.pop(from_position - 1))
    conn = get_conn()
    cur = conn.cursor()
    for i, row in enumerate(rows):
        cur.execute("UPDATE todos SET order_index = %s WHERE id = %s", (float(i + 1), row["id"]))
    conn.commit()
    cur.close()
    conn.close()
    return True


def clear_all_todos() -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM todos WHERE done = 0")
    affected = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    return affected


def clear_completed_todos() -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM todos WHERE done = 1")
    affected = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    return affected


def complete_all_todos() -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE todos SET done = 1 WHERE done = 0")
    affected = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    return affected


def format_todo_list(todos: list[dict]) -> str:
    if not todos:
        return "No tasks."
    today = date.today()
    lines = []
    for t in todos:
        pos = t.get("position", "?")
        status = "x" if t["done"] else " "
        priority_tag = PRIORITY_LABEL.get(t.get("priority", "normal"), "")
        pri = f" [{priority_tag}]" if priority_tag else ""
        raw_tags = t.get("tags", "")
        tag_str = "  " + " ".join(f"#{tag}" for tag in raw_tags.split(",") if tag) if raw_tags else ""
        due = t.get("due_date")
        if due:
            if isinstance(due, str):
                due = date.fromisoformat(due)
            delta = (due - today).days
            if delta < 0:
                due_str = f"  (overdue {abs(delta)}d)"
            elif delta == 0:
                due_str = "  (due today)"
            elif delta == 1:
                due_str = "  (due tomorrow)"
            else:
                due_str = f"  (due {due.strftime('%b %d')})"
        else:
            due_str = ""
        recur = t.get("recurrence_rule")
        interval = t.get("recurrence_interval") or 1
        if recur:
            if recur == "weekdays":
                recur_str = "  (repeats weekdays)"
            elif interval == 1:
                recur_str = f"  (repeats {recur})"
            else:
                recur_str = f"  (repeats every {interval} {recur.rstrip('ly')}s)"
        else:
            recur_str = ""
        lines.append(f"{pos}. [{status}]{pri} {t['text']}{tag_str}{due_str}{recur_str}")
    return "\n".join(lines)
