"""Background worker - scheduled jobs for news fetch, sentiment analysis, AI insights."""
import time
import schedule
from loguru import logger

from .services import NewsFetcher, SentimentAnalyzer, RSSParser, get_ai_insights_service
from .config import get_settings


def fetch_news_job():
    """Fetch news from NewsAPI and RSS feeds."""
    logger.info("Starting scheduled news fetch...")

    try:
        fetcher = NewsFetcher()
        newsapi_count = fetcher.fetch_and_store(page_size=50)
        logger.info(f"NewsAPI: fetched {newsapi_count} new articles")
    except Exception as e:
        logger.error(f"NewsAPI fetch failed: {e}")

    # Fetch from RSS feeds
    try:
        parser = RSSParser()
        rss_count = parser.fetch_and_store()
        logger.info(f"RSS: fetched {rss_count} new articles")
    except Exception as e:
        logger.error(f"RSS fetch failed: {e}")


def analyze_sentiment_job():
    """Run FinBERT sentiment analysis on unprocessed articles."""
    logger.info("Starting scheduled sentiment analysis...")

    try:
        analyzer = SentimentAnalyzer()
        processed = analyzer.process_stored_articles(limit=100)
        logger.info(f"Processed sentiment for {processed} articles")
    except Exception as e:
        logger.error(f"Sentiment analysis failed: {e}")


def generate_ai_insights_job():
    """Generate market insights via Claude API."""
    settings = get_settings()

    if not settings.AI_INSIGHTS_ENABLED:
        logger.debug("AI insights generation is disabled")
        return

    if not settings.ANTHROPIC_API_KEY:
        logger.debug("AI insights skipped: ANTHROPIC_API_KEY not configured")
        return

    logger.info("Starting scheduled AI insights generation...")

    try:
        service = get_ai_insights_service()
        result = service.generate_insights(force=False)

        if result:
            logger.info("AI insights generated successfully")
        else:
            logger.warning("AI insights generation returned no results")
    except Exception as e:
        logger.error(f"AI insights generation failed: {e}")


def run_worker():
    """Main entry point - sets up scheduled jobs and runs loop."""
    settings = get_settings()
    logger.info(f"Starting {settings.APP_NAME} background worker...")

    # Schedule recurring jobs
    schedule.every(30).minutes.do(fetch_news_job)       # Fetch news every 30 min
    schedule.every(15).minutes.do(analyze_sentiment_job) # Analyze sentiment every 15 min

    # Schedule AI insights if enabled
    if settings.AI_INSIGHTS_ENABLED:
        schedule.every(settings.AI_INSIGHTS_GENERATION_INTERVAL).minutes.do(generate_ai_insights_job)
        logger.info(f"AI insights scheduled every {settings.AI_INSIGHTS_GENERATION_INTERVAL} minutes")

    # Run jobs immediately on startup
    logger.info("Running initial news fetch...")
    fetch_news_job()
    analyze_sentiment_job()

    # Generate initial AI insights if configured
    if settings.AI_INSIGHTS_ENABLED and settings.ANTHROPIC_API_KEY:
        logger.info("Running initial AI insights generation...")
        generate_ai_insights_job()

    # Main loop - check for pending jobs every minute
    logger.info("Worker started. Press Ctrl+C to stop.")
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    run_worker()
