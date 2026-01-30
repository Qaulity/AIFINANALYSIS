"""FinBERT-based sentiment analysis for financial text."""
import torch
from typing import List, Dict, Optional, Tuple
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from loguru import logger
import numpy as np

from ...models import SentimentResult


class FinBERTAnalyzer:
    """FinBERT sentiment analyzer - fine-tuned on financial text, outputs score/label/confidence."""

    MODEL_NAME = "ProsusAI/finbert"

    def __init__(self, device: Optional[str] = None):
        """Initialize with device ('cuda', 'cpu', or None for auto-detect)."""
        self._model = None
        self._tokenizer = None
        self._device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self._loaded = False

        logger.info(f"FinBERT analyzer initialized (device: {self._device})")

    def _load_model(self):
        """Lazy load the model (it's ~440MB)."""
        if self._loaded:
            return

        logger.info(f"Loading FinBERT model from {self.MODEL_NAME}...")

        try:
            self._tokenizer = AutoTokenizer.from_pretrained(self.MODEL_NAME)
            self._model = AutoModelForSequenceClassification.from_pretrained(self.MODEL_NAME)
            self._model.to(self._device)
            self._model.eval()
            self._loaded = True
            logger.info("FinBERT model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load FinBERT model: {e}")
            raise

    def analyze(self, text: str) -> SentimentResult:
        """Analyze sentiment of a single text, returns SentimentResult."""
        if not text or len(text.strip()) < 10:
            return SentimentResult(
                score=0.0,
                label="neutral",
                confidence=0.0,
                model="finbert"
            )

        self._load_model()

        try:
            # Tokenize with truncation for long texts
            inputs = self._tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True
            ).to(self._device)

            # Get predictions
            with torch.no_grad():
                outputs = self._model(**inputs)
                probabilities = torch.nn.functional.softmax(outputs.logits, dim=-1)

            # FinBERT outputs: [positive, negative, neutral]
            probs = probabilities[0].cpu().numpy()
            positive, negative, neutral = probs

            # Determine label and confidence
            max_idx = np.argmax(probs)
            labels = ["positive", "negative", "neutral"]
            label = labels[max_idx]
            confidence = float(probs[max_idx])

            # Calculate score on -1 to 1 scale
            # Positive contributes positively, negative contributes negatively
            score = float(positive - negative)

            return SentimentResult(
                score=round(score, 4),
                label=label,
                confidence=round(confidence, 4),
                model="finbert"
            )

        except Exception as e:
            logger.error(f"FinBERT analysis failed: {e}")
            return SentimentResult(
                score=0.0,
                label="neutral",
                confidence=0.0,
                model="finbert-error"
            )

    def analyze_batch(self, texts: List[str], batch_size: int = 16) -> List[SentimentResult]:
        """Batch analyze multiple texts, returns list of SentimentResult."""
        if not texts:
            return []

        self._load_model()
        results = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            # Filter empty texts
            valid_indices = []
            valid_texts = []
            for j, text in enumerate(batch):
                if text and len(text.strip()) >= 10:
                    valid_indices.append(j)
                    valid_texts.append(text)

            if not valid_texts:
                results.extend([
                    SentimentResult(score=0.0, label="neutral", confidence=0.0, model="finbert")
                    for _ in batch
                ])
                continue

            try:
                inputs = self._tokenizer(
                    valid_texts,
                    return_tensors="pt",
                    truncation=True,
                    max_length=512,
                    padding=True
                ).to(self._device)

                with torch.no_grad():
                    outputs = self._model(**inputs)
                    probabilities = torch.nn.functional.softmax(outputs.logits, dim=-1)

                probs_batch = probabilities.cpu().numpy()

                # Build results maintaining original order
                batch_results = [None] * len(batch)

                for idx, probs in zip(valid_indices, probs_batch):
                    positive, negative, neutral = probs
                    max_idx = np.argmax(probs)
                    labels = ["positive", "negative", "neutral"]

                    batch_results[idx] = SentimentResult(
                        score=round(float(positive - negative), 4),
                        label=labels[max_idx],
                        confidence=round(float(probs[max_idx]), 4),
                        model="finbert"
                    )

                # Fill in empty results
                for j in range(len(batch)):
                    if batch_results[j] is None:
                        batch_results[j] = SentimentResult(
                            score=0.0, label="neutral", confidence=0.0, model="finbert"
                        )

                results.extend(batch_results)

            except Exception as e:
                logger.error(f"Batch analysis failed: {e}")
                results.extend([
                    SentimentResult(score=0.0, label="neutral", confidence=0.0, model="finbert-error")
                    for _ in batch
                ])

        return results

    def analyze_with_sentences(self, text: str) -> Dict:
        """Analyze with sentence-level breakdown, returns overall + per-sentence sentiments."""
        import nltk
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt', quiet=True)

        from nltk.tokenize import sent_tokenize

        sentences = sent_tokenize(text)

        if not sentences:
            return {
                "overall": self.analyze(text),
                "sentences": []
            }

        # Analyze each sentence
        sentence_results = self.analyze_batch(sentences)

        # Calculate weighted overall sentiment
        total_weight = 0
        weighted_score = 0

        sentence_analysis = []
        for sent, result in zip(sentences, sentence_results):
            weight = len(sent)  # Weight by sentence length
            weighted_score += result.score * weight
            total_weight += weight
            sentence_analysis.append({
                "text": sent,
                "sentiment": result
            })

        overall_score = weighted_score / total_weight if total_weight > 0 else 0

        # Determine overall label
        if overall_score > 0.1:
            overall_label = "positive"
        elif overall_score < -0.1:
            overall_label = "negative"
        else:
            overall_label = "neutral"

        return {
            "overall": SentimentResult(
                score=round(overall_score, 4),
                label=overall_label,
                confidence=round(sum(r.confidence for r in sentence_results) / len(sentence_results), 4),
                model="finbert-aggregate"
            ),
            "sentences": sentence_analysis,
            "positive_sentences": sum(1 for r in sentence_results if r.label == "positive"),
            "negative_sentences": sum(1 for r in sentence_results if r.label == "negative"),
            "neutral_sentences": sum(1 for r in sentence_results if r.label == "neutral")
        }
