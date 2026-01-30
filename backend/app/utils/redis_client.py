"""Redis client utilities for data storage and caching."""
import json
from typing import Optional, Any, List
from datetime import datetime, timedelta
import redis
from loguru import logger

from ..config import get_settings


class RedisClient:
    """Redis client wrapper with convenience methods for the news pipeline."""

    def __init__(self, redis_instance: redis.Redis):
        self.redis = redis_instance

    # Key prefixes for organization
    ARTICLE_PREFIX = "article:"
    ARTICLE_LIST = "articles:all"
    SENTIMENT_PREFIX = "sentiment:"
    TICKER_PREFIX = "ticker:"
    TREND_PREFIX = "trend:"
    CACHE_PREFIX = "cache:"

    def ping(self) -> bool:
        """Check Redis connection."""
        try:
            return self.redis.ping()
        except redis.ConnectionError:
            return False

    # Article operations
    def store_article(self, article_id: str, article_data: dict, ttl_days: int = 30) -> bool:
        """Store an article with optional TTL."""
        try:
            key = f"{self.ARTICLE_PREFIX}{article_id}"
            article_data["stored_at"] = datetime.utcnow().isoformat()

            # Store article data
            self.redis.set(key, json.dumps(article_data))

            # Set TTL
            if ttl_days > 0:
                self.redis.expire(key, timedelta(days=ttl_days))

            # Add to sorted set for listing (score by publish date)
            pub_date = article_data.get("published_at", datetime.utcnow().isoformat())
            score = datetime.fromisoformat(pub_date.replace("Z", "+00:00")).timestamp()
            self.redis.zadd(self.ARTICLE_LIST, {article_id: score})

            return True
        except Exception as e:
            logger.error(f"Failed to store article {article_id}: {e}")
            return False

    def get_article(self, article_id: str) -> Optional[dict]:
        """Retrieve an article by ID."""
        try:
            key = f"{self.ARTICLE_PREFIX}{article_id}"
            data = self.redis.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Failed to get article {article_id}: {e}")
            return None

    def get_articles(
        self,
        offset: int = 0,
        limit: int = 20,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[dict]:
        """Get paginated list of articles, newest first."""
        try:
            # Get article IDs from sorted set
            if start_date and end_date:
                min_score = start_date.timestamp()
                max_score = end_date.timestamp()
                article_ids = self.redis.zrevrangebyscore(
                    self.ARTICLE_LIST, max_score, min_score,
                    start=offset, num=limit
                )
            else:
                article_ids = self.redis.zrevrange(
                    self.ARTICLE_LIST, offset, offset + limit - 1
                )

            # Fetch article data
            articles = []
            for aid in article_ids:
                article = self.get_article(aid.decode() if isinstance(aid, bytes) else aid)
                if article:
                    article["id"] = aid.decode() if isinstance(aid, bytes) else aid
                    articles.append(article)

            return articles
        except Exception as e:
            logger.error(f"Failed to get articles: {e}")
            return []

    def article_exists(self, article_id: str) -> bool:
        """Check if an article already exists."""
        return self.redis.exists(f"{self.ARTICLE_PREFIX}{article_id}") > 0

    def get_article_count(self) -> int:
        """Get total number of stored articles."""
        return self.redis.zcard(self.ARTICLE_LIST)

    # Sentiment operations
    def store_sentiment(self, article_id: str, sentiment_data: dict) -> bool:
        """Store sentiment analysis results for an article."""
        try:
            key = f"{self.SENTIMENT_PREFIX}{article_id}"
            self.redis.set(key, json.dumps(sentiment_data))
            return True
        except Exception as e:
            logger.error(f"Failed to store sentiment for {article_id}: {e}")
            return False

    def get_sentiment(self, article_id: str) -> Optional[dict]:
        """Get sentiment data for an article."""
        try:
            key = f"{self.SENTIMENT_PREFIX}{article_id}"
            data = self.redis.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Failed to get sentiment for {article_id}: {e}")
            return None

    # Ticker operations
    def add_ticker_mention(self, ticker: str, article_id: str, sentiment_score: float) -> bool:
        """Track a ticker mention with its sentiment."""
        try:
            key = f"{self.TICKER_PREFIX}{ticker}:articles"
            self.redis.zadd(key, {article_id: sentiment_score})

            # Update ticker stats
            stats_key = f"{self.TICKER_PREFIX}{ticker}:stats"
            self.redis.hincrby(stats_key, "mention_count", 1)

            return True
        except Exception as e:
            logger.error(f"Failed to add ticker mention {ticker}: {e}")
            return False

    def get_ticker_sentiment(self, ticker: str, limit: int = 100) -> dict:
        """Get sentiment summary for a ticker."""
        try:
            key = f"{self.TICKER_PREFIX}{ticker}:articles"
            mentions = self.redis.zrange(key, 0, limit - 1, withscores=True)

            if not mentions:
                return {"ticker": ticker, "mentions": 0, "avg_sentiment": 0.0}

            sentiments = [score for _, score in mentions]
            avg_sentiment = sum(sentiments) / len(sentiments)

            return {
                "ticker": ticker,
                "mentions": len(mentions),
                "avg_sentiment": round(avg_sentiment, 4),
                "recent_sentiments": sentiments[-10:]
            }
        except Exception as e:
            logger.error(f"Failed to get ticker sentiment for {ticker}: {e}")
            return {"ticker": ticker, "mentions": 0, "avg_sentiment": 0.0}

    # Cache operations
    def cache_set(self, key: str, value: Any, ttl_seconds: int = 300) -> bool:
        """Set a cached value with TTL."""
        try:
            cache_key = f"{self.CACHE_PREFIX}{key}"
            self.redis.setex(cache_key, ttl_seconds, json.dumps(value))
            return True
        except Exception as e:
            logger.error(f"Failed to set cache {key}: {e}")
            return False

    def cache_get(self, key: str) -> Optional[Any]:
        """Get a cached value."""
        try:
            cache_key = f"{self.CACHE_PREFIX}{key}"
            data = self.redis.get(cache_key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Failed to get cache {key}: {e}")
            return None


_redis_client: Optional[RedisClient] = None


def get_redis_client() -> RedisClient:
    """Get or create the Redis client singleton."""
    global _redis_client

    if _redis_client is None:
        settings = get_settings()
        redis_instance = redis.from_url(settings.redis_url, decode_responses=False)
        _redis_client = RedisClient(redis_instance)
        logger.info(f"Connected to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}")

    return _redis_client
