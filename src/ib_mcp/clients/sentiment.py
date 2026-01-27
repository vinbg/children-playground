"""Sentiment Analysis using FinBERT and VADER."""

import logging
from typing import Any

from cachetools import TTLCache

from ..config import SentimentConfig

logger = logging.getLogger(__name__)

# Lazy imports for heavy ML libraries
_finbert_model = None
_finbert_tokenizer = None
_vader_analyzer = None


def _load_finbert():
    """Lazy load FinBERT model."""
    global _finbert_model, _finbert_tokenizer

    if _finbert_model is None:
        logger.info("Loading FinBERT model (this may take a moment on first run)...")
        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
            import torch

            model_name = "ProsusAI/finbert"
            _finbert_tokenizer = AutoTokenizer.from_pretrained(model_name)
            _finbert_model = AutoModelForSequenceClassification.from_pretrained(model_name)
            _finbert_model.eval()

            # Move to GPU if available
            if torch.cuda.is_available():
                _finbert_model = _finbert_model.cuda()
                logger.info("FinBERT loaded on GPU")
            else:
                logger.info("FinBERT loaded on CPU")

        except Exception as e:
            logger.error(f"Failed to load FinBERT: {e}")
            raise

    return _finbert_model, _finbert_tokenizer


def _load_vader():
    """Lazy load VADER sentiment analyzer."""
    global _vader_analyzer

    if _vader_analyzer is None:
        logger.info("Loading VADER sentiment analyzer...")
        try:
            import nltk
            from nltk.sentiment.vader import SentimentIntensityAnalyzer

            # Download VADER lexicon if needed
            try:
                nltk.data.find("sentiment/vader_lexicon.zip")
            except LookupError:
                nltk.download("vader_lexicon", quiet=True)

            _vader_analyzer = SentimentIntensityAnalyzer()
            logger.info("VADER loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load VADER: {e}")
            raise

    return _vader_analyzer


class SentimentAnalyzer:
    """Sentiment analysis for financial text."""

    LABELS = ["positive", "negative", "neutral"]

    def __init__(self, config: SentimentConfig):
        self.config = config
        self._cache = TTLCache(maxsize=1000, ttl=config.cache_ttl)

    def _analyze_with_finbert(self, text: str) -> dict[str, Any]:
        """Analyze sentiment using FinBERT."""
        import torch

        model, tokenizer = _load_finbert()

        # Tokenize
        inputs = tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True
        )

        # Move to same device as model
        if torch.cuda.is_available():
            inputs = {k: v.cuda() for k, v in inputs.items()}

        # Inference
        with torch.no_grad():
            outputs = model(**inputs)
            predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)

        # Get probabilities
        probs = predictions[0].cpu().numpy()

        # FinBERT labels: positive, negative, neutral
        sentiment_scores = {
            "positive": float(probs[0]),
            "negative": float(probs[1]),
            "neutral": float(probs[2]),
        }

        # Determine overall sentiment
        max_label = max(sentiment_scores, key=sentiment_scores.get)
        max_score = sentiment_scores[max_label]

        # Calculate compound score (-1 to 1)
        compound = sentiment_scores["positive"] - sentiment_scores["negative"]

        return {
            "model": "finbert",
            "label": max_label,
            "confidence": max_score,
            "compound": compound,
            "scores": sentiment_scores,
        }

    def _analyze_with_vader(self, text: str) -> dict[str, Any]:
        """Analyze sentiment using VADER."""
        analyzer = _load_vader()

        scores = analyzer.polarity_scores(text)

        # Determine label
        compound = scores["compound"]
        if compound >= 0.05:
            label = "positive"
        elif compound <= -0.05:
            label = "negative"
        else:
            label = "neutral"

        return {
            "model": "vader",
            "label": label,
            "confidence": abs(compound),
            "compound": compound,
            "scores": {
                "positive": scores["pos"],
                "negative": scores["neg"],
                "neutral": scores["neu"],
            },
        }

    async def analyze_text(self, text: str) -> dict[str, Any]:
        """Analyze sentiment of a single text."""
        if not text or not text.strip():
            return {
                "error": "Empty text provided",
                "label": "neutral",
                "compound": 0,
            }

        # Check cache
        cache_key = f"text_{hash(text)}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            if self.config.model == "finbert":
                result = self._analyze_with_finbert(text)
            else:
                result = self._analyze_with_vader(text)

            result["text_preview"] = text[:100] + "..." if len(text) > 100 else text
            self._cache[cache_key] = result
            return result

        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")

            # Fallback to VADER if FinBERT fails
            if self.config.model == "finbert":
                logger.info("Falling back to VADER")
                try:
                    result = self._analyze_with_vader(text)
                    result["fallback"] = True
                    return result
                except Exception as e2:
                    logger.error(f"VADER fallback also failed: {e2}")

            return {
                "error": str(e),
                "label": "neutral",
                "compound": 0,
            }

    async def analyze_news_sentiment(
        self,
        news_items: list[dict[str, Any]],
        symbol: str | None = None,
    ) -> dict[str, Any]:
        """Analyze sentiment across multiple news articles."""
        if not news_items:
            return {
                "symbol": symbol,
                "error": "No news items provided",
                "overall_sentiment": "neutral",
                "compound": 0,
                "articles_analyzed": 0,
            }

        results = []
        total_compound = 0
        sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}

        for item in news_items:
            # Combine headline and summary for analysis
            text = ""
            if item.get("headline"):
                text += item["headline"] + ". "
            if item.get("summary"):
                text += item["summary"]

            if not text.strip():
                continue

            sentiment = await self.analyze_text(text)

            results.append({
                "headline": item.get("headline"),
                "source": item.get("source"),
                "datetime": item.get("datetime"),
                "sentiment": sentiment["label"],
                "compound": sentiment["compound"],
                "confidence": sentiment.get("confidence", 0),
            })

            total_compound += sentiment["compound"]
            sentiment_counts[sentiment["label"]] += 1

        # Calculate overall sentiment
        if results:
            avg_compound = total_compound / len(results)
            if avg_compound >= 0.05:
                overall = "positive"
            elif avg_compound <= -0.05:
                overall = "negative"
            else:
                overall = "neutral"
        else:
            avg_compound = 0
            overall = "neutral"

        return {
            "symbol": symbol,
            "model": self.config.model,
            "overall_sentiment": overall,
            "compound": avg_compound,
            "sentiment_distribution": sentiment_counts,
            "articles_analyzed": len(results),
            "articles": results,
        }

    async def batch_analyze(self, texts: list[str]) -> list[dict[str, Any]]:
        """Analyze sentiment for multiple texts."""
        results = []
        for text in texts:
            result = await self.analyze_text(text)
            results.append(result)
        return results
