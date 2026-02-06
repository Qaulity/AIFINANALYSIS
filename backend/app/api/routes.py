"""Flask API routes for the financial news platform."""
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from flask_restx import Api, Resource, fields, Namespace
from loguru import logger

from ..utils import get_redis_client
from ..services import NewsFetcher, SentimentAnalyzer, RSSParser, NLPPipeline, get_alpha_vantage_client, get_market_data_service, get_ai_insights_service
from ..models import Article

# Create Blueprint
api_bp = Blueprint("api", __name__, url_prefix="/api")

# Create API with Swagger documentation
api = Api(
    api_bp,
    version="1.0",
    title="Financial News Analysis API",
    description="REST API for financial news analysis with FinBERT sentiment, NER, and topic modeling",
    doc="/docs"
)

# Namespaces
articles_ns = Namespace("articles", description="Article operations")
trends_ns = Namespace("trends", description="Trend analysis")
tickers_ns = Namespace("tickers", description="Ticker sentiment")
insights_ns = Namespace("insights", description="Dashboard insights")
nlp_ns = Namespace("nlp", description="Advanced NLP analysis")
ai_ns = Namespace("ai", description="AI-powered market insights")
stocks_ns = Namespace("stocks", description="Stock market data from Alpha Vantage")
market_ns = Namespace("market", description="Market data from Yahoo Finance")

api.add_namespace(articles_ns)
api.add_namespace(trends_ns)
api.add_namespace(tickers_ns)
api.add_namespace(insights_ns)
api.add_namespace(nlp_ns)
api.add_namespace(stocks_ns)
api.add_namespace(market_ns)
api.add_namespace(ai_ns)

# Singleton NLP pipeline (heavy models, load once)
_nlp_pipeline = None

def get_nlp_pipeline():
    """Get or create the NLP pipeline singleton."""
    global _nlp_pipeline
    if _nlp_pipeline is None:
        _nlp_pipeline = NLPPipeline(use_gpu=True, enable_topics=True)
    return _nlp_pipeline

# Models for Swagger documentation
sentiment_model = api.model("Sentiment", {
    "score": fields.Float(description="Sentiment score from -1 to 1"),
    "label": fields.String(description="Sentiment label"),
    "confidence": fields.Float(description="Confidence score"),
    "model": fields.String(description="Model used")
})

article_model = api.model("Article", {
    "id": fields.String(description="Unique article ID"),
    "title": fields.String(description="Article title"),
    "description": fields.String(description="Article summary"),
    "url": fields.String(description="Original article URL"),
    "source_name": fields.String(description="News source"),
    "source_type": fields.String(description="Source type (newsapi, rss, scraper)"),
    "author": fields.String(description="Article author"),
    "published_at": fields.String(description="Publication date"),
    "image_url": fields.String(description="Featured image URL"),
    "sentiment": fields.Nested(sentiment_model),
    "tickers": fields.List(fields.String, description="Mentioned tickers"),
    "topics": fields.List(fields.String, description="Topic labels")
})

article_list_model = api.model("ArticleList", {
    "articles": fields.List(fields.Nested(article_model)),
    "total": fields.Integer(description="Total article count"),
    "page": fields.Integer(description="Current page"),
    "per_page": fields.Integer(description="Articles per page")
})


