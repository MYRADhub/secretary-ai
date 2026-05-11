import feedparser
import asyncio
from datetime import datetime
from storage.db import get_conn
from llm.client import chat
import config

TELEGRAM_MAX = 4000  # leave headroom under 4096


def _get_preferences() -> dict:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT topics_follow, topics_skip FROM news_preferences WHERE id = 1")
    row = cur.fetchone()
    conn.close()
    return {"follow": row["topics_follow"], "skip": row["topics_skip"]} if row else {"follow": "", "skip": ""}


def update_preferences(follow: str | None = None, skip: str | None = None) -> None:
    conn = get_conn()
    cur = conn.cursor()
    if follow is not None:
        cur.execute("UPDATE news_preferences SET topics_follow = ? WHERE id = 1", (follow,))
    if skip is not None:
        cur.execute("UPDATE news_preferences SET topics_skip = ? WHERE id = 1", (skip,))
    conn.commit()
    conn.close()


def get_recent_digests(limit: int = 5) -> list[dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT digest, created_at FROM news_digests ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def _save_digest(digest: str) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO news_digests (digest) VALUES (?)", (digest,))
    conn.commit()
    conn.close()


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
    cur.execute("INSERT OR IGNORE INTO news_sent (item_url) VALUES (?)", (url,))
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


async def fetch_and_summarize() -> str:
    loop = asyncio.get_event_loop()

    all_items = []
    for feed_url in config.NEWS_FEEDS:
        items = await loop.run_in_executor(None, _fetch_feed, feed_url)
        all_items.extend(items)

    if not all_items:
        return "No new tech news items found."

    prefs = _get_preferences()
    extra_instructions = ""
    if prefs["follow"]:
        extra_instructions += f"\nPay extra attention to topics: {prefs['follow']}."
    if prefs["skip"]:
        extra_instructions += f"\nSkip or deprioritize topics: {prefs['skip']}."

    system = (
        "You are a tech news curator for a software developer and startup founder.\n"
        "Given a list of recent article titles and descriptions, select the 5-8 most relevant items and write a concise digest.\n"
        "Focus on: new AI models, LLM updates, developer tools, startup funding, major tech releases, security issues.\n"
        "Skip: opinion pieces, listicles, sponsored content, tutorials on basics.\n"
        "Format your response as a clean digest with brief bullet points. Be direct — no fluff."
        + extra_instructions
    )

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
        _mark_sent(item["url"])

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    full_digest = f"Tech digest — {timestamp}\n\n{digest}"
    _save_digest(full_digest)
    return full_digest
