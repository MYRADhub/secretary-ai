import sqlite3
from storage.db import get_conn


def add_todo(text: str) -> dict:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO todos (text) VALUES (?)", (text,))
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return {"id": row_id, "text": text}


def list_todos(include_done: bool = False) -> list[dict]:
    conn = get_conn()
    cur = conn.cursor()
    if include_done:
        cur.execute("SELECT id, text, done, created_at FROM todos ORDER BY created_at DESC")
    else:
        cur.execute("SELECT id, text, done, created_at FROM todos WHERE done = 0 ORDER BY created_at DESC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def complete_todo(todo_id: int) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE todos SET done = 1 WHERE id = ?", (todo_id,))
    conn.commit()
    affected = cur.rowcount
    conn.close()
    return affected > 0


def delete_todo(todo_id: int) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
    conn.commit()
    affected = cur.rowcount
    conn.close()
    return affected > 0


def format_todo_list(todos: list[dict]) -> str:
    if not todos:
        return "No pending tasks."
    lines = []
    for t in todos:
        status = "✓" if t["done"] else "○"
        lines.append(f"{status} [{t['id']}] {t['text']}")
    return "\n".join(lines)