@articles_ns.route("")
class ArticleList(Resource):
    """Article list endpoint."""

    @articles_ns.doc("list_articles")
    @articles_ns.param("page", "Page number", type=int, default=1)
    @articles_ns.param("per_page", "Articles per page", type=int, default=20)
    @articles_ns.param("sentiment", "Filter by sentiment (positive, negative, neutral)")
    @articles_ns.param("source", "Filter by source name")
    @articles_ns.param("ticker", "Filter by ticker symbol")
    @articles_ns.param("keyword", "Search keywords in title and description (supports multiple words)")
    @articles_ns.param("days", "Articles from last N days", type=int, default=7)
    @articles_ns.marshal_with(article_list_model)
    def get(self):
        """Get list of articles with optional filtering."""
        redis_client = get_redis_client()

        # Parse parameters
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)
        sentiment_filter = request.args.get("sentiment")
        source_filter = request.args.get("source")
        ticker_filter = request.args.get("ticker")
        keyword_filter = request.args.get("keyword")
        days = request.args.get("days", 7, type=int)

        # Calculate offset
        offset = (page - 1) * per_page

        # Date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # Get articles - fetch more when filtering by keyword to ensure enough results
        fetch_limit = per_page * 10 if keyword_filter else per_page * 2
        articles = redis_client.get_articles(
            offset=offset,
            limit=fetch_limit,
            start_date=start_date,
            end_date=end_date
        )

        # Prepare keyword search terms (case-insensitive)
        keyword_terms = []
        if keyword_filter:
            # Support both space-separated and comma-separated keywords
            keyword_filter = keyword_filter.strip()
            if keyword_filter:
                keyword_terms = [term.strip().lower() for term in keyword_filter.replace(",", " ").split() if term.strip()]

        # Apply filters
        filtered = []
        for article in articles:
            # Sentiment filter
            if sentiment_filter:
                sentiment = article.get("sentiment", {})
                if sentiment.get("label") != sentiment_filter:
                    continue

            # Source filter
            if source_filter:
                if source_filter.lower() not in article.get("source_name", "").lower():
                    continue

            # Ticker filter
            if ticker_filter:
                if ticker_filter.upper() not in [t.upper() for t in article.get("tickers", [])]:
                    continue

            # Keyword filter - search in title and description
            if keyword_terms:
                title = (article.get("title") or "").lower()
                description = (article.get("description") or "").lower()
                searchable_text = f"{title} {description}"

                # Check if ALL keyword terms are present (AND logic)
                if not all(term in searchable_text for term in keyword_terms):
                    continue

            filtered.append(article)

            if len(filtered) >= per_page:
                break

        return {
            "articles": filtered,
            "total": redis_client.get_article_count(),
            "page": page,
            "per_page": per_page
        }


@articles_ns.route("/<string:article_id>")
class ArticleDetail(Resource):
    """Single article endpoint."""

    @articles_ns.doc("get_article")
    @articles_ns.marshal_with(article_model)
    def get(self, article_id):
        """Get a single article by ID."""
        redis_client = get_redis_client()
        article = redis_client.get_article(article_id)

        if not article:
            articles_ns.abort(404, f"Article {article_id} not found")

        article["id"] = article_id
        return article


@articles_ns.route("/fetch")
class ArticleFetch(Resource):
    """Trigger article fetching."""

    @articles_ns.doc("fetch_articles")
    @articles_ns.param("source", "Source to fetch from (newsapi, rss, all)", default="all")
    def post(self):
        """Trigger fetching of new articles."""
        source = request.args.get("source", "all")

        results = {"fetched": 0, "sources": []}

        try:
            if source in ("newsapi", "all"):
                fetcher = NewsFetcher()
                count = fetcher.fetch_and_store()
                results["fetched"] += count
                results["sources"].append({"name": "newsapi", "count": count})

            if source in ("rss", "all"):
                parser = RSSParser()
                count = parser.fetch_and_store()
                results["fetched"] += count
                results["sources"].append({"name": "rss", "count": count})

            return {"status": "success", **results}

        except Exception as e:
            logger.error(f"Fetch failed: {e}")
            return {"status": "error", "message": str(e)}, 500


@articles_ns.route("/analyze")
class ArticleAnalyze(Resource):
    """Trigger sentiment analysis."""

    @articles_ns.doc("analyze_articles")
    @articles_ns.param("limit", "Number of articles to analyze", type=int, default=100)
    def post(self):
        """Trigger sentiment analysis on unprocessed articles."""
        limit = request.args.get("limit", 100, type=int)

        try:
            analyzer = SentimentAnalyzer()
            processed = analyzer.process_stored_articles(limit=limit)
            return {"status": "success", "processed": processed}
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return {"status": "error", "message": str(e)}, 500


