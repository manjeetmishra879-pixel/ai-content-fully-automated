"""
Trend data sources — RSS, YouTube trending RSS, Reddit, Hacker News.

We deliberately use endpoints that don't require API keys so the engine
works out-of-the-box. Callers can layer in keyed sources later.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
import feedparser

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (compatible; ContentBot/1.0)"


def _http_get(url: str, timeout: float = 10.0) -> Optional[str]:
    try:
        r = httpx.get(url, timeout=timeout, headers={"User-Agent": USER_AGENT},
                      follow_redirects=True)
        r.raise_for_status()
        return r.text
    except Exception as exc:  # noqa: BLE001
        logger.debug("Source fetch failed %s: %s", url, exc)
        return None


def fetch_google_news(query: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
    if query:
        url = f"https://news.google.com/rss/search?q={query.replace(' ', '+')}&hl=en-US&gl=US&ceid=US:en"
    else:
        url = "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"
    text = _http_get(url)
    if not text:
        return []
    parsed = feedparser.parse(text)
    out = []
    for entry in parsed.entries[:limit]:
        out.append({
            "title": entry.get("title", ""),
            "link": entry.get("link"),
            "published": entry.get("published"),
            "source": "google_news",
            "summary": entry.get("summary", "")[:500],
        })
    return out


def fetch_youtube_trending(country: str = "US", limit: int = 20) -> List[Dict[str, Any]]:
    """Public 'most popular' RSS via the trending category."""
    url = f"https://www.youtube.com/feeds/videos.xml?chart=mostPopular&gl={country}"
    text = _http_get(url)
    if not text:
        return []
    parsed = feedparser.parse(text)
    out = []
    for entry in parsed.entries[:limit]:
        out.append({
            "title": entry.get("title", ""),
            "link": entry.get("link"),
            "published": entry.get("published"),
            "source": "youtube",
            "channel": entry.get("author"),
        })
    return out


def fetch_reddit(subreddit: str = "popular", limit: int = 20) -> List[Dict[str, Any]]:
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
    try:
        r = httpx.get(url, timeout=10.0, headers={"User-Agent": USER_AGENT})
        r.raise_for_status()
        data = r.json()
    except Exception as exc:
        logger.debug("Reddit fetch failed: %s", exc)
        return []
    out = []
    for child in data.get("data", {}).get("children", []):
        d = child.get("data", {})
        out.append({
            "title": d.get("title", ""),
            "link": "https://www.reddit.com" + d.get("permalink", ""),
            "score": d.get("score", 0),
            "comments": d.get("num_comments", 0),
            "subreddit": d.get("subreddit"),
            "source": "reddit",
        })
    return out


def fetch_hackernews(limit: int = 20) -> List[Dict[str, Any]]:
    try:
        r = httpx.get("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=10.0)
        ids = r.json()[:limit]
    except Exception:
        return []
    out = []
    for hid in ids:
        try:
            item = httpx.get(f"https://hacker-news.firebaseio.com/v0/item/{hid}.json", timeout=5.0).json()
        except Exception:
            continue
        out.append({
            "title": item.get("title", ""),
            "link": item.get("url") or f"https://news.ycombinator.com/item?id={hid}",
            "score": item.get("score", 0),
            "comments": item.get("descendants", 0),
            "source": "hackernews",
        })
    return out


def fetch_rss(feed_url: str, limit: int = 20) -> List[Dict[str, Any]]:
    text = _http_get(feed_url)
    if not text:
        return []
    parsed = feedparser.parse(text)
    out = []
    for entry in parsed.entries[:limit]:
        out.append({
            "title": entry.get("title", ""),
            "link": entry.get("link"),
            "published": entry.get("published"),
            "source": parsed.feed.get("title", feed_url),
            "summary": entry.get("summary", "")[:500],
        })
    return out
