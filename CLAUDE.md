# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Setup
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run
python main.py

# Deployment (CI/CD via GitHub Actions on push to main)
# SSH into DigitalOcean, runs deploy/update.sh
systemctl status secretary-ai
journalctl -u secretary-ai -f
```

No test suite or linter is configured — manual testing only.

## Architecture

Secretary AI is a Telegram bot that acts as a personal productivity assistant. Users send natural language messages; the bot classifies intent with an LLM and routes to the appropriate handler.

### Message Flow

```
Telegram message
    → bot/telegram.py       (PTB handler, voice transcription via Whisper)
    → bot/dispatcher.py     (intent classification via LLM, 20-message conversation history)
    → handlers/*.py         (todo, reminder, news, briefing, memory, search)
    → storage/db.py         (PostgreSQL via psycopg2)
```

### Key Files

| File | Role |
|------|------|
| `main.py` | Entry point: validates config, inits DB, starts PTB polling and APScheduler |
| `config.py` | Env var loading + hardcoded feed URLs, model name, timezone |
| `bot/telegram.py` | PTB Application, message/voice/command handlers, 4096-char response chunking |
| `bot/dispatcher.py` | LLM-based intent classification, conversation history deque, handler routing |
| `handlers/todo.py` | Todo CRUD with priority, tags, due dates, ordering |
| `handlers/reminder.py` | Reminder CRUD; delivery polled every minute by scheduler |
| `handlers/memory.py` | Behavioral rules ("when I say X, do Y") stored and matched per-message |
| `handlers/news.py` | RSS fetching (tech + finance feeds), LLM-summarized digests, deduplication |
| `handlers/briefing.py` | Morning/midday briefings composing todos, due items, and reminders |
| `handlers/search.py` | DuckDuckGo web search with LLM summarization |
| `llm/client.py` | OpenAI AsyncOpenAI wrapper for chat completions and Whisper transcription |
| `scheduler/jobs.py` | APScheduler cron jobs: digests (8am/6pm ET), reminder polling (1min), briefings (9am/3pm/8am) |
| `storage/db.py` | PostgreSQL schema init, migrations, connection management |

### Database Schema

- `todos` — id, text, done, priority, order_index, tags, due_date, created_at
- `reminders` — id, text, remind_at, sent, created_at
- `memories` — id, raw_input, trigger_pattern, action_type, action_params, created_at
- `news_sent` — id, item_url, category, sent_at (deduplication)
- `news_digests` — id, category, digest, created_at
- `news_preferences` — id, category, topics_follow, topics_skip

### Design Patterns

- **Async-first**: All LLM, DB, and HTTP calls are async; PTB owns the event loop with APScheduler running inside it via `AsyncIOScheduler`
- **Intent-driven routing**: Every message is classified into a structured intent + parameters before dispatch
- **Conversation context**: Last 20 messages kept in a deque for coherent follow-ups
- **Timezone**: All scheduling uses `America/New_York` via `ZoneInfo`

## Configuration

Required `.env` variables:

```
OPENAI_API_KEY=sk-...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_ALLOWED_USER_ID=...
DATABASE_URL=postgresql://user:pass@host:5432/dbname
```

Model is set in `config.py` (currently `gpt-5-nano`). News feed URLs are also hardcoded there.