@trends_ns.route("")
class TrendList(Resource):
    """Market trends from news analysis."""

    @trends_ns.doc("get_trends")
    @trends_ns.param("days", "Analysis period in days", type=int, default=7)
    def get(self):
        """Get current market trends from news analysis."""
        redis_client = get_redis_client()
        days = request.args.get("days", 7, type=int)

        # Check cache
        cache_key = f"trends:{days}d"
        cached = redis_client.cache_get(cache_key)
        if cached:
            return cached

        # Get recent articles
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        articles = redis_client.get_articles(
            limit=500,
            start_date=start_date,
            end_date=end_date
        )

        # Calculate trends
        sentiment_sum = 0
        sentiment_count = 0
        source_counts = {}
        ticker_mentions = {}

        for article in articles:
            # Aggregate sentiment
            sentiment = article.get("sentiment", {})
            if sentiment and sentiment.get("score") is not None:
                sentiment_sum += sentiment["score"]
                sentiment_count += 1

            # Count sources
            source = article.get("source_name", "Unknown")
            source_counts[source] = source_counts.get(source, 0) + 1

            # Count ticker mentions
            for ticker in article.get("tickers", []):
                if ticker not in ticker_mentions:
                    ticker_mentions[ticker] = {"count": 0, "sentiment_sum": 0}
                ticker_mentions[ticker]["count"] += 1
                if sentiment and sentiment.get("score") is not None:
                    ticker_mentions[ticker]["sentiment_sum"] += sentiment["score"]

        # Build response
        avg_sentiment = sentiment_sum / sentiment_count if sentiment_count > 0 else 0

        top_tickers = sorted(
            [
                {
                    "ticker": ticker,
                    "mentions": data["count"],
                    "avg_sentiment": round(data["sentiment_sum"] / data["count"], 4) if data["count"] > 0 else 0
                }
                for ticker, data in ticker_mentions.items()
            ],
            key=lambda x: x["mentions"],
            reverse=True
        )[:10]

        top_sources = sorted(
            [{"name": k, "count": v} for k, v in source_counts.items()],
            key=lambda x: x["count"],
            reverse=True
        )[:10]

        result = {
            "period_days": days,
            "total_articles": len(articles),
            "average_sentiment": round(avg_sentiment, 4),
            "market_mood": "bullish" if avg_sentiment > 0.1 else "bearish" if avg_sentiment < -0.1 else "neutral",
            "top_tickers": top_tickers,
            "top_sources": top_sources
        }

        # Cache for 5 minutes
        redis_client.cache_set(cache_key, result, ttl_seconds=300)

        return result


@tickers_ns.route("/<string:symbol>/sentiment")
class TickerSentiment(Resource):
    """Ticker sentiment over time."""

    @tickers_ns.doc("get_ticker_sentiment")
    @tickers_ns.param("days", "Analysis period in days", type=int, default=30)
    def get(self, symbol):
        """Get sentiment history for a specific ticker."""
        redis_client = get_redis_client()
        days = request.args.get("days", 30, type=int)

        # Get ticker data
        ticker_data = redis_client.get_ticker_sentiment(symbol.upper())

        # Get articles mentioning this ticker
        articles = redis_client.get_articles(limit=500)
        ticker_articles = [
            a for a in articles
            if symbol.upper() in [t.upper() for t in a.get("tickers", [])]
        ]

        # Group by day for trend
        daily_sentiment = {}
        for article in ticker_articles:
            pub_date = article.get("published_at", "")
            if pub_date:
                try:
                    date_key = pub_date[:10]  # YYYY-MM-DD
                    sentiment = article.get("sentiment", {}).get("score", 0)
                    if date_key not in daily_sentiment:
                        daily_sentiment[date_key] = {"sum": 0, "count": 0}
                    daily_sentiment[date_key]["sum"] += sentiment
                    daily_sentiment[date_key]["count"] += 1
                except Exception:
                    pass

        trend = [
            {
                "date": date,
                "avg_sentiment": round(data["sum"] / data["count"], 4),
                "article_count": data["count"]
            }
            for date, data in sorted(daily_sentiment.items())
        ]

        return {
            "ticker": symbol.upper(),
            "summary": ticker_data,
            "trend": trend[-days:],
            "recent_articles": ticker_articles[:10]
        }


