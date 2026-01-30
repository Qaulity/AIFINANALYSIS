"""Unified NLP pipeline orchestrating all analysis components."""
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass, field
from loguru import logger
import torch

from .finbert_analyzer import FinBERTAnalyzer
from .entity_extractor import EntityExtractor
from .topic_modeler import TopicModeler
from ...models import Article, SentimentResult
from ...utils import get_redis_client


@dataclass
class ArticleAnalysis:
    """Complete NLP analysis results for an article."""
    article_id: str
    sentiment: SentimentResult
    sentence_sentiments: List[Dict] = field(default_factory=list)
    tickers: List[Dict] = field(default_factory=list)
    entities: List[Dict] = field(default_factory=list)
    people: List[Dict] = field(default_factory=list)
    financial_metrics: Dict = field(default_factory=dict)
    topics: List[str] = field(default_factory=list)
    topic_id: Optional[int] = None
    analyzed_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict:
        return {
            "article_id": self.article_id,
            "sentiment": self.sentiment.model_dump(mode="json") if self.sentiment else None,
            "sentence_sentiments": self.sentence_sentiments,
            "tickers": self.tickers,
            "entities": self.entities,
            "people": self.people,
            "financial_metrics": self.financial_metrics,
            "topics": self.topics,
            "topic_id": self.topic_id,
            "analyzed_at": self.analyzed_at.isoformat()
        }


