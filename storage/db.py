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
            tags TEXT NOT NULL DEFAULT '',
            due_date DATE DEFAULT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)

    cur.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'todos' AND column_name = 'tags'
            ) THEN
                ALTER TABLE todos ADD COLUMN tags TEXT NOT NULL DEFAULT '';
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'todos' AND column_name = 'due_date'
            ) THEN
                ALTER TABLE todos ADD COLUMN due_date DATE DEFAULT NULL;
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'todos' AND column_name = 'recurrence_rule'
            ) THEN
                ALTER TABLE todos ADD COLUMN recurrence_rule TEXT DEFAULT NULL;
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'todos' AND column_name = 'recurrence_interval'
            ) THEN
                ALTER TABLE todos ADD COLUMN recurrence_interval INTEGER DEFAULT 1;
            END IF;
        END $$
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id SERIAL PRIMARY KEY,
            text TEXT NOT NULL,
            remind_at TIMESTAMP NOT NULL,
            sent INTEGER NOT NULL DEFAULT 0,
            snoozed_until TIMESTAMP DEFAULT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)

    cur.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'reminders' AND column_name = 'snoozed_until'
            ) THEN
                ALTER TABLE reminders ADD COLUMN snoozed_until TIMESTAMP DEFAULT NULL;
            END IF;
        END $$
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

    # Migrate news_preferences: drop legacy check constraint, add category column if missing
    cur.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'news_preferences_id_check'
                AND conrelid = 'news_preferences'::regclass
            ) THEN
                ALTER TABLE news_preferences DROP CONSTRAINT news_preferences_id_check;
            END IF;
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

    cur.execute("""
        CREATE TABLE IF NOT EXISTS curriculum_progress (
            id SERIAL PRIMARY KEY,
            module_num INTEGER NOT NULL,
            lesson_num INTEGER NOT NULL,
            completed_at TIMESTAMP NOT NULL DEFAULT NOW(),
            UNIQUE (module_num, lesson_num)
        )
    """)
    cur.execute("""
        ALTER TABLE curriculum_progress
        ADD COLUMN IF NOT EXISTS section_num INTEGER NOT NULL DEFAULT 0
    """)
    cur.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'curriculum_progress_module_num_lesson_num_key'
            ) THEN
                ALTER TABLE curriculum_progress
                DROP CONSTRAINT curriculum_progress_module_num_lesson_num_key;
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'curriculum_progress_module_section_lesson_key'
            ) THEN
                ALTER TABLE curriculum_progress
                ADD CONSTRAINT curriculum_progress_module_section_lesson_key
                UNIQUE (module_num, section_num, lesson_num);
            END IF;
        END$$;
    """)

    conn.commit()
    cur.close()
    conn.close()