@insights_ns.route("/summary")
class InsightsSummary(Resource):
    """Dashboard summary data."""

    @insights_ns.doc("get_summary")
    def get(self):
        """Get dashboard summary with key metrics."""
        redis_client = get_redis_client()

        # Check cache
        cached = redis_client.cache_get("insights:summary")
        if cached:
            return cached

        # Get article stats
        total_articles = redis_client.get_article_count()

        # Get recent articles for analysis
        today = datetime.utcnow()
        yesterday = today - timedelta(days=1)
        week_ago = today - timedelta(days=7)

        recent_articles = redis_client.get_articles(limit=200)

        # Calculate metrics
        today_count = sum(
            1 for a in recent_articles
            if a.get("published_at", "")[:10] == today.strftime("%Y-%m-%d")
        )

        sentiment_scores = [
            a.get("sentiment", {}).get("score", 0)
            for a in recent_articles
            if a.get("sentiment")
        ]
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0

        # Sentiment distribution
        positive = sum(1 for s in sentiment_scores if s > 0.1)
        negative = sum(1 for s in sentiment_scores if s < -0.1)
        neutral = len(sentiment_scores) - positive - negative

        result = {
            "total_articles": total_articles,
            "articles_today": today_count,
            "average_sentiment": round(avg_sentiment, 4),
            "sentiment_distribution": {
                "positive": positive,
                "negative": negative,
                "neutral": neutral
            },
            "market_mood": "bullish" if avg_sentiment > 0.1 else "bearish" if avg_sentiment < -0.1 else "neutral",
            "last_updated": datetime.utcnow().isoformat()
        }

        # Cache for 2 minutes
        redis_client.cache_set("insights:summary", result, ttl_seconds=120)

        return result


# --- NLP Endpoints ---

@nlp_ns.route("/analyze")
class NLPAnalyze(Resource):
    """Run full NLP pipeline on articles."""

    @nlp_ns.doc("analyze_with_nlp")
    @nlp_ns.param("limit", "Number of articles to analyze", type=int, default=50)
    @nlp_ns.param("fit_topics", "Whether to fit topic model", type=bool, default=True)
    def post(self):
        """Run NLP pipeline on articles (FinBERT + spaCy NER + BERTopic)."""
        limit = request.args.get("limit", 50, type=int)
        fit_topics = request.args.get("fit_topics", "true").lower() == "true"

        try:
            redis_client = get_redis_client()
            pipeline = get_nlp_pipeline()

            # Get unanalyzed articles
            articles_data = redis_client.get_articles(limit=limit)

            # Convert to Article objects
            articles = []
            for data in articles_data:
                try:
                    articles.append(Article.from_dict(data))
                except Exception as e:
                    logger.warning(f"Failed to parse article: {e}")

            if not articles:
                return {"status": "success", "message": "No articles to analyze", "processed": 0}

            # Run NLP pipeline
            result = pipeline.process_and_store(articles, fit_topics=fit_topics)

            return {
                "status": "success",
                "processed": result["processed"],
                "stored": result["stored"],
                "ticker_updates": result["ticker_updates"],
                "topics_fitted": result["topics_fitted"]
            }

        except Exception as e:
            logger.error(f"NLP analysis failed: {e}")
            return {"status": "error", "message": str(e)}, 500


@nlp_ns.route("/analyze/<string:article_id>")
class NLPAnalyzeArticle(Resource):
    """Analyze a single article with full NLP."""

    @nlp_ns.doc("analyze_single_article")
    def get(self, article_id):
        """Get detailed NLP analysis for a single article."""
        try:
            redis_client = get_redis_client()
            article_data = redis_client.get_article(article_id)

            if not article_data:
                nlp_ns.abort(404, f"Article {article_id} not found")

            # Check if already analyzed
            if article_data.get("nlp_analysis"):
                return article_data["nlp_analysis"]

            # Analyze now
            pipeline = get_nlp_pipeline()
            article = Article.from_dict(article_data)
            analysis = pipeline.analyze_article(article, include_sentence_sentiment=True)

            return analysis.to_dict()

        except Exception as e:
            logger.error(f"Article analysis failed: {e}")
            return {"status": "error", "message": str(e)}, 500