class NLPPipeline:
    """NLP pipeline - FinBERT sentiment, entity extraction, ticker detection, topic modeling."""

    def __init__(
        self,
        use_gpu: bool = True,
        enable_topics: bool = True,
        sentiment_batch_size: int = 16
    ):
        """Initialize pipeline with GPU/topic/batch settings."""
        # Only use CUDA if requested AND available
        cuda_available = torch.cuda.is_available()
        device = 'cuda' if use_gpu and cuda_available else 'cpu'

        if use_gpu and not cuda_available:
            logger.warning("GPU requested but CUDA not available, falling back to CPU")

        self.sentiment_analyzer = FinBERTAnalyzer(device=device)
        self.entity_extractor = EntityExtractor()
        self.topic_modeler = TopicModeler() if enable_topics else None
        self.sentiment_batch_size = sentiment_batch_size

        self._topics_fitted = False

        logger.info(f"NLP Pipeline initialized (GPU: {use_gpu}, Topics: {enable_topics})")

    def analyze_article(
        self,
        article: Article,
        include_sentence_sentiment: bool = True,
        include_topics: bool = False
    ) -> ArticleAnalysis:
        """Run full NLP analysis on a single article."""
        # Combine title and content for analysis
        text = article.title
        if article.content:
            text += " " + article.content
        elif article.description:
            text += " " + article.description

        # Sentiment analysis
        if include_sentence_sentiment:
            sentiment_result = self.sentiment_analyzer.analyze_with_sentences(text)
            sentiment = sentiment_result["overall"]
            sentence_sentiments = sentiment_result.get("sentences", [])
        else:
            sentiment = self.sentiment_analyzer.analyze(text)
            sentence_sentiments = []

        # Entity extraction
        extraction = self.entity_extractor.full_extraction(text)

        # Topic assignment (if model is fitted)
        topics = []
        topic_id = None
        if include_topics and self.topic_modeler and self._topics_fitted:
            topic_id, prob, topic_keywords = self.topic_modeler.get_topic_for_document(text)
            topics = topic_keywords

        return ArticleAnalysis(
            article_id=article.id,
            sentiment=sentiment,
            sentence_sentiments=[
                {"text": s["text"], "score": s["sentiment"].score, "label": s["sentiment"].label}
                for s in sentence_sentiments
            ],
            tickers=extraction["tickers"],
            entities=extraction["entities"],
            people=extraction["people"],
            financial_metrics=extraction["metrics"],
            topics=topics,
            topic_id=topic_id
        )

    def analyze_articles_batch(
        self,
        articles: List[Article],
        fit_topics: bool = True
    ) -> List[ArticleAnalysis]:
        """Batch analyze multiple articles with optional topic fitting."""
        if not articles:
            return []

        logger.info(f"Analyzing batch of {len(articles)} articles...")

        # Prepare texts
        texts = []
        for article in articles:
            text = article.title
            if article.content:
                text += " " + article.content
            elif article.description:
                text += " " + article.description
            texts.append(text)

        # Batch sentiment analysis
        logger.info("Running batch sentiment analysis...")
        sentiments = self.sentiment_analyzer.analyze_batch(texts, self.sentiment_batch_size)

        # Topic modeling on the batch
        topic_assignments = []
        topic_keywords_map = {}

        if self.topic_modeler and fit_topics and len(texts) >= 10:
            logger.info("Fitting topic model...")
            topic_assignments, topic_infos = self.topic_modeler.fit_transform(texts)
            self._topics_fitted = True

            # Create mapping from topic_id to keywords
            for info in topic_infos:
                topic_keywords_map[info.id] = info.keywords

        # Analyze each article
        results = []
        for i, (article, text, sentiment) in enumerate(zip(articles, texts, sentiments)):
            # Entity extraction
            extraction = self.entity_extractor.full_extraction(text)

            # Get topic info
            topics = []
            topic_id = None
            if topic_assignments and i < len(topic_assignments):
                topic_id = topic_assignments[i]
                if topic_id in topic_keywords_map:
                    topics = topic_keywords_map[topic_id]

            results.append(ArticleAnalysis(
                article_id=article.id,
                sentiment=sentiment,
                tickers=extraction["tickers"],
                entities=extraction["entities"],
                people=extraction["people"],
                financial_metrics=extraction["metrics"],
                topics=topics,
                topic_id=topic_id
            ))

        logger.info(f"Batch analysis complete: {len(results)} articles processed")
        return results

    def process_and_store(
        self,
        articles: List[Article],
        fit_topics: bool = True
    ) -> Dict:
        """Analyze articles and store results in Redis."""
        redis_client = get_redis_client()

        # Analyze
        analyses = self.analyze_articles_batch(articles, fit_topics=fit_topics)

        # Store results
        stored = 0
        ticker_updates = 0

        for article, analysis in zip(articles, analyses):
            try:
                # Update article with analysis results
                article_data = article.to_dict()
                article_data["sentiment"] = analysis.sentiment.model_dump(mode="json")
                article_data["tickers"] = [t["symbol"] for t in analysis.tickers]
                article_data["entities"] = analysis.entities
                article_data["topics"] = analysis.topics
                article_data["nlp_analysis"] = analysis.to_dict()

                # Store updated article
                redis_client.store_article(article.id, article_data)

                # Store sentiment separately
                redis_client.store_sentiment(article.id, analysis.sentiment.model_dump(mode="json"))

                # Update ticker mentions
                for ticker in analysis.tickers:
                    redis_client.add_ticker_mention(
                        ticker["symbol"],
                        article.id,
                        analysis.sentiment.score
                    )
                    ticker_updates += 1

                stored += 1

            except Exception as e:
                logger.error(f"Failed to store analysis for {article.id}: {e}")

        return {
            "processed": len(analyses),
            "stored": stored,
            "ticker_updates": ticker_updates,
            "topics_fitted": self._topics_fitted
        }

    def get_topic_summary(self) -> Optional[Dict]:
        """Get summary of discovered topics."""
        if self.topic_modeler and self._topics_fitted:
            return self.topic_modeler.get_topic_summary()
        return None

    def find_similar_articles(
        self,
        article: Article,
        top_n: int = 5
    ) -> List[Dict]:
        """Find articles similar to the given one using topic embeddings."""
        if not self.topic_modeler or not self._topics_fitted:
            return []

        text = article.title
        if article.content:
            text += " " + article.content
        elif article.description:
            text += " " + article.description

        similar = self.topic_modeler.get_similar_documents(text, top_n)

        return [
            {"text": doc[:200] + "...", "similarity": score}
            for doc, score in similar
        ]

    def analyze_market_sentiment(self, articles: List[Article]) -> Dict:
        """Aggregate sentiment across articles for overall market mood."""
        if not articles:
            return {"error": "No articles provided"}

        # Get sentiments
        texts = []
        for article in articles:
            text = article.title
            if article.content:
                text += " " + article.content
            elif article.description:
                text += " " + article.description
            texts.append(text)

        sentiments = self.sentiment_analyzer.analyze_batch(texts)

        # Aggregate
        scores = [s.score for s in sentiments]
        labels = [s.label for s in sentiments]

        import numpy as np

        return {
            "total_articles": len(articles),
            "average_sentiment": round(float(np.mean(scores)), 4),
            "sentiment_std": round(float(np.std(scores)), 4),
            "median_sentiment": round(float(np.median(scores)), 4),
            "positive_count": labels.count("positive"),
            "negative_count": labels.count("negative"),
            "neutral_count": labels.count("neutral"),
            "positive_ratio": round(labels.count("positive") / len(labels), 4),
            "negative_ratio": round(labels.count("negative") / len(labels), 4),
            "market_mood": "bullish" if np.mean(scores) > 0.1 else "bearish" if np.mean(scores) < -0.1 else "neutral",
            "confidence": round(float(np.mean([s.confidence for s in sentiments])), 4)
        }
