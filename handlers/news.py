import feedparser
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
from storage.db import get_conn

TZ = ZoneInfo("America/New_York")
from llm.client import chat
import psycopg2.extras
import config

TELEGRAM_MAX = 4000

CATEGORY_FEEDS = {
    "tech": config.NEWS_FEEDS,
    "finance": config.FINANCE_FEEDS,
}

CATEGORY_PROMPTS = {
    "tech": (
        "You are a tech news curator for a software developer and startup founder.\n"
        "Given a list of recent article titles and descriptions, select the 5-8 most relevant items and write a concise digest.\n"
        "Focus on: new AI models, LLM updates, developer tools, startup funding, major tech releases, security issues.\n"
        "Skip: opinion pieces, listicles, sponsored content, tutorials on basics.\n"
        "Format your response as a clean digest with brief bullet points. Be direct — no fluff."
    ),
    "finance": (
        "You are a finance news curator for a software developer and startup founder.\n"
        "Given a list of recent article titles and descriptions, select the 5-8 most relevant items and write a concise digest.\n"
        "Focus on: market movements, macro trends, interest rates, tech stock news, startup funding rounds, economic data, crypto if significant.\n"
        "Skip: individual stock tips, sponsored content, celebrity finance stories.\n"
        "Format your response as a clean digest with brief bullet points. Be direct — no fluff."
    ),
}

CATEGORY_LABELS = {
    "tech": "Tech",
    "finance": "Finance",
}


def _get_preferences(category: str) -> dict:
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT topics_follow, topics_skip FROM news_preferences WHERE category = %s",
        (category,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return {"follow": row["topics_follow"], "skip": row["topics_skip"]} if row else {"follow": "", "skip": ""}


def update_preferences(category: str = "tech", follow: str | None = None, skip: str | None = None) -> None:
    conn = get_conn()
    cur = conn.cursor()
    if follow is not None:
        cur.execute(
            "UPDATE news_preferences SET topics_follow = %s WHERE category = %s",
            (follow, category),
        )
    if skip is not None:
        cur.execute(
            "UPDATE news_preferences SET topics_skip = %s WHERE category = %s",
            (skip, category),
        )
    conn.commit()
    cur.close()
    conn.close()


def get_recent_digests(category: str = "tech", limit: int = 5) -> list[dict]:
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT digest, created_at FROM news_digests WHERE category = %s ORDER BY created_at DESC LIMIT %s",
        (category, limit),
    )
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return rows


def _save_digest(category: str, digest: str) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO news_digests (category, digest) VALUES (%s, %s)", (category, digest))
    conn.commit()
    cur.close()
    conn.close()


def _is_already_sent(url: str, category: str) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM news_sent WHERE item_url = %s AND category = %s", (url, category))
    exists = cur.fetchone() is not None
    cur.close()
    conn.close()
    return exists


def _mark_sent(url: str, category: str) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO news_sent (item_url, category) VALUES (%s, %s) ON CONFLICT DO NOTHING",
        (url, category),
    )
    conn.commit()
    cur.close()
    conn.close()


def _fetch_feed(url: str, category: str) -> list[dict]:
    feed = feedparser.parse(url)
    items = []
    for entry in feed.entries[:15]:
        item_url = entry.get("link", "")
        if not item_url or _is_already_sent(item_url, category):
            continue
        items.append({
            "title": entry.get("title", ""),
            "url": item_url,
            "summary": entry.get("summary", "")[:300],
        })
    return items


def chunk_message(text: str, max_len: int = TELEGRAM_MAX) -> list[str]:
    if len(text) <= max_len:
        return [text]
    chunks = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break
        split_at = text.rfind("\n", 0, max_len)
        if split_at == -1:
            split_at = max_len
        chunks.append(text[:split_at].rstrip())
        text = text[split_at:].lstrip()
    return chunks


async def fetch_and_summarize(category: str = "tech") -> str:
    loop = asyncio.get_event_loop()
    feeds = CATEGORY_FEEDS.get(category, config.NEWS_FEEDS)

    all_items = []
    for feed_url in feeds:
        items = await loop.run_in_executor(None, _fetch_feed, feed_url, category)
        all_items.extend(items)

    label = CATEGORY_LABELS.get(category, category.capitalize())

    if not all_items:
        return f"No new {label.lower()} news items found."

    prefs = _get_preferences(category)
    base_prompt = CATEGORY_PROMPTS.get(category, CATEGORY_PROMPTS["tech"])
    extra_instructions = ""
    if prefs["follow"]:
        extra_instructions += f"\nPay extra attention to topics: {prefs['follow']}."
    if prefs["skip"]:
        extra_instructions += f"\nSkip or deprioritize topics: {prefs['skip']}."

    system = base_prompt + extra_instructions

    articles_text = "\n\n".join(
        f"Title: {item['title']}\nURL: {item['url']}\nSummary: {item['summary']}"
        for item in all_items
    )

    digest = await chat(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": f"Here are today's articles:\n\n{articles_text}"},
        ],
        temperature=0.5,
    )

    for item in all_items:
        _mark_sent(item["url"], category)

    timestamp = datetime.now(TZ).strftime("%Y-%m-%d %H:%M ET")
    full_digest = f"{label} digest — {timestamp}\n\n{digest}"
    _save_digest(category, full_digest)
    return full_digest
