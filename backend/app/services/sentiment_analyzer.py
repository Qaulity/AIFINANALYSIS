"""Sentiment analysis for financial news articles."""
from typing import Optional, List
from textblob import TextBlob
from loguru import logger

from ..models import Article, SentimentResult
from ..utils import get_redis_client
from ..config import get_settings


class SentimentAnalyzer:
    """Analyzes sentiment of news articles using TextBlob or FinBERT."""

    def __init__(self):
        settings = get_settings()
        self.model_type = settings.SENTIMENT_MODEL
        self._finbert_model = None
        self._finbert_tokenizer = None

    def _load_finbert(self):
        """Lazy load FinBERT model (heavy, only load if needed)."""
        if self._finbert_model is None:
            try:
                from transformers import AutoTokenizer, AutoModelForSequenceClassification
                import torch

                model_name = "ProsusAI/finbert"
                self._finbert_tokenizer = AutoTokenizer.from_pretrained(model_name)
                self._finbert_model = AutoModelForSequenceClassification.from_pretrained(model_name)
                logger.info("FinBERT model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load FinBERT: {e}")
                raise

    def analyze_text_textblob(self, text: str) -> SentimentResult:
        """Analyze sentiment using TextBlob."""
        blob = TextBlob(text)
        # TextBlob polarity is -1 to 1
        score = blob.sentiment.polarity
        return SentimentResult.from_score(score, model="textblob")

    def analyze_text_finbert(self, text: str) -> SentimentResult:
        """Analyze sentiment using FinBERT."""
        self._load_finbert()

        try:
            import torch

            # Truncate text to model max length
            inputs = self._finbert_tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True
            )

            with torch.no_grad():
                outputs = self._finbert_model(**inputs)
                predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)

            # FinBERT outputs: [positive, negative, neutral]
            scores = predictions[0].tolist()
            positive, negative, neutral = scores

            # Convert to -1 to 1 scale
            sentiment_score = positive - negative

            return SentimentResult(
                score=round(sentiment_score, 4),
                label="positive" if positive > max(negative, neutral) else
                      "negative" if negative > max(positive, neutral) else "neutral",
                confidence=max(scores),
                model="finbert"
            )

        except Exception as e:
            logger.error(f"FinBERT analysis failed: {e}")
            # Fallback to TextBlob
            return self.analyze_text_textblob(text)

    def analyze_text(self, text: str) -> SentimentResult:
        """Analyze text using configured model."""
        if not text or len(text.strip()) < 10:
            return SentimentResult(score=0.0, label="neutral", confidence=0.0, model="none")

        if self.model_type == "finbert":
            return self.analyze_text_finbert(text)
        else:
            return self.analyze_text_textblob(text)

    def analyze_article(self, article: Article) -> SentimentResult:
        """Analyze sentiment of an article."""
        # Combine title and content/description for analysis
        text_parts = [article.title]

        if article.content:
            text_parts.append(article.content)
        elif article.description:
            text_parts.append(article.description)

        combined_text = " ".join(text_parts)
        return self.analyze_text(combined_text)

    def process_article(self, article: Article) -> Article:
        """Process an article and add sentiment analysis."""
        sentiment = self.analyze_article(article)
        article.sentiment = sentiment
        return article

    def process_articles(self, articles: List[Article]) -> List[Article]:
        """Process multiple articles."""
        processed = []
        for article in articles:
            try:
                processed.append(self.process_article(article))
            except Exception as e:
                logger.error(f"Failed to process article {article.id}: {e}")
                processed.append(article)
        return processed

    def process_stored_articles(self, limit: int = 100) -> int:
        """Process articles stored in Redis that don't have sentiment."""
        redis_client = get_redis_client()
        articles = redis_client.get_articles(limit=limit)

        processed_count = 0
        for article_data in articles:
            article_id = article_data.get("id")

            # Skip if already has sentiment
            if article_data.get("sentiment"):
                continue

            try:
                article = Article.from_dict(article_data)
                sentiment = self.analyze_article(article)

                # Update article with sentiment
                article_data["sentiment"] = sentiment.model_dump(mode="json")
                redis_client.store_article(article_id, article_data)

                # Also store sentiment separately for quick access
                redis_client.store_sentiment(article_id, sentiment.model_dump(mode="json"))

                # Track ticker sentiment if tickers are identified
                for ticker in article_data.get("tickers", []):
                    redis_client.add_ticker_mention(ticker, article_id, sentiment.score)

                processed_count += 1

            except Exception as e:
                logger.error(f"Failed to process article {article_id}: {e}")

        logger.info(f"Processed sentiment for {processed_count} articles")
        return processed_count
