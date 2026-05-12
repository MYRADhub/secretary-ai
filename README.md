# Secretary AI

A personal 24/7 AI secretary that lives in your Telegram. Manages your todos, sets reminders, sends twice-daily news digests, searches the web, and understands natural language throughout.

## Features

### Todo Management
- Add, complete, delete, rename, reorder tasks
- Priority levels: high, medium, normal, low
- Tags: `#work`, `#personal`, etc.
- Due dates with overdue/today/tomorrow indicators
- Bulk operations: complete all, clear all
- Filter and sort by any criteria via natural language

### Reminders
- Set reminders in natural language ("remind me at 3pm to call John")
- Polled every minute, delivered on time

### News Digests
- Twice-daily digests at 8am and 6pm ET: tech and finance, sent separately
- Tech: Hacker News, O'Reilly, AI News, TechCrunch
- Finance: Yahoo Finance, MarketWatch, CNBC
- Per-category topic preferences (follow/skip)
- On-demand: "get me tech news", "get me finance news"
- Past digest recall: "what was in this morning's finance digest"

### Daily Briefings
- **9am**: good morning summary — pending tasks, today's reminders, tasks due soon
- **3pm**: midday check-in — what's left, upcoming reminders
- **8am**: proactive alert if any tasks are due today or tomorrow

### Web Search
- DuckDuckGo-powered, summarized by LLM
- "search for X", "what is Y", "look up Z"

### Memory Rules
- Store behavioral rules: "remember that when I say groceries, add it as a todo"
- LLM matches rules on every message, executes actions automatically

### Voice Messages
- Send voice messages — transcribed via OpenAI Whisper, processed like text

### Conversation History
- Last 20 messages kept in context for follow-up understanding

## Tech Stack

| Layer | Tech |
|---|---|
| Bot framework | python-telegram-bot v21+ |
| LLM (chat/intent) | OpenAI gpt-5-nano |
| Transcription | OpenAI Whisper |
| Scheduling | APScheduler (AsyncIOScheduler) |
| Database | PostgreSQL (psycopg2) |
| News parsing | feedparser |
| Hosting | DigitalOcean Droplet |
| CI/CD | GitHub Actions + SSH deploy |

## Project Structure

```
secretary_AI/
├── main.py                  # Entry point, PTB app setup
├── config.py                # Env var loading
├── requirements.txt
├── bot/
│   ├── dispatcher.py        # Intent classification + routing
│   └── telegram.py          # PTB handlers, message chunking
├── handlers/
│   ├── todo.py              # Todo CRUD, due dates, tags
│   ├── reminder.py          # Reminder CRUD
│   ├── memory.py            # Memory rule storage and matching
│   ├── news.py              # RSS fetching, LLM summarization, digests
│   ├── briefing.py          # Morning and midday briefing composers
│   └── search.py            # DuckDuckGo web search
├── llm/
│   └── client.py            # OpenAI async client (chat + transcribe)
├── scheduler/
│   └── jobs.py              # Cron jobs: news, briefings, reminders, due alerts
├── storage/
│   └── db.py                # PostgreSQL schema init and migrations
└── deploy/
    ├── setup.sh             # One-shot server setup script
    ├── update.sh            # Pull + restart + notify
    ├── notify.py            # Telegram deploy notification
    └── secretary-ai.service # systemd unit file
```

## Setup

### Prerequisites
- Python 3.12+
- PostgreSQL database
- A Telegram bot token (from [@BotFather](https://t.me/BotFather))
- OpenAI API key

### Environment Variables

Create a `.env` file:

```env
OPENAI_API_KEY=sk-...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_ALLOWED_USER_ID=...       # Your Telegram user ID (restricts access to you only)
DATABASE_URL=postgresql://user:pass@host:5432/dbname
```

### Run Locally

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

### Deploy to DigitalOcean

1. Create a $6/mo Ubuntu droplet
2. SSH in as root and run:

```bash
curl -fsSL https://raw.githubusercontent.com/MYRADhub/secretary-ai/main/deploy/setup.sh | bash
```

3. Copy your `.env` to `/home/secretary/secretary-ai/.env`
4. `systemctl restart secretary-ai`

### CI/CD (GitHub Actions)

Add two repository secrets:
- `DEPLOY_HOST` — your droplet IP
- `DEPLOY_SSH_KEY` — private SSH key with root access

Every push to `main` SSHes into the droplet and runs `deploy/update.sh`, which pulls, reinstalls deps, restarts the service, and sends a Telegram notification.

## Usage Examples

```
add buy milk #shopping due friday
show me my tasks
complete task 2
move task 3 to top
set task 1 as high priority
tag task 2 with #work #urgent
show me all work tasks
filter tasks due this week

remind me at 9am tomorrow to call the bank
show my reminders

get me tech news
get me finance news
what was in this morning's digest
follow AI and startups in tech news

search for latest OpenAI announcements
what is the current federal funds rate

remember that when I say standup add it as a todo for work
```

## Database Schema

| Table | Purpose |
|---|---|
| `todos` | Tasks with priority, tags, due date, order |
| `reminders` | Time-based reminders |
| `memories` | Behavioral rules (trigger → action) |
| `news_sent` | Deduplication of sent news items per category |
| `news_digests` | Stored past digests per category |
| `news_preferences` | Per-category follow/skip topic preferences |

## Architecture Notes

- **Single event loop**: PTB v21+ owns the event loop via `run_polling()`. The scheduler starts in `post_init` and stops in `post_shutdown` to avoid conflicts.
- **Intent classification**: One LLM call per message handles both intent parsing and memory rule matching, keeping latency low.
- **Message chunking**: Telegram's 4096-character limit is handled transparently — long responses are split on newlines and sent as sequential messages.
- **Timezone**: All scheduling and datetime context runs in `America/New_York`.
