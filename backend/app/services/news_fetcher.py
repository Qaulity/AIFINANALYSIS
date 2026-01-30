"""NewsAPI integration for fetching financial news."""
import time
from datetime import datetime, timedelta
from typing import List, Optional
from newsapi import NewsApiClient
from newsapi.newsapi_exception import NewsAPIException
from loguru import logger

from ..config import get_settings
from ..models import Article, ArticleSource
from ..utils import get_redis_client


class NewsFetcher:
    """Fetches news articles from NewsAPI with rate limiting."""

    # Financial/business keywords for filtering
    FINANCIAL_KEYWORDS = [
        "stock", "market", "trading", "investor", "earnings",
        "nasdaq", "dow", "s&p", "cryptocurrency", "bitcoin",
        "federal reserve", "interest rate", "inflation", "gdp",
        "merger", "acquisition", "ipo", "dividend"
    ]

    # Business news sources
    BUSINESS_SOURCES = [
        "bloomberg", "reuters", "the-wall-street-journal",
        "financial-times", "cnbc", "fortune", "business-insider"
    ]

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.NEWSAPI_KEY
        self.rate_limit = settings.NEWSAPI_RATE_LIMIT
        self._client: Optional[NewsApiClient] = None
        self._request_count = 0
        self._last_reset = datetime.utcnow()

    @property
    def client(self) -> NewsApiClient:
        """Lazy initialization of NewsAPI client."""
        if self._client is None:
            if not self.api_key:
                raise ValueError("NEWSAPI_KEY environment variable is not set")
            self._client = NewsApiClient(api_key=self.api_key)
        return self._client

    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits."""
        now = datetime.utcnow()

        # Reset counter daily
        if (now - self._last_reset).days >= 1:
            self._request_count = 0
            self._last_reset = now

        if self._request_count >= self.rate_limit:
            logger.warning("NewsAPI rate limit reached for today")
            return False

        return True

    def _increment_request_count(self):
        """Increment the request counter."""
        self._request_count += 1

    def fetch_top_headlines(
        self,
        category: str = "business",
        country: str = "us",
        page_size: int = 20
    ) -> List[Article]:
        """Fetch top business headlines."""
        if not self._check_rate_limit():
            return []

        try:
            self._increment_request_count()
            response = self.client.get_top_headlines(
                category=category,
                country=country,
                page_size=page_size
            )

            if response["status"] != "ok":
                logger.error(f"NewsAPI error: {response.get('message', 'Unknown error')}")
                return []

            return self._parse_articles(response["articles"])

        except NewsAPIException as e:
            logger.error(f"NewsAPI exception: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching headlines: {e}")
            return []

    def fetch_everything(
        self,
        query: Optional[str] = None,
        sources: Optional[List[str]] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        page_size: int = 20,
        page: int = 1
    ) -> List[Article]:
        """Fetch articles matching query or from specific sources."""
        if not self._check_rate_limit():
            return []

        try:
            self._increment_request_count()

            # Default to last 7 days if no dates specified
            if from_date is None:
                from_date = datetime.utcnow() - timedelta(days=7)
            if to_date is None:
                to_date = datetime.utcnow()

            params = {
                "from_param": from_date.strftime("%Y-%m-%d"),
                "to": to_date.strftime("%Y-%m-%d"),
                "page_size": page_size,
                "page": page,
                "language": "en",
                "sort_by": "publishedAt"
            }

            if query:
                params["q"] = query
            if sources:
                params["sources"] = ",".join(sources)

            response = self.client.get_everything(**params)

            if response["status"] != "ok":
                logger.error(f"NewsAPI error: {response.get('message', 'Unknown error')}")
                return []

            logger.info(f"Fetched {len(response['articles'])} articles from NewsAPI")
            return self._parse_articles(response["articles"])

        except NewsAPIException as e:
            logger.error(f"NewsAPI exception: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching articles: {e}")
            return []

    def fetch_financial_news(self, page_size: int = 50) -> List[Article]:
        """Fetch financial news using predefined keywords and sources."""
        articles = []

        # Fetch from business sources
        source_articles = self.fetch_everything(
            sources=self.BUSINESS_SOURCES[:5],  # Limit sources per request
            page_size=min(page_size, 100)
        )
        articles.extend(source_articles)

        # Also search for financial keywords
        keyword_articles = self.fetch_everything(
            query=" OR ".join(self.FINANCIAL_KEYWORDS[:5]),
            page_size=min(page_size, 100)
        )
        articles.extend(keyword_articles)

        # Deduplicate by URL
        seen_urls = set()
        unique_articles = []
        for article in articles:
            if article.url not in seen_urls:
                seen_urls.add(article.url)
                unique_articles.append(article)

        logger.info(f"Fetched {len(unique_articles)} unique financial articles")
        return unique_articles

    def _parse_articles(self, raw_articles: List[dict]) -> List[Article]:
        """Parse raw API response into Article models."""
        articles = []

        for raw in raw_articles:
            try:
                # Parse published date
                pub_date = raw.get("publishedAt")
                if pub_date:
                    if isinstance(pub_date, str):
                        pub_date = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                else:
                    pub_date = datetime.utcnow()

                article = Article(
                    title=raw.get("title", ""),
                    content=raw.get("content"),
                    description=raw.get("description"),
                    url=raw.get("url", ""),
                    source_name=raw.get("source", {}).get("name", "Unknown"),
                    source_type=ArticleSource.NEWSAPI,
                    author=raw.get("author"),
                    published_at=pub_date,
                    image_url=raw.get("urlToImage")
                )

                # Skip articles with minimal content
                if not article.title or not article.url:
                    continue

                articles.append(article)

            except Exception as e:
                logger.warning(f"Failed to parse article: {e}")
                continue

        return articles

    def fetch_and_store(self, page_size: int = 50) -> int:
        """Fetch financial news and store in Redis. Returns count of new articles."""
        articles = self.fetch_financial_news(page_size=page_size)
        redis_client = get_redis_client()

        stored_count = 0
        for article in articles:
            # Skip if already exists
            if redis_client.article_exists(article.id):
                continue

            if redis_client.store_article(article.id, article.to_dict()):
                stored_count += 1

        logger.info(f"Stored {stored_count} new articles in Redis")
        return stored_count
