from dotenv import load_dotenv
import os

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "models/gemini-2.5-flash"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_ALLOWED_USER_ID = os.getenv("TELEGRAM_ALLOWED_USER_ID")

NEWS_FETCH_TIMES = ["08:00", "18:00"]

NEWS_FEEDS = [
    "https://hnrss.org/frontpage",
    "https://feeds.feedburner.com/oreilly/radar",
    "https://www.artificialintelligence-news.com/feed/",
    "https://techcrunch.com/feed/",
]

FINANCE_FEEDS = [
    "https://feeds.finance.yahoo.com/rss/2.0/headline",
    "https://feeds.marketwatch.com/marketwatch/topstories/",
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",
]

DATABASE_URL = os.getenv("DATABASE_URL")
