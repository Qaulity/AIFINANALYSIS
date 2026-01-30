"""App config - loads from environment variables and .env file."""
import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """All app settings. Values come from environment variables or .env file."""

    # General
    APP_NAME: str = "Financial News Analysis"
    DEBUG: bool = False

    # Redis connection
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""

    # News API - for fetching articles
    NEWSAPI_KEY: str = ""

    # Alpha Vantage - for stock data (optional, limited free tier)
    ALPHAVANTAGE_KEY: str = ""

    # Finnhub - for stock symbol search (free, 60 req/min)
    FINNHUB_API_KEY: str = ""

    # Claude AI - for generating market insights
    ANTHROPIC_API_KEY: str = ""
    AI_INSIGHTS_ENABLED: bool = True
    AI_INSIGHTS_GENERATION_INTERVAL: int = 15  # how often to generate (minutes)
    AI_INSIGHTS_CACHE_TTL: int = 1200  # how long to keep cached (seconds)
    AI_INSIGHTS_MODEL: str = "claude-sonnet-4-20250514"
    AI_INSIGHTS_MAX_TOKENS: int = 1500

    # Rate limiting
    NEWSAPI_RATE_LIMIT: int = 100  # requests per day

    # NLP/ML settings
    SENTIMENT_MODEL: str = "finbert"  # finbert or textblob
    ENABLE_TOPIC_MODELING: bool = True
    USE_GPU: bool = True
    NLP_BATCH_SIZE: int = 16

    @property
    def redis_url(self) -> str:
        """Build Redis connection URL from individual settings."""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """
    Get settings instance.
    Cached so we only load once - call get_settings.cache_clear() to reload.
    """
    return Settings()
