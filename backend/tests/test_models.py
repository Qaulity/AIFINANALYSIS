"""Tests for data models."""
import pytest
from datetime import datetime
from app.models import Article, ArticleSource, SentimentResult


class TestSentimentResult:
    """Tests for SentimentResult model."""

    def test_from_score_positive(self):
        """Test creating positive sentiment from score."""
        result = SentimentResult.from_score(0.5)
        assert result.label == "positive"
        assert result.score == 0.5
        assert result.model == "textblob"

    def test_from_score_negative(self):
        """Test creating negative sentiment from score."""
        result = SentimentResult.from_score(-0.3)
        assert result.label == "negative"
        assert result.score == -0.3

    def test_from_score_neutral(self):
        """Test creating neutral sentiment from score."""
        result = SentimentResult.from_score(0.05)
        assert result.label == "neutral"


class TestArticle:
    """Tests for Article model."""

    def test_article_creation(self):
        """Test basic article creation."""
        article = Article(
            title="Test Article",
            url="https://example.com/article",
            source_name="Test Source",
            source_type=ArticleSource.NEWSAPI,
            published_at=datetime.utcnow()
        )
        assert article.title == "Test Article"
        assert article.id is not None
        assert len(article.id) == 16

    def test_article_id_generation(self):
        """Test that same URL+title generates same ID."""
        article1 = Article(
            title="Test",
            url="https://example.com/test",
            source_name="Source",
            source_type=ArticleSource.RSS,
            published_at=datetime.utcnow()
        )
        article2 = Article(
            title="Test",
            url="https://example.com/test",
            source_name="Different Source",
            source_type=ArticleSource.RSS,
            published_at=datetime.utcnow()
        )
        assert article1.id == article2.id

    def test_article_to_dict(self):
        """Test article serialization."""
        article = Article(
            title="Test",
            url="https://example.com",
            source_name="Source",
            source_type=ArticleSource.NEWSAPI,
            published_at=datetime.utcnow(),
            sentiment=SentimentResult.from_score(0.5)
        )
        data = article.to_dict()
        assert data["title"] == "Test"
        assert data["sentiment"]["label"] == "positive"

    def test_article_from_dict(self):
        """Test article deserialization."""
        data = {
            "title": "Test",
            "url": "https://example.com",
            "source_name": "Source",
            "source_type": "newsapi",
            "published_at": datetime.utcnow().isoformat(),
            "tickers": ["AAPL", "GOOGL"]
        }
        article = Article.from_dict(data)
        assert article.title == "Test"
        assert article.tickers == ["AAPL", "GOOGL"]
