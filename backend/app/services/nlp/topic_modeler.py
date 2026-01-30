"""Topic modeling for financial news using BERTopic."""
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from loguru import logger


@dataclass
class TopicInfo:
    """Information about a discovered topic."""
    id: int
    name: str
    keywords: List[str]
    size: int  # Number of documents in this topic
    representative_docs: List[str]

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "keywords": self.keywords,
            "size": self.size,
            "representative_docs": self.representative_docs[:3]
        }


class TopicModeler:
    """BERTopic topic modeling - clusters articles by theme, discovers trending topics."""

    # Financial domain stop words to filter out
    FINANCIAL_STOPWORDS = {
        "said", "would", "could", "also", "one", "two", "new", "year", "years",
        "company", "companies", "market", "markets", "stock", "stocks", "share",
        "shares", "percent", "million", "billion", "trillion", "quarter"
    }

    def __init__(
        self,
        embedding_model: str = "all-MiniLM-L6-v2",
        min_topic_size: int = 5,
        n_gram_range: Tuple[int, int] = (1, 2)
    ):
        """Initialize with embedding model, min topic size, and n-gram range."""
        self._model = None
        self._embedding_model_name = embedding_model
        self._min_topic_size = min_topic_size
        self._n_gram_range = n_gram_range
        self._loaded = False
        self._last_topics = None
        self._last_docs = None

    def _load_model(self):
        """Lazy load BERTopic model."""
        if self._loaded:
            return

        logger.info("Loading BERTopic model...")

        try:
            from bertopic import BERTopic
            from sentence_transformers import SentenceTransformer
            from sklearn.feature_extraction.text import CountVectorizer

            # Custom vectorizer with financial stopwords
            vectorizer = CountVectorizer(
                stop_words=list(self.FINANCIAL_STOPWORDS),
                ngram_range=self._n_gram_range
            )

            # Load embedding model
            embedding_model = SentenceTransformer(self._embedding_model_name)

            # Create BERTopic model
            self._model = BERTopic(
                embedding_model=embedding_model,
                vectorizer_model=vectorizer,
                min_topic_size=self._min_topic_size,
                verbose=False,
                calculate_probabilities=True
            )

            self._loaded = True
            logger.info("BERTopic model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load BERTopic: {e}")
            raise

    def fit_transform(self, documents: List[str]) -> Tuple[List[int], List[TopicInfo]]:
        """Discover topics in documents, returns (topic assignments, topic info)."""
        if not documents or len(documents) < self._min_topic_size:
            logger.warning(f"Need at least {self._min_topic_size} documents for topic modeling")
            return [], []

        self._load_model()

        try:
            # Fit model and get topic assignments
            topics, probs = self._model.fit_transform(documents)

            # Store for later use
            self._last_topics = topics
            self._last_docs = documents

            # Get topic info
            topic_info = self._extract_topic_info(documents, topics)

            logger.info(f"Discovered {len(topic_info)} topics from {len(documents)} documents")

            return topics, topic_info

        except Exception as e:
            logger.error(f"Topic modeling failed: {e}")
            return [], []

    def _extract_topic_info(self, documents: List[str], topics: List[int]) -> List[TopicInfo]:
        """Extract detailed topic information."""
        topic_infos = []

        # Get unique topics (excluding -1 which is outliers)
        unique_topics = set(topics)
        unique_topics.discard(-1)

        for topic_id in sorted(unique_topics):
            # Get topic keywords
            topic_words = self._model.get_topic(topic_id)
            keywords = [word for word, _ in topic_words[:10]] if topic_words else []

            # Get documents in this topic
            topic_docs = [doc for doc, t in zip(documents, topics) if t == topic_id]

            # Generate topic name from top keywords
            name = " | ".join(keywords[:3]) if keywords else f"Topic {topic_id}"

            topic_infos.append(TopicInfo(
                id=topic_id,
                name=name,
                keywords=keywords,
                size=len(topic_docs),
                representative_docs=topic_docs[:5]
            ))

        # Sort by size (most common topics first)
        topic_infos.sort(key=lambda x: x.size, reverse=True)

        return topic_infos

    def get_topic_for_document(self, document: str) -> Tuple[int, float, List[str]]:
        """Assign topic to new document, returns (topic_id, probability, keywords)."""
        if not self._loaded or self._model is None:
            logger.warning("Model not fitted yet. Call fit_transform first.")
            return -1, 0.0, []

        try:
            topics, probs = self._model.transform([document])
            topic_id = topics[0]
            prob = float(probs[0].max()) if probs is not None else 0.0

            keywords = []
            if topic_id != -1:
                topic_words = self._model.get_topic(topic_id)
                keywords = [word for word, _ in topic_words[:5]] if topic_words else []

            return topic_id, prob, keywords

        except Exception as e:
            logger.error(f"Topic prediction failed: {e}")
            return -1, 0.0, []

    def get_similar_documents(
        self,
        document: str,
        top_n: int = 5
    ) -> List[Tuple[str, float]]:
        """Find similar documents using embedding similarity."""
        if self._last_docs is None:
            logger.warning("No documents fitted. Call fit_transform first.")
            return []

        try:
            from sentence_transformers import SentenceTransformer

            # Get embeddings
            embedding_model = SentenceTransformer(self._embedding_model_name)
            query_embedding = embedding_model.encode([document])[0]
            doc_embeddings = embedding_model.encode(self._last_docs)

            # Calculate cosine similarity
            from sklearn.metrics.pairwise import cosine_similarity
            similarities = cosine_similarity([query_embedding], doc_embeddings)[0]

            # Get top N
            top_indices = np.argsort(similarities)[::-1][:top_n]

            return [
                (self._last_docs[i], float(similarities[i]))
                for i in top_indices
            ]

        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            return []

    def get_topic_evolution(
        self,
        documents: List[str],
        timestamps: List[str],
        nr_bins: int = 10
    ) -> Dict:
        """Analyze topic trends over time."""
        if len(documents) != len(timestamps):
            logger.error("Documents and timestamps must have same length")
            return {}

        if not self._loaded:
            # Fit first
            self.fit_transform(documents)

        try:
            topics_over_time = self._model.topics_over_time(
                documents,
                timestamps,
                nr_bins=nr_bins
            )

            return {
                "data": topics_over_time.to_dict('records'),
                "topics": list(topics_over_time['Topic'].unique())
            }

        except Exception as e:
            logger.error(f"Topic evolution analysis failed: {e}")
            return {}

    def visualize_topics(self) -> Optional[str]:
        """Generate HTML visualization of topics."""
        if not self._loaded or self._model is None:
            return None

        try:
            fig = self._model.visualize_topics()
            return fig.to_html()
        except Exception as e:
            logger.error(f"Visualization failed: {e}")
            return None

    def get_topic_summary(self) -> Dict:
        """Get summary of all discovered topics."""
        if not self._loaded or self._last_topics is None:
            return {"error": "No topics fitted"}

        topic_counts = {}
        for t in self._last_topics:
            topic_counts[t] = topic_counts.get(t, 0) + 1

        # Get topic info
        topics_info = []
        for topic_id in sorted(set(self._last_topics)):
            if topic_id == -1:
                name = "Outliers"
                keywords = []
            else:
                topic_words = self._model.get_topic(topic_id)
                keywords = [w for w, _ in topic_words[:5]] if topic_words else []
                name = " | ".join(keywords[:3])

            topics_info.append({
                "id": topic_id,
                "name": name,
                "keywords": keywords,
                "count": topic_counts[topic_id],
                "percentage": round(topic_counts[topic_id] / len(self._last_topics) * 100, 2)
            })

        return {
            "total_documents": len(self._last_topics),
            "num_topics": len(set(self._last_topics)) - (1 if -1 in self._last_topics else 0),
            "outliers": topic_counts.get(-1, 0),
            "topics": sorted(topics_info, key=lambda x: x["count"], reverse=True)
        }
