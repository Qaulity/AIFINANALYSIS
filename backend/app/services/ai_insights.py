"""AI insights service - generates market analysis via Claude, caches to Redis."""
import json
import threading
from datetime import datetime, timedelta
from typing import Optional, Any
from loguru import logger

from ..config import get_settings
from ..utils import get_redis_client


class AIInsightsService:
    """AI market insights service. Singleton."""

    _instance: Optional["AIInsightsService"] = None
    _lock = threading.Lock()

    # redis keys
    CACHE_KEY = "ai_insights"
    RATE_LIMIT_KEY = "ai_insights:rate_limit"
    GENERATING_KEY = "ai_insights:generating"

    RATE_LIMIT_COOLDOWN = 60  # manual refresh cooldown in seconds

    def __new__(cls) -> "AIInsightsService":
        """Return existing instance or create new one."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Init service config. Only runs once."""
        if self._initialized:
            return

        self.settings = get_settings()
        self.redis = get_redis_client()
        self._client = None
        self._generation_lock = threading.Lock()
        self._initialized = True

    @property
    def client(self):
        """Get Anthropic client. Lazy loaded on first use."""
        if self._client is None and self.settings.ANTHROPIC_API_KEY:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.settings.ANTHROPIC_API_KEY)
            except ImportError:
                logger.error("anthropic package not installed")
            except Exception as e:
                logger.error(f"Failed to initialize Anthropic client: {e}")
        return self._client

    def is_configured(self) -> bool:
        """Check if API key is set and feature enabled."""
        return bool(self.settings.ANTHROPIC_API_KEY) and self.settings.AI_INSIGHTS_ENABLED

    def gather_context_data(self) -> dict:
        """Pull last 7 days of articles from Redis and calculate stats for Claude."""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)

        articles = self.redis.get_articles(limit=200, start_date=start_date, end_date=end_date)

        if not articles:
            return {"error": "No articles available"}

        sentiment_scores = []
        ticker_data = {}
        source_counts = {}

        for article in articles:
            sentiment = article.get("sentiment", {})
            if sentiment and sentiment.get("score") is not None:
                sentiment_scores.append(sentiment["score"])

            # aggregate ticker mentions and sentiment
            for ticker in article.get("tickers", []):
                if ticker not in ticker_data:
                    ticker_data[ticker] = {
                        "mentions": 0,
                        "sentiment_sum": 0,
                        "headlines": []
                    }
                ticker_data[ticker]["mentions"] += 1
                if sentiment and sentiment.get("score") is not None:
                    ticker_data[ticker]["sentiment_sum"] += sentiment["score"]
                if len(ticker_data[ticker]["headlines"]) < 3:  # keep max 3 headlines per ticker
                    ticker_data[ticker]["headlines"].append(article.get("title", ""))

            source = article.get("source_name", "Unknown")
            source_counts[source] = source_counts.get(source, 0) + 1

        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0

        # determine market mood from avg sentiment
        if avg_sentiment > 0.1:
            market_mood = "bullish"
        elif avg_sentiment < -0.1:
            market_mood = "bearish"
        else:
            market_mood = "neutral"

        # top 10 tickers by mention count
        top_tickers = sorted(
            [
                {
                    "ticker": ticker,
                    "mentions": data["mentions"],
                    "avg_sentiment": round(data["sentiment_sum"] / data["mentions"], 4) if data["mentions"] > 0 else 0,
                    "headlines": data["headlines"]
                }
                for ticker, data in ticker_data.items()
            ],
            key=lambda x: x["mentions"],
            reverse=True
        )[:10]

        # top 5 sources by article count
        top_sources = sorted(
            [{"name": k, "count": v} for k, v in source_counts.items()],
            key=lambda x: x["count"],
            reverse=True
        )[:5]

        return {
            "article_count": len(articles),
            "avg_sentiment": round(avg_sentiment, 4),
            "market_mood": market_mood,
            "top_tickers": top_tickers,
            "top_sources": top_sources,
            "sentiment_distribution": {
                "positive": sum(1 for s in sentiment_scores if s > 0.1),
                "negative": sum(1 for s in sentiment_scores if s < -0.1),
                "neutral": sum(1 for s in sentiment_scores if -0.1 <= s <= 0.1)
            },
            "data_timestamp": datetime.utcnow().isoformat()
        }

    def _build_prompt(self, context: dict) -> str:
        """Build the Claude prompt with article stats and expected JSON format."""
        tickers_info = "\n".join([
            f"- {t['ticker']}: {t['mentions']} mentions, sentiment {t['avg_sentiment']:.2f}, headlines: {', '.join(t['headlines'][:2])}"
            for t in context.get("top_tickers", [])[:8]
        ])

        sources_info = "\n".join([
            f"- {s['name']}: {s['count']} articles"
            for s in context.get("top_sources", [])[:5]
        ])

        return f"""You are a financial market analyst. Based on the following news data from the past 7 days, provide market insights.

DATA SUMMARY:
- Total articles analyzed: {context.get('article_count', 0)}
- Average sentiment score: {context.get('avg_sentiment', 0):.4f} (scale: -1 to 1)
- Current market mood: {context.get('market_mood', 'neutral')}
- Sentiment distribution: {context.get('sentiment_distribution', {})}

TOP MENTIONED TICKERS:
{tickers_info or "No specific tickers identified"}

TOP NEWS SOURCES:
{sources_info or "Various sources"}

Provide your analysis in the following JSON format (respond ONLY with valid JSON, no markdown):
{{
    "market_summary": "A 2-3 sentence overview of the current market sentiment and conditions based on news coverage.",
    "trend_alerts": [
        {{
            "ticker": "SYMBOL",
            "alert_type": "bullish|bearish|volatile|momentum",
            "message": "Brief explanation of the trend signal"
        }}
    ],
    "sector_analysis": "Brief analysis of which sectors appear to be receiving positive or negative coverage.",
    "key_observations": [
        "First key observation about market conditions",
        "Second key observation",
        "Third key observation"
    ],
    "sentiment_outlook": "A brief 1-2 sentence outlook on near-term market sentiment direction."
}}

Keep the analysis concise, actionable, and based solely on the provided news data. Include 2-4 trend alerts for the most significant tickers."""

    def generate_insights(self, force: bool = False) -> Optional[dict]:
        """Call Claude API to generate insights. Returns None on failure."""
        if not self.is_configured():
            logger.warning("AI insights service not configured")
            return None

        # skip if already generating
        if not force:
            is_generating = self.redis.cache_get(self.GENERATING_KEY)
            if is_generating:
                logger.info("AI insights generation already in progress")
                return self.get_cached_insights()

        # try to acquire lock, return cached if busy
        if not self._generation_lock.acquire(blocking=False):
            logger.info("Could not acquire generation lock")
            return self.get_cached_insights()

        try:
            self.redis.cache_set(self.GENERATING_KEY, True, ttl_seconds=120)

            context = self.gather_context_data()
            if "error" in context:
                logger.warning(f"Cannot generate insights: {context['error']}")
                return None

            if context.get("article_count", 0) < 5:  # need at least 5 articles
                logger.warning("Insufficient articles for AI insights generation")
                return None

            prompt = self._build_prompt(context)
            logger.info("Calling Claude API for market insights...")
            response = self.client.messages.create(
                model=self.settings.AI_INSIGHTS_MODEL,
                max_tokens=self.settings.AI_INSIGHTS_MAX_TOKENS,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response_text = response.content[0].text.strip()

            # strip markdown code blocks if present
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                json_lines = []
                in_json = False
                for line in lines:
                    if line.startswith("```") and not in_json:
                        in_json = True
                        continue
                    elif line.startswith("```") and in_json:
                        break
                    elif in_json:
                        json_lines.append(line)
                response_text = "\n".join(json_lines)

            insights_data = json.loads(response_text)

            insights = {
                "market_summary": insights_data.get("market_summary", ""),
                "trend_alerts": insights_data.get("trend_alerts", []),
                "sector_analysis": insights_data.get("sector_analysis", ""),
                "key_observations": insights_data.get("key_observations", []),
                "sentiment_outlook": insights_data.get("sentiment_outlook", ""),
                "generated_at": datetime.utcnow().isoformat(),
                "data_timestamp": context.get("data_timestamp"),
                "is_stale": False
            }

            self.redis.cache_set(
                self.CACHE_KEY,
                insights,
                ttl_seconds=self.settings.AI_INSIGHTS_CACHE_TTL
            )

            logger.info("AI insights generated successfully")
            return insights

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response as JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to generate AI insights: {e}")
            return None
        finally:
            self.redis.cache_set(self.GENERATING_KEY, False, ttl_seconds=1)
            self._generation_lock.release()

    def get_cached_insights(self) -> Optional[dict]:
        """Get insights from cache. Marks as stale if older than generation interval."""
        insights = self.redis.cache_get(self.CACHE_KEY)
        if insights:
            generated_at = insights.get("generated_at")
            if generated_at:
                try:
                    gen_time = datetime.fromisoformat(generated_at)
                    age_minutes = (datetime.utcnow() - gen_time).total_seconds() / 60
                    insights["is_stale"] = age_minutes > self.settings.AI_INSIGHTS_GENERATION_INTERVAL
                except Exception:
                    insights["is_stale"] = True
        return insights

    def get_or_generate(self, force: bool = False) -> dict:
        """Main API method. Returns cached or generates new, handles rate limiting."""
        if force:
            rate_limited = self.redis.cache_get(self.RATE_LIMIT_KEY)
            if rate_limited:
                remaining = rate_limited.get("retry_after", self.RATE_LIMIT_COOLDOWN)
                return {
                    "status": "rate_limited",
                    "insights": self.get_cached_insights(),
                    "retry_after": remaining,
                    "is_generating": False
                }

        cached = self.get_cached_insights()

        if cached and not force:
            is_generating = self.redis.cache_get(self.GENERATING_KEY)
            return {
                "status": "success",
                "insights": cached,
                "is_generating": bool(is_generating)
            }

        if force:  # set rate limit on manual refresh
            self.redis.cache_set(
                self.RATE_LIMIT_KEY,
                {"retry_after": self.RATE_LIMIT_COOLDOWN},
                ttl_seconds=self.RATE_LIMIT_COOLDOWN
            )

        insights = self.generate_insights(force=force)

        if insights:
            return {
                "status": "success",
                "insights": insights,
                "is_generating": False
            }
        elif cached:  # generation failed, fall back to cache
            return {
                "status": "success",
                "insights": cached,
                "is_generating": False,
                "warning": "Using cached insights - generation failed"
            }
        else:
            return {
                "status": "unavailable",
                "insights": None,
                "is_generating": False,
                "message": "No insights available"
            }

    def get_status(self) -> dict:
        """Return service status for status endpoint."""
        cached = self.get_cached_insights()
        is_generating = bool(self.redis.cache_get(self.GENERATING_KEY))
        rate_limited = self.redis.cache_get(self.RATE_LIMIT_KEY)

        return {
            "configured": self.is_configured(),
            "enabled": self.settings.AI_INSIGHTS_ENABLED,
            "has_cached_insights": cached is not None,
            "is_generating": is_generating,
            "is_rate_limited": rate_limited is not None,
            "rate_limit_remaining": rate_limited.get("retry_after") if rate_limited else None,
            "generation_interval_minutes": self.settings.AI_INSIGHTS_GENERATION_INTERVAL,
            "cache_ttl_seconds": self.settings.AI_INSIGHTS_CACHE_TTL,
            "last_generated": cached.get("generated_at") if cached else None
        }


_ai_insights_service: Optional[AIInsightsService] = None


def get_ai_insights_service() -> AIInsightsService:
    """Get singleton instance."""
    global _ai_insights_service
    if _ai_insights_service is None:
        _ai_insights_service = AIInsightsService()
    return _ai_insights_service
