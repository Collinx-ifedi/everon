"""
sentiment_utils.py

Production-grade sentiment analysis module.

Features:
- TextBlob-based sentiment scoring
- Crypto sentiment classification
- Reddit/Twitter/News aggregation support
- No LLM dependency
- No API cost
- Fast execution
"""

import re
import sys
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from textblob import TextBlob

# --------------------------------------------------
# PATH SETUP
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# --------------------------------------------------
# LOGGER
# --------------------------------------------------

try:
    from utils.logger import get_logger
    logger = get_logger("SentimentUtils")
except Exception:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    logger = logging.getLogger("SentimentUtils")

# --------------------------------------------------
# SCRAPERS
# --------------------------------------------------
try:
    from src.sentiment.scraper import SentimentScraper

except Exception as e:
    logger.warning(
        f"Could not import SentimentScraper: {e}"
    )

    SentimentScraper = None

# ==================================================
# TEXT CLEANING
# ==================================================

def clean_text(text: str) -> str:
    """
    Clean social/news text before sentiment analysis.
    """

    if not isinstance(text, str):
        return ""

    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"www\S+", "", text)

    text = re.sub(r"@\w+", "", text)

    text = re.sub(r"#", "", text)

    text = re.sub(
        r"[^\w\s\.,!\?\$\%\+\-\(\)]",
        "",
        text
    )

    return text.strip()


# ==================================================
# SENTIMENT MAPPING
# ==================================================

def classify_sentiment(score: float) -> str:
    """
    Convert polarity score into crypto sentiment.
    """

    if score >= 0.50:
        return "bullish"

    if score >= 0.10:
        return "mini bullish"

    if score <= -0.50:
        return "bearish"

    if score <= -0.10:
        return "mini bearish"

    return "neutral"


# ==================================================
# TEXTBLOB SENTIMENT
# ==================================================

def hybrid_sentiment(text: str) -> Dict[str, Any]:
    """
    Main sentiment analysis function.

    Returns:
    {
        score: float,
        category: str,
        confidence: float,
        error: None
    }
    """

    try:

        cleaned_text = clean_text(text)

        if not cleaned_text:

            return {
                "score": 0.0,
                "category": "neutral",
                "confidence": 0.0,
                "error": "Empty text"
            }

        blob = TextBlob(cleaned_text)

        polarity = float(blob.sentiment.polarity)

        subjectivity = float(blob.sentiment.subjectivity)

        category = classify_sentiment(polarity)

        confidence = round(abs(polarity), 3)

        return {
            "score": round(polarity, 4),
            "category": category,
            "confidence": confidence,
            "subjectivity": round(subjectivity, 4),
            "error": None
        }

    except Exception as e:

        logger.exception(
            f"Sentiment analysis failed: {e}"
        )

        return {
            "score": 0.0,
            "category": "neutral",
            "confidence": 0.0,
            "error": str(e)
        }


# ==================================================
# AGGREGATION HELPERS
# ==================================================

def calculate_average_sentiment(
    items: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Aggregate sentiment results.
    """

    if not items:

        return {
            "average_score": 0.0,
            "category": "neutral",
            "sample_size": 0
        }

    scores = [
        item.get("sentiment_score", 0.0)
        for item in items
    ]

    avg_score = sum(scores) / len(scores)

    return {
        "average_score": round(avg_score, 4),
        "category": classify_sentiment(avg_score),
        "sample_size": len(scores)
    }


# ==================================================
# SENTIMENT AGGREGATOR
# ==================================================

class SentimentAggregator:
    """
    Production sentiment aggregation layer.

    Uses:
    - Twitter/X (SerpAPI)
    - CryptoPanic

    via unified SentimentScraper.
    """

    def __init__(self):

        self.scraper = None

        try:

            if SentimentScraper:
                self.scraper = SentimentScraper()

            logger.info(
                "SentimentAggregator initialized."
            )

        except Exception as e:

            logger.exception(
                f"Failed to initialize SentimentScraper: {e}"
            )

    def get_sentiment_data(
        self,
        coin_name: str,
        limit: int = 20
    ) -> Dict[str, Any]:

        logger.info(
            f"Collecting sentiment for {coin_name}"
        )

        result = {
            "coin": coin_name,
            "twitter": [],
            "news": [],
            "summary": {},
            "error": None
        }

        try:

            if not self.scraper:

                result["error"] = (
                    "SentimentScraper unavailable"
                )

                return result

            raw_data = self.scraper.collect(
                coin_name=coin_name,
                twitter_limit=limit,
                news_limit=limit
            )

            twitter_posts = raw_data.get(
                "twitter_posts",
                []
            )

            news_articles = raw_data.get(
                "news_articles",
                []
            )

            result["twitter"] = (
                self._analyze_items(
                    twitter_posts,
                    "content"
                )
            )

            result["news"] = (
                self._analyze_items(
                    news_articles,
                    "title"
                )
            )

            combined = (
                result["twitter"]
                + result["news"]
            )

            result["summary"] = (
                calculate_average_sentiment(
                    combined
                )
            )

            return result

        except Exception as e:

            logger.exception(
                f"Aggregation error for {coin_name}"
            )

            result["error"] = str(e)

            return result

    def _analyze_items(
        self,
        items: List[Dict[str, Any]],
        field: str
    ) -> List[Dict[str, Any]]:

        analyzed = []

        for item in items:

            try:

                text = item.get(
                    field,
                    ""
                )

                sentiment = hybrid_sentiment(
                    text
                )

                item[
                    "sentiment_analysis"
                ] = sentiment

                item[
                    "sentiment_score"
                ] = sentiment["score"]

                item[
                    "sentiment_category"
                ] = sentiment["category"]

                item[
                    "confidence"
                ] = sentiment["confidence"]

                analyzed.append(item)

            except Exception as e:

                logger.error(
                    f"Failed analyzing item: {e}"
                )

        return analyzed

# ==================================================
# CLI TEST
# ==================================================

if __name__ == "__main__":

    examples = [
        "Bitcoin is exploding higher and institutions are buying.",
        "ETH looks good but there is some resistance ahead.",
        "The market is trading sideways.",
        "Traders are becoming worried after the selloff.",
        "Everything is crashing hard."
    ]

    print("\nTEXTBLOB SENTIMENT TEST\n")

    for text in examples:

        result = hybrid_sentiment(text)

        print(f"TEXT: {text}")
        print(
            f"SCORE: {result['score']} | "
            f"CATEGORY: {result['category']} | "
            f"CONFIDENCE: {result['confidence']}"
        )
        print("-" * 60)