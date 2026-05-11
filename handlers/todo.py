import sqlite3
from storage.db import get_conn

PRIORITIES = {"high", "medium", "normal", "low"}
PRIORITY_LABEL = {"high": "!", "medium": "~", "normal": "", "low": "v"}


def _get_ordered(include_done: bool = False) -> list[dict]:
    conn = get_conn()
    cur = conn.cursor()
    if include_done:
        cur.execute("SELECT id, text, done, priority, order_index FROM todos ORDER BY order_index ASC")
    else:
        cur.execute("SELECT id, text, done, priority, order_index FROM todos WHERE done = 0 ORDER BY order_index ASC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def add_todo(text: str, priority: str = "normal") -> dict:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT MAX(order_index) FROM todos")
    row = cur.fetchone()
    max_order = row[0] if row[0] is not None else 0
    order_index = max_order + 1
    cur.execute(
        "INSERT INTO todos (text, priority, order_index) VALUES (?, ?, ?)",
        (text, priority if priority in PRIORITIES else "normal", order_index),
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return {"id": row_id, "text": text, "priority": priority}


def list_todos(include_done: bool = False) -> list[dict]:
    rows = _get_ordered(include_done)
    for i, row in enumerate(rows):
        row["position"] = i + 1
    return rows


def _get_by_position(position: int, include_done: bool = False) -> dict | None:
    rows = _get_ordered(include_done)
    if 1 <= position <= len(rows):
        return rows[position - 1]
    return None


def complete_todo(position: int) -> bool:
    row = _get_by_position(position)
    if not row:
        return False
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE todos SET done = 1 WHERE id = ?", (row["id"],))
    conn.commit()
    conn.close()
    return True


def delete_todo(position: int) -> bool:
    row = _get_by_position(position)
    if not row:
        return False
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM todos WHERE id = ?", (row["id"],))
    conn.commit()
    conn.close()
    return True


def rename_todo(position: int, new_text: str) -> bool:
    row = _get_by_position(position)
    if not row:
        return False
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE todos SET text = ? WHERE id = ?", (new_text, row["id"]))
    conn.commit()
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
    cur.execute("UPDATE todos SET priority = ? WHERE id = ?", (priority, row["id"]))
    conn.commit()
    conn.close()
    return True


def move_todo(from_position: int, to_position: int) -> bool:
    rows = _get_ordered()
    if not (1 <= from_position <= len(rows)) or not (1 <= to_position <= len(rows)):
        return False
    if from_position == to_position:
        return True

    item = rows[from_position - 1]
    rows.insert(to_position - 1, rows.pop(from_position - 1))

    conn = get_conn()
    cur = conn.cursor()
    for i, row in enumerate(rows):
        cur.execute("UPDATE todos SET order_index = ? WHERE id = ?", (float(i + 1), row["id"]))
    conn.commit()
    conn.close()
    return True


def clear_all_todos() -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM todos WHERE done = 0")
    conn.commit()
    affected = cur.rowcount
    conn.close()
    return affected


def complete_all_todos() -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE todos SET done = 1 WHERE done = 0")
    conn.commit()
    affected = cur.rowcount
    conn.close()
    return affected


def format_todo_list(todos: list[dict]) -> str:
    if not todos:
        return "No tasks."
    lines = []
    for t in todos:
        pos = t.get("position", "?")
        status = "✓" if t["done"] else "○"
        priority_tag = PRIORITY_LABEL.get(t.get("priority", "normal"), "")
        tag = f" [{priority_tag}]" if priority_tag else ""
        lines.append(f"{pos}. {status}{tag} {t['text']}")
    return "\n".join(lines)
