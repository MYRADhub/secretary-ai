import psycopg2
import psycopg2.extras
import os


def get_conn():
    conn = psycopg2.connect(os.environ["DATABASE_URL"], sslmode="require")
    return conn


def init_db() -> None:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS todos (
            id SERIAL PRIMARY KEY,
            text TEXT NOT NULL,
            done INTEGER NOT NULL DEFAULT 0,
            priority TEXT NOT NULL DEFAULT 'normal',
            order_index REAL NOT NULL DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id SERIAL PRIMARY KEY,
            text TEXT NOT NULL,
            remind_at TIMESTAMP NOT NULL,
            sent INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id SERIAL PRIMARY KEY,
            raw_input TEXT NOT NULL,
            trigger_pattern TEXT NOT NULL,
            action_type TEXT NOT NULL,
            action_params TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS news_sent (
            id SERIAL PRIMARY KEY,
            item_url TEXT NOT NULL UNIQUE,
            sent_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS news_digests (
            id SERIAL PRIMARY KEY,
            digest TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS news_preferences (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            topics_follow TEXT NOT NULL DEFAULT '',
            topics_skip TEXT NOT NULL DEFAULT ''
        )
    """)

    cur.execute("INSERT INTO news_preferences (id) VALUES (1) ON CONFLICT DO NOTHING")

    conn.commit()
    cur.close()
    conn.close()
