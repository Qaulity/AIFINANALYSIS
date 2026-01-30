"""Tests for sentiment analysis service."""
import pytest
from datetime import datetime
from app.services import SentimentAnalyzer
from app.models import Article, ArticleSource


class TestSentimentAnalyzer:
    """Tests for SentimentAnalyzer."""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        return SentimentAnalyzer()

    def test_analyze_positive_text(self, analyzer):
        """Test analyzing positive text."""
        result = analyzer.analyze_text(
            "The company reported excellent earnings and strong growth. "
            "Investors are very happy with the results."
        )
        assert result.score > 0
        assert result.label == "positive"

    def test_analyze_negative_text(self, analyzer):
        """Test analyzing negative text."""
        result = analyzer.analyze_text(
            "The company suffered major losses. Stock prices crashed. "
            "Investors are worried about the future."
        )
        assert result.score < 0
        assert result.label == "negative"

    def test_analyze_neutral_text(self, analyzer):
        """Test analyzing neutral text."""
        result = analyzer.analyze_text(
            "The company released their quarterly report today."
        )
        assert abs(result.score) < 0.3  # Near neutral

    def test_analyze_empty_text(self, analyzer):
        """Test analyzing empty or very short text."""
        result = analyzer.analyze_text("")
        assert result.score == 0
        assert result.label == "neutral"
        assert result.confidence == 0

    def test_analyze_article(self, analyzer):
        """Test analyzing a full article."""
        article = Article(
            title="Great earnings beat expectations",
            description="Company XYZ reported amazing quarterly results.",
            url="https://example.com/article",
            source_name="Test",
            source_type=ArticleSource.NEWSAPI,
            published_at=datetime.utcnow()
        )
        result = analyzer.analyze_article(article)
        assert result.score > 0

    def test_process_article(self, analyzer):
        """Test processing article adds sentiment."""
        article = Article(
            title="Stock market rally continues",
            url="https://example.com/rally",
            source_name="Test",
            source_type=ArticleSource.RSS,
            published_at=datetime.utcnow()
        )
        assert article.sentiment is None

        processed = analyzer.process_article(article)
        assert processed.sentiment is not None
        assert processed.sentiment.model == "textblob"
