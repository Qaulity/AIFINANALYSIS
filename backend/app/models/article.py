"""Article and related data models."""
from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field
import hashlib


class ArticleSource(str, Enum):
    """Source of the article."""
    NEWSAPI = "newsapi"
    RSS = "rss"
    SCRAPER = "scraper"


class SentimentResult(BaseModel):
    """Sentiment analysis result for an article."""
    score: float = Field(..., ge=-1.0, le=1.0, description="Sentiment score from -1 (negative) to 1 (positive)")
    label: str = Field(..., description="Sentiment label: positive, negative, or neutral")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence in the prediction")
    model: str = Field(default="textblob", description="Model used for analysis")
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)

    @classmethod
    def from_score(cls, score: float, model: str = "textblob") -> "SentimentResult":
        """Create a SentimentResult from a raw score."""
        if score > 0.1:
            label = "positive"
        elif score < -0.1:
            label = "negative"
        else:
            label = "neutral"

        return cls(score=score, label=label, model=model)


class Article(BaseModel):
    """Unified article model for all news sources."""
    id: Optional[str] = Field(default=None, description="Unique article identifier")
    title: str = Field(..., min_length=1, description="Article title")
    content: Optional[str] = Field(default=None, description="Full article content")
    description: Optional[str] = Field(default=None, description="Article summary/description")
    url: str = Field(..., description="Original article URL")
    source_name: str = Field(..., description="Name of the news source")
    source_type: ArticleSource = Field(..., description="Type of source (newsapi, rss, scraper)")
    author: Optional[str] = Field(default=None, description="Article author")
    published_at: datetime = Field(..., description="Publication date")
    image_url: Optional[str] = Field(default=None, description="Featured image URL")

    # Analysis results
    sentiment: Optional[SentimentResult] = Field(default=None, description="Sentiment analysis result")
    tickers: List[str] = Field(default_factory=list, description="Mentioned stock tickers")
    entities: List[str] = Field(default_factory=list, description="Named entities extracted")
    topics: List[str] = Field(default_factory=list, description="Topic labels")

    # Metadata
    fetched_at: datetime = Field(default_factory=datetime.utcnow)

    def model_post_init(self, __context) -> None:
        """Generate ID if not provided."""
        if self.id is None:
            self.id = self.generate_id()

    def generate_id(self) -> str:
        """Generate a unique ID based on URL and title."""
        content = f"{self.url}:{self.title}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        data = self.model_dump(mode="json")
        if self.sentiment:
            data["sentiment"] = self.sentiment.model_dump(mode="json")
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Article":
        """Create from dictionary."""
        if "sentiment" in data and data["sentiment"]:
            data["sentiment"] = SentimentResult(**data["sentiment"])
        return cls(**data)