@nlp_ns.route("/sentiment")
class NLPSentiment(Resource):
    """Analyze sentiment of arbitrary text."""

    @nlp_ns.doc("analyze_text_sentiment")
    def post(self):
        """Analyze sentiment of provided text using FinBERT."""
        try:
            data = request.get_json()
            text = data.get("text", "")

            if not text:
                return {"error": "No text provided"}, 400

            pipeline = get_nlp_pipeline()
            result = pipeline.sentiment_analyzer.analyze_with_sentences(text)

            return {
                "overall": result["overall"].model_dump(mode="json"),
                "sentences": [
                    {"text": s["text"], "score": s["sentiment"].score, "label": s["sentiment"].label}
                    for s in result.get("sentences", [])
                ],
                "positive_sentences": result.get("positive_sentences", 0),
                "negative_sentences": result.get("negative_sentences", 0),
                "neutral_sentences": result.get("neutral_sentences", 0)
            }

        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            return {"status": "error", "message": str(e)}, 500


@nlp_ns.route("/entities")
class NLPEntities(Resource):
    """Extract entities from text."""

    @nlp_ns.doc("extract_entities")
    def post(self):
        """Extract entities, tickers, and financial metrics from text."""
        try:
            data = request.get_json()
            text = data.get("text", "")

            if not text:
                return {"error": "No text provided"}, 400

            pipeline = get_nlp_pipeline()
            extraction = pipeline.entity_extractor.full_extraction(text)

            return extraction

        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return {"status": "error", "message": str(e)}, 500


@nlp_ns.route("/topics")
class NLPTopics(Resource):
    """Topic modeling endpoints."""

    @nlp_ns.doc("get_topics")
    def get(self):
        """Get summary of discovered topics."""
        try:
            pipeline = get_nlp_pipeline()
            summary = pipeline.get_topic_summary()

            if summary is None:
                return {
                    "status": "not_fitted",
                    "message": "Topic model not yet fitted. Run POST /api/nlp/analyze first."
                }

            return summary

        except Exception as e:
            logger.error(f"Topic summary failed: {e}")
            return {"status": "error", "message": str(e)}, 500


@nlp_ns.route("/market-sentiment")
class NLPMarketSentiment(Resource):
    """Aggregate market sentiment analysis."""

    @nlp_ns.doc("get_market_sentiment")
    @nlp_ns.param("days", "Analysis period in days", type=int, default=7)
    @nlp_ns.param("limit", "Max articles to analyze", type=int, default=100)
    def get(self):
        """Get aggregated market sentiment from recent articles."""
        try:
            days = request.args.get("days", 7, type=int)
            limit = request.args.get("limit", 100, type=int)

            redis_client = get_redis_client()

            # Get recent articles
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)

            articles_data = redis_client.get_articles(
                limit=limit,
                start_date=start_date,
                end_date=end_date
            )

            # Convert to Article objects
            articles = []
            for data in articles_data:
                try:
                    articles.append(Article.from_dict(data))
                except Exception:
                    continue

            if not articles:
                return {"error": "No articles found for analysis"}

            pipeline = get_nlp_pipeline()
            result = pipeline.analyze_market_sentiment(articles)
            result["period_days"] = days
            result["analyzed_at"] = datetime.utcnow().isoformat()

            return result

        except Exception as e:
            logger.error(f"Market sentiment analysis failed: {e}")
            return {"status": "error", "message": str(e)}, 500


# --- Stock Data Endpoints (Alpha Vantage) ---

@stocks_ns.route("/search")
class StockSearch(Resource):
    """Search for stock symbols."""

    @stocks_ns.doc("search_stocks")
    @stocks_ns.param("q", "Search query (company name or symbol)")
    def get(self):
        """Search for stocks by company name or symbol."""
        query = request.args.get("q", "")
        if not query or len(query) < 2:
            return {"error": "Query must be at least 2 characters"}, 400

        try:
            client = get_alpha_vantage_client()
            results = client.search_symbol(query)
            return {"results": results, "count": len(results)}
        except Exception as e:
            logger.error(f"Stock search failed: {e}")
            return {"error": str(e)}, 500


@stocks_ns.route("/<string:symbol>/quote")
class StockQuote(Resource):
    """Get current stock quote."""

    @stocks_ns.doc("get_stock_quote")
    def get(self, symbol):
        """Get current stock price and trading data."""
        try:
            client = get_alpha_vantage_client()
            quote = client.get_quote(symbol.upper())

            if not quote:
                return {"error": f"No quote data for {symbol}"}, 404

            return quote.to_dict()
        except Exception as e:
            logger.error(f"Quote fetch failed for {symbol}: {e}")
            return {"error": str(e)}, 500


