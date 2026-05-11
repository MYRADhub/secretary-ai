import feedparser
import asyncio
from datetime import datetime
from storage.db import get_conn
from llm.client import chat
import config


SUMMARIZE_SYSTEM = """You are a tech news curator for a software developer and startup founder.
Given a list of recent article titles and descriptions, select the 5-8 most relevant items and write a concise digest.
Focus on: new AI models, LLM updates, developer tools, startup funding, major tech releases, security issues.
Skip: opinion pieces, listicles, sponsored content, tutorials on basics.

Format your response as a clean digest with brief bullet points. Be direct — no fluff."""


def _is_already_sent(url: str) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM news_sent WHERE item_url = ?", (url,))
    exists = cur.fetchone() is not None
    conn.close()
    return exists


def _mark_sent(url: str) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO news_sent (item_url) VALUES (?)", (url,)
    )
    conn.commit()
    conn.close()


def _fetch_feed(url: str) -> list[dict]:
    feed = feedparser.parse(url)
    items = []
    for entry in feed.entries[:15]:
        item_url = entry.get("link", "")
        if not item_url or _is_already_sent(item_url):
            continue
        items.append({
            "title": entry.get("title", ""),
            "url": item_url,
            "summary": entry.get("summary", "")[:300],
        })
    return items


async def fetch_and_summarize() -> str:
    loop = asyncio.get_event_loop()

    all_items = []
    for feed_url in config.NEWS_FEEDS:
        items = await loop.run_in_executor(None, _fetch_feed, feed_url)
        all_items.extend(items)

    if not all_items:
        return "No new tech news items found."

    articles_text = "\n\n".join(
        f"Title: {item['title']}\nURL: {item['url']}\nSummary: {item['summary']}"
        for item in all_items
    )

    digest = await chat(
        messages=[
            {"role": "system", "content": SUMMARIZE_SYSTEM},
            {"role": "user", "content": f"Here are today's articles:\n\n{articles_text}"},
        ],
        temperature=0.5,
    )

    for item in all_items:
        _mark_sent(item["url"])

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"Tech digest — {timestamp}\n\n{digest}"
