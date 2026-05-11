import sqlite3
import config

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    conn = get_conn()
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            done INTEGER NOT NULL DEFAULT 0,
            priority TEXT NOT NULL DEFAULT 'normal',
            order_index REAL NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            remind_at TEXT NOT NULL,
            sent INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            raw_input TEXT NOT NULL,
            trigger_pattern TEXT NOT NULL,
            action_type TEXT NOT NULL,
            action_params TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS news_sent (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_url TEXT NOT NULL UNIQUE,
            sent_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS news_digests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            digest TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS news_preferences (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            topics_follow TEXT NOT NULL DEFAULT '',
            topics_skip TEXT NOT NULL DEFAULT ''
        );
    """)

    cur.execute("INSERT OR IGNORE INTO news_preferences (id) VALUES (1)")

    for col, definition in [("priority", "TEXT NOT NULL DEFAULT 'normal'"), ("order_index", "REAL NOT NULL DEFAULT 0")]:
        try:
            cur.execute(f"ALTER TABLE todos ADD COLUMN {col} {definition}")
        except sqlite3.OperationalError:
            pass

    cur.execute("UPDATE todos SET order_index = id WHERE order_index = 0")

    conn.commit()
    conn.close()
