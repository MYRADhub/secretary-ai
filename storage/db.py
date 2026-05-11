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
            item_url TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'tech',
            sent_at TIMESTAMP NOT NULL DEFAULT NOW(),
            UNIQUE (item_url, category)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS news_digests (
            id SERIAL PRIMARY KEY,
            category TEXT NOT NULL DEFAULT 'tech',
            digest TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS news_preferences (
            id INTEGER PRIMARY KEY,
            category TEXT NOT NULL DEFAULT 'tech',
            topics_follow TEXT NOT NULL DEFAULT '',
            topics_skip TEXT NOT NULL DEFAULT '',
            UNIQUE (id, category)
        )
    """)

    # Migrate news_sent: drop old unique constraint on item_url alone if it exists,
    # add category column if missing
    cur.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'news_sent' AND column_name = 'category'
            ) THEN
                ALTER TABLE news_sent ADD COLUMN category TEXT NOT NULL DEFAULT 'tech';
                ALTER TABLE news_sent DROP CONSTRAINT IF EXISTS news_sent_item_url_key;
                ALTER TABLE news_sent ADD CONSTRAINT news_sent_item_url_category_key UNIQUE (item_url, category);
            END IF;
        END $$
    """)

    # Migrate news_digests: add category column if missing
    cur.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'news_digests' AND column_name = 'category'
            ) THEN
                ALTER TABLE news_digests ADD COLUMN category TEXT NOT NULL DEFAULT 'tech';
            END IF;
        END $$
    """)

    # Migrate news_preferences: add category column if missing, re-key
    cur.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'news_preferences' AND column_name = 'category'
            ) THEN
                ALTER TABLE news_preferences ADD COLUMN category TEXT NOT NULL DEFAULT 'tech';
            END IF;
        END $$
    """)

    cur.execute(
        "INSERT INTO news_preferences (id, category) VALUES (1, 'tech') ON CONFLICT DO NOTHING"
    )
    cur.execute(
        "INSERT INTO news_preferences (id, category) VALUES (2, 'finance') ON CONFLICT DO NOTHING"
    )

    conn.commit()
    cur.close()
    conn.close()
