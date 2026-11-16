"""RSS-driven article crawler.

Discovery comes from RSS feeds (stable, welcome to aggregators, no keys);
full text comes from trafilatura's article extraction. Every article gets a
stable id (sha1 of its canonical URL) so re-crawls are idempotent.
"""

import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import Iterator, List, Optional

import feedparser
import httpx
import trafilatura

from . import config

logger = logging.getLogger(__name__)


@dataclass
class Article:
    id: str
    url: str
    title: str
    source: str
    published: str  # ISO 8601 or "" when the feed omits it
    text: str = ""
    summary: str = ""
    fetched_at: float = field(default_factory=time.time)


def _article_id(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()


def discover(feeds: Optional[List[str]] = None, per_feed: int = 20) -> Iterator[Article]:
    """Yield article stubs (no body yet) from each feed, newest first."""
    for feed_url in feeds or config.DEFAULT_FEEDS:
        try:
            parsed = feedparser.parse(feed_url)
        except Exception:
            logger.exception("feed failed: %s", feed_url)
            continue
        source = (parsed.feed.get("title") or feed_url).strip()
        for entry in parsed.entries[:per_feed]:
            url = entry.get("link")
            if not url:
                continue
            published = ""
            for key in ("published_parsed", "updated_parsed"):
                st = entry.get(key)
                if st:
                    published = time.strftime("%Y-%m-%dT%H:%M:%SZ", st)
                    break
            yield Article(
                id=_article_id(url),
                url=url,
                title=(entry.get("title") or "").strip(),
                source=source,
                published=published,
                summary=(entry.get("summary") or "")[:500],
            )


def fetch_body(article: Article, client: httpx.Client) -> Article:
    """Fill in full article text; fall back to the feed summary on failure."""
    try:
        resp = client.get(article.url, follow_redirects=True)
        resp.raise_for_status()
        extracted = trafilatura.extract(
            resp.text, include_comments=False, include_tables=False
        )
        article.text = (extracted or "").strip()
    except Exception as exc:
        logger.warning("body fetch failed for %s: %s", article.url, exc)
    if not article.text:
        article.text = article.summary
    return article


def crawl(feeds: Optional[List[str]] = None, per_feed: int = 20,
          delay: float = 0.5) -> Iterator[Article]:
    """Discover and hydrate articles, politely rate-limited per request."""
    headers = {"User-Agent": config.USER_AGENT}
    with httpx.Client(timeout=config.REQUEST_TIMEOUT, headers=headers) as client:
        for stub in discover(feeds, per_feed):
            yield fetch_body(stub, client)
            time.sleep(delay)
