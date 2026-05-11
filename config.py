from dotenv import load_dotenv
import os

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_ALLOWED_USER_ID = os.getenv("TELEGRAM_ALLOWED_USER_ID")

NEWS_FETCH_TIMES = ["08:00", "18:00"]

NEWS_FEEDS = [
    "https://hnrss.org/frontpage",
    "https://feeds.feedburner.com/oreilly/radar",
    "https://www.artificialintelligence-news.com/feed/",
    "https://techcrunch.com/feed/",
]

DB_PATH = os.getenv("DB_PATH", "secretary.db")
