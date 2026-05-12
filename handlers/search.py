import asyncio
import aiohttp
from llm.client import chat


async def web_search(query: str) -> str:
    loop = asyncio.get_event_loop()
    raw = await loop.run_in_executor(None, _ddg_search, query)
    if not raw:
        return "No results found."

    results_text = "\n\n".join(
        f"Title: {r['title']}\nURL: {r['url']}\nSnippet: {r['snippet']}"
        for r in raw[:5]
    )

    summary = await chat(
        messages=[
            {"role": "system", "content": "You are a helpful assistant. Answer the user's query concisely based on the search results below. Cite sources with URLs where relevant."},
            {"role": "user", "content": f"Query: {query}\n\nSearch results:\n{results_text}"},
        ],
        temperature=0.3,
    )
    return summary


def _ddg_search(query: str) -> list[dict]:
    import urllib.request
    import urllib.parse
    import json

    url = "https://api.duckduckgo.com/?q=" + urllib.parse.quote(query) + "&format=json&no_redirect=1&no_html=1"
    req = urllib.request.Request(url, headers={"User-Agent": "secretary-ai/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode())

    results = []

    if data.get("AbstractText"):
        results.append({
            "title": data.get("Heading", query),
            "url": data.get("AbstractURL", ""),
            "snippet": data["AbstractText"],
        })

    for r in data.get("RelatedTopics", []):
        if "Text" in r and "FirstURL" in r:
            results.append({
                "title": r.get("Text", "")[:80],
                "url": r["FirstURL"],
                "snippet": r["Text"],
            })
        elif "Topics" in r:
            for sub in r["Topics"]:
                if "Text" in sub and "FirstURL" in sub:
                    results.append({
                        "title": sub.get("Text", "")[:80],
                        "url": sub["FirstURL"],
                        "snippet": sub["Text"],
                    })

    return results[:5]