@stocks_ns.route("/<string:symbol>/history")
class StockHistory(Resource):
    """Get historical stock prices."""

    @stocks_ns.doc("get_stock_history")
    @stocks_ns.param("days", "Number of days of history", type=int, default=30)
    def get(self, symbol):
        """Get historical daily prices for a stock."""
        days = request.args.get("days", 30, type=int)
        days = min(days, 365)  # Limit to 1 year

        try:
            client = get_alpha_vantage_client()
            prices = client.get_daily_prices(symbol.upper(), days=days)

            if not prices:
                return {"error": f"No price history for {symbol}"}, 404

            return {
                "symbol": symbol.upper(),
                "days": len(prices),
                "prices": [p.to_dict() for p in prices]
            }
        except Exception as e:
            logger.error(f"History fetch failed for {symbol}: {e}")
            return {"error": str(e)}, 500


@stocks_ns.route("/<string:symbol>/overview")
class StockOverview(Resource):
    """Get company fundamental data."""

    @stocks_ns.doc("get_company_overview")
    def get(self, symbol):
        """Get company overview including market cap, sector, P/E ratio, etc."""
        try:
            client = get_alpha_vantage_client()
            overview = client.get_company_overview(symbol.upper())

            if not overview:
                return {"error": f"No company data for {symbol}"}, 404

            return overview.to_dict()
        except Exception as e:
            logger.error(f"Overview fetch failed for {symbol}: {e}")
            return {"error": str(e)}, 500


@stocks_ns.route("/<string:symbol>/analysis")
class StockAnalysis(Resource):
    """Combined stock and sentiment analysis."""

    @stocks_ns.doc("get_stock_analysis")
    @stocks_ns.param("days", "Analysis period in days", type=int, default=30)
    def get(self, symbol):
        """Get stock prices + news sentiment correlation analysis."""
        days = request.args.get("days", 30, type=int)
        symbol = symbol.upper()

        try:
            client = get_alpha_vantage_client()
            redis_client = get_redis_client()

            # Get stock data
            quote = client.get_quote(symbol)
            prices = client.get_daily_prices(symbol, days=days)
            overview = client.get_company_overview(symbol)

            # Get news sentiment for this ticker
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)

            articles = redis_client.get_articles(limit=500, start_date=start_date, end_date=end_date)
            ticker_articles = [
                a for a in articles
                if symbol in [t.upper() for t in a.get("tickers", [])]
            ]

            # Group sentiment by date
            daily_sentiment = {}
            for article in ticker_articles:
                pub_date = article.get("published_at", "")[:10]
                if pub_date:
                    sentiment = article.get("sentiment", {}).get("score", 0)
                    if pub_date not in daily_sentiment:
                        daily_sentiment[pub_date] = {"sum": 0, "count": 0, "articles": []}
                    daily_sentiment[pub_date]["sum"] += sentiment
                    daily_sentiment[pub_date]["count"] += 1
                    daily_sentiment[pub_date]["articles"].append({
                        "title": article.get("title"),
                        "sentiment": sentiment
                    })

            # Combine price and sentiment data
            combined_data = []
            for price in prices:
                date = price.date
                sent_data = daily_sentiment.get(date, {"sum": 0, "count": 0})
                avg_sent = sent_data["sum"] / sent_data["count"] if sent_data["count"] > 0 else None

                combined_data.append({
                    "date": date,
                    "close": price.close,
                    "volume": price.volume,
                    "price_change": round(price.close - price.open, 2),
                    "avg_sentiment": round(avg_sent, 4) if avg_sent else None,
                    "news_count": sent_data["count"]
                })

            # Calculate correlation insights
            price_changes = []
            sentiment_scores = []
            for d in combined_data:
                if d["avg_sentiment"] is not None:
                    price_changes.append(d["price_change"])
                    sentiment_scores.append(d["avg_sentiment"])

            correlation = None
            if len(price_changes) >= 5:
                # Simple correlation calculation
                n = len(price_changes)
                sum_x = sum(sentiment_scores)
                sum_y = sum(price_changes)
                sum_xy = sum(x * y for x, y in zip(sentiment_scores, price_changes))
                sum_x2 = sum(x ** 2 for x in sentiment_scores)
                sum_y2 = sum(y ** 2 for y in price_changes)

                numerator = n * sum_xy - sum_x * sum_y
                denominator = ((n * sum_x2 - sum_x ** 2) * (n * sum_y2 - sum_y ** 2)) ** 0.5

                if denominator != 0:
                    correlation = round(numerator / denominator, 4)

            return {
                "symbol": symbol,
                "current_quote": quote.to_dict() if quote else None,
                "company": overview.to_dict() if overview else None,
                "price_sentiment_data": combined_data,
                "total_articles": len(ticker_articles),
                "sentiment_price_correlation": correlation,
                "correlation_insight": (
                    "Strong positive correlation - sentiment predicts price movement" if correlation and correlation > 0.5 else
                    "Moderate positive correlation" if correlation and correlation > 0.3 else
                    "Weak or no correlation" if correlation and correlation > -0.3 else
                    "Negative correlation - contrarian indicator" if correlation else
                    "Insufficient data for correlation"
                ),
                "analysis_period_days": days
            }

        except Exception as e:
            logger.error(f"Stock analysis failed for {symbol}: {e}")
            return {"error": str(e)}, 500


