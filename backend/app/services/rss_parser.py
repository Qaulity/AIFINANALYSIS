"""RSS feed parser for financial news sources."""
import hashlib
from datetime import datetime
from typing import List, Optional, Dict
from time import mktime
import feedparser
from loguru import logger

from ..models import Article, ArticleSource
from ..utils import get_redis_client


class RSSParser:
    """Parses RSS/Atom feeds from financial news sources."""

    # Default financial news RSS feeds
    DEFAULT_FEEDS: Dict[str, str] = {
        "Reuters Business": "https://feeds.reuters.com/reuters/businessNews",
        "Yahoo Finance": "https://finance.yahoo.com/news/rssindex",
        "MarketWatch": "https://feeds.marketwatch.com/marketwatch/topstories/",
        "CNBC Top News": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "Bloomberg Markets": "https://feeds.bloomberg.com/markets/news.rss",
        "WSJ Markets": "https://feeds.a]washingtonpost.com/rss/business",
        "Financial Times": "https://www.ft.com/rss/home",
        "Seeking Alpha": "https://seekingalpha.com/market_currents.xml",
        "Investing.com": "https://www.investing.com/rss/news.rss",
    }

    def __init__(self, feeds: Optional[Dict[str, str]] = None):
        """Initialize with optional custom feeds."""
        self.feeds = feeds or self.DEFAULT_FEEDS
        self._seen_urls = set()

    def parse_feed(self, feed_name: str, feed_url: str) -> List[Article]:
        """Parse a single RSS feed and return articles."""
        articles = []

        try:
            feed = feedparser.parse(feed_url)

            if feed.bozo and feed.bozo_exception:
                logger.warning(f"Feed parsing issue for {feed_name}: {feed.bozo_exception}")

            for entry in feed.entries:
                try:
                    article = self._parse_entry(entry, feed_name)
                    if article:
                        articles.append(article)
                except Exception as e:
                    logger.warning(f"Failed to parse entry from {feed_name}: {e}")

            logger.info(f"Parsed {len(articles)} articles from {feed_name}")

        except Exception as e:
            logger.error(f"Failed to fetch feed {feed_name}: {e}")

        return articles

    def _parse_entry(self, entry: dict, source_name: str) -> Optional[Article]:
        """Parse a single feed entry into an Article."""
        # Get URL
        url = entry.get("link", "")
        if not url:
            return None

        # Check for duplicates
        if url in self._seen_urls:
            return None
        self._seen_urls.add(url)

        # Get title
        title = entry.get("title", "").strip()
        if not title:
            return None

        # Get content/description
        content = None
        description = None

        if "content" in entry and entry.content:
            content = entry.content[0].get("value", "")
        if "summary" in entry:
            description = entry.get("summary", "")
        elif "description" in entry:
            description = entry.get("description", "")

        # Parse publication date
        pub_date = datetime.utcnow()
        if "published_parsed" in entry and entry.published_parsed:
            try:
                pub_date = datetime.fromtimestamp(mktime(entry.published_parsed))
            except (TypeError, ValueError):
                pass
        elif "updated_parsed" in entry and entry.updated_parsed:
            try:
                pub_date = datetime.fromtimestamp(mktime(entry.updated_parsed))
            except (TypeError, ValueError):
                pass

        # Get author
        author = entry.get("author", entry.get("dc_creator"))

        # Get image if available
        image_url = None
        if "media_content" in entry and entry.media_content:
            image_url = entry.media_content[0].get("url")
        elif "enclosures" in entry and entry.enclosures:
            for enc in entry.enclosures:
                if enc.get("type", "").startswith("image/"):
                    image_url = enc.get("href")
                    break

        return Article(
            title=title,
            content=content,
            description=description,
            url=url,
            source_name=source_name,
            source_type=ArticleSource.RSS,
            author=author,
            published_at=pub_date,
            image_url=image_url
        )

    def fetch_all_feeds(self) -> List[Article]:
        """Fetch articles from all configured feeds."""
        all_articles = []
        self._seen_urls.clear()  # Reset deduplication

        for feed_name, feed_url in self.feeds.items():
            articles = self.parse_feed(feed_name, feed_url)
            all_articles.extend(articles)

        # Final deduplication by generated ID
        seen_ids = set()
        unique_articles = []
        for article in all_articles:
            if article.id not in seen_ids:
                seen_ids.add(article.id)
                unique_articles.append(article)

        logger.info(f"Fetched {len(unique_articles)} unique articles from {len(self.feeds)} feeds")
        return unique_articles

    def fetch_and_store(self) -> int:
        """Fetch from all feeds and store new articles in Redis."""
        articles = self.fetch_all_feeds()
        redis_client = get_redis_client()

        stored_count = 0
        for article in articles:
            if redis_client.article_exists(article.id):
                continue

            if redis_client.store_article(article.id, article.to_dict()):
                stored_count += 1

        logger.info(f"Stored {stored_count} new articles from RSS feeds")
        return stored_count

    def add_feed(self, name: str, url: str):
        """Add a new feed to the parser."""
        self.feeds[name] = url
        logger.info(f"Added feed: {name}")

    def remove_feed(self, name: str):
        """Remove a feed from the parser."""
        if name in self.feeds:
            del self.feeds[name]
            logger.info(f"Removed feed: {name}")

    def list_feeds(self) -> Dict[str, str]:
        """List all configured feeds."""
        return self.feeds.copy()