# --- Market Data Endpoints (yfinance) ---

@market_ns.route("/indices")
class MarketIndices(Resource):
    """Get major market indices."""

    @market_ns.doc("get_market_indices")
    def get(self):
        """Get current data for major market indices (DOW, S&P 500, NASDAQ, etc.)."""
        try:
            service = get_market_data_service()
            indices = service.get_market_indices()
            return {"indices": indices, "count": len(indices)}
        except Exception as e:
            logger.error(f"Failed to get market indices: {e}")
            return {"error": str(e)}, 500


@market_ns.route("/quote/<string:symbol>")
class MarketQuote(Resource):
    """Get quote for any stock/ETF."""

    @market_ns.doc("get_market_quote")
    def get(self, symbol):
        """Get current quote for a stock, ETF, or index."""
        try:
            service = get_market_data_service()
            quote = service.get_quote(symbol)

            if not quote:
                return {"error": f"No data for symbol: {symbol}"}, 404

            return quote.to_dict()
        except Exception as e:
            logger.error(f"Failed to get quote for {symbol}: {e}")
            return {"error": str(e)}, 500


@market_ns.route("/quotes")
class MarketQuotes(Resource):
    """Get quotes for multiple symbols."""

    @market_ns.doc("get_market_quotes")
    @market_ns.param("symbols", "Comma-separated list of symbols")
    def get(self):
        """Get quotes for multiple symbols at once."""
        symbols_str = request.args.get("symbols", "")
        if not symbols_str:
            return {"error": "No symbols provided"}, 400

        symbols = [s.strip().upper() for s in symbols_str.split(",") if s.strip()]

        if len(symbols) > 20:
            return {"error": "Maximum 20 symbols allowed"}, 400

        try:
            service = get_market_data_service()
            quotes = service.get_multiple_quotes(symbols)
            return {"quotes": [q.to_dict() for q in quotes], "count": len(quotes)}
        except Exception as e:
            logger.error(f"Failed to get quotes: {e}")
            return {"error": str(e)}, 500


@market_ns.route("/history/<string:symbol>")
class MarketHistory(Resource):
    """Get historical prices."""

    @market_ns.doc("get_market_history")
    @market_ns.param("period", "Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max)", default="1mo")
    @market_ns.param("interval", "Data interval (1m, 5m, 15m, 30m, 1h, 1d, 1wk, 1mo)", default="1d")
    def get(self, symbol):
        """Get historical price data for a symbol."""
        period = request.args.get("period", "1mo")
        interval = request.args.get("interval", "1d")

        # Validate inputs
        valid_periods = ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "max"]
        valid_intervals = ["1m", "5m", "15m", "30m", "1h", "1d", "1wk", "1mo"]

        if period not in valid_periods:
            return {"error": f"Invalid period. Must be one of: {valid_periods}"}, 400
        if interval not in valid_intervals:
            return {"error": f"Invalid interval. Must be one of: {valid_intervals}"}, 400

        try:
            service = get_market_data_service()
            prices = service.get_historical_prices(symbol, period, interval)

            if not prices:
                return {"error": f"No historical data for {symbol}"}, 404

            return {
                "symbol": symbol.upper(),
                "period": period,
                "interval": interval,
                "prices": [p.to_dict() for p in prices],
                "count": len(prices)
            }
        except Exception as e:
            logger.error(f"Failed to get history for {symbol}: {e}")
            return {"error": str(e)}, 500


@market_ns.route("/search")
class MarketSearch(Resource):
    """Search for stocks/ETFs."""

    @market_ns.doc("search_market")
    @market_ns.param("q", "Search query (symbol or company name)")
    @market_ns.param("limit", "Maximum results", type=int, default=10)
    def get(self):
        """Search for stocks, ETFs, or indices by symbol or name."""
        query = request.args.get("q", "")
        limit = request.args.get("limit", 10, type=int)

        if not query or len(query) < 1:
            return {"error": "Query must be at least 1 character"}, 400

        try:
            service = get_market_data_service()
            results = service.search_symbols(query, limit)
            return {"results": results, "count": len(results)}
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return {"error": str(e)}, 500


@market_ns.route("/company/<string:symbol>")
class MarketCompany(Resource):
    """Get company information."""

    @market_ns.doc("get_company_info")
    def get(self, symbol):
        """Get detailed company information."""
        try:
            service = get_market_data_service()
            info = service.get_company_info(symbol)

            if not info:
                return {"error": f"No company info for {symbol}"}, 404

            return info
        except Exception as e:
            logger.error(f"Failed to get company info for {symbol}: {e}")
            return {"error": str(e)}, 500


@market_ns.route("/trending")
class MarketTrending(Resource):
    """Get trending/most active stocks."""

    @market_ns.doc("get_trending")
    def get(self):
        """Get most active/trending stocks."""
        try:
            service = get_market_data_service()
            trending = service.get_trending_tickers()
            return {"tickers": trending, "count": len(trending)}
        except Exception as e:
            logger.error(f"Failed to get trending: {e}")
            return {"error": str(e)}, 500


# --- AI Insights Endpoints ---

@ai_ns.route("/insights")
class AIInsights(Resource):
    """Get AI-generated market insights."""

    @ai_ns.doc("get_ai_insights")
    def get(self):
        """Get cached AI insights. Generated every 15 min by background job."""
        try:
            service = get_ai_insights_service()

            if not service.is_configured():
                return {
                    "status": "not_configured",
                    "insights": None,
                    "is_generating": False,
                    "message": "AI insights service is not configured. Set ANTHROPIC_API_KEY environment variable."
                }, 503

            result = service.get_or_generate(force=False)
            return result

        except Exception as e:
            logger.error(f"Failed to get AI insights: {e}")
            return {"status": "error", "message": str(e)}, 500


@ai_ns.route("/insights/refresh")
class AIInsightsRefresh(Resource):
    """Manually refresh AI insights."""

    @ai_ns.doc("refresh_ai_insights")
    def post(self):
        """Manually trigger AI insights generation. Rate limited to 1/min."""
        try:
            service = get_ai_insights_service()

            if not service.is_configured():
                return {
                    "status": "not_configured",
                    "insights": None,
                    "is_generating": False,
                    "message": "AI insights service is not configured"
                }, 503

            result = service.get_or_generate(force=True)

            if result.get("status") == "rate_limited":
                return result, 429

            return result

        except Exception as e:
            logger.error(f"Failed to refresh AI insights: {e}")
            return {"status": "error", "message": str(e)}, 500


@ai_ns.route("/insights/status")
class AIInsightsStatus(Resource):
    """Get AI insights service status."""

    @ai_ns.doc("get_ai_insights_status")
    def get(self):
        """Get the current status of the AI insights service."""
        try:
            service = get_ai_insights_service()
            return service.get_status()
        except Exception as e:
            logger.error(f"Failed to get AI insights status: {e}")
            return {"status": "error", "message": str(e)}, 500


# Health check endpoint (outside namespaces)
@api_bp.route("/health")
def health_check():
    """Health check endpoint."""
    redis_client = get_redis_client()
    redis_ok = redis_client.ping()

    return jsonify({
        "status": "healthy" if redis_ok else "degraded",
        "redis": "connected" if redis_ok else "disconnected",
        "timestamp": datetime.utcnow().isoformat()
    }), 200 if redis_ok else 503
