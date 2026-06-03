# ace/src/sentiment/scraper.py

from __future__ import annotations

import logging
from typing import Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import settings


logger = logging.getLogger(__name__)


class ScraperError(Exception):
    """Base scraper exception."""


class TwitterScraperError(ScraperError):
    """Twitter scraping failure."""


class CryptoPanicScraperError(ScraperError):
    """CryptoPanic scraping failure."""


class SentimentScraper:
    """
    Unified sentiment data collector.

    Sources:
    - Twitter/X (via SerpAPI)
    - CryptoPanic

    This class does NOT perform sentiment analysis.

    Responsibilities:
    - Collect raw social posts
    - Collect raw news headlines
    - Normalize output
    - Return structured data for Ace LLM processing
    """

    SERPAPI_URL = "https://serpapi.com/search"
    CRYPTOPANIC_URL = "https://cryptopanic.com/api/v1/posts/"

    DEFAULT_TIMEOUT = 30

    def __init__(self) -> None:

        self.serpapi_key = settings.SERPAPI_API_KEY
        self.cryptopanic_key = settings.CRYPTOPANIC_API_KEY

        self.session = self._build_session()

    def _build_session(self) -> requests.Session:
        """
        Production-grade HTTP session
        with retries and backoff.
        """

        session = requests.Session()

        retries = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[
                429,
                500,
                502,
                503,
                504,
            ],
            allowed_methods=[
                "GET",
            ],
        )

        adapter = HTTPAdapter(
            max_retries=retries
        )

        session.mount(
            "https://",
            adapter
        )

        session.mount(
            "http://",
            adapter
        )

        return session

    # =====================================================
    # TWITTER / X
    # =====================================================

    def fetch_twitter_posts(
        self,
        coin_name: str,
        max_results: int = 30,
    ) -> List[Dict]:
        """
        Fetch Twitter/X discussions using SerpAPI.

        Returns:
            [
                {
                    "source": "twitter",
                    "content": "...",
                }
            ]
        """

        try:

            query = f"{coin_name} crypto site:twitter.com"

            params = {
                "engine": "google",
                "q": query,
                "api_key": self.serpapi_key,
                "num": max_results,
                "hl": "en",
                "gl": "us",
            }

            response = self.session.get(
                self.SERPAPI_URL,
                params=params,
                timeout=self.DEFAULT_TIMEOUT,
            )

            response.raise_for_status()

            data = response.json()

            posts: List[Dict] = []

            for item in data.get(
                "organic_results",
                []
            ):

                title = item.get(
                    "title",
                    ""
                )

                snippet = item.get(
                    "snippet",
                    ""
                )

                content = (
                    f"{title} {snippet}"
                ).strip()

                if not content:
                    continue

                posts.append(
                    {
                        "source": "twitter",
                        "content": content,
                    }
                )

            logger.info(
                "Fetched %s Twitter posts for %s",
                len(posts),
                coin_name,
            )

            return posts

        except Exception as exc:

            logger.exception(
                "Twitter scraping failed: %s",
                exc,
            )

            raise TwitterScraperError(
                str(exc)
            ) from exc

    # =====================================================
    # CRYPTOPANIC
    # =====================================================

    def fetch_news(
        self,
        coin_name: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict]:
        """
        Fetch CryptoPanic news.

        Returns:
            [
                {
                    "source": "cryptopanic",
                    "title": "...",
                    "summary": "...",
                    "url": "...",
                    "published_at": "...",
                }
            ]
        """

        try:

            params = {
                "auth_token": self.cryptopanic_key,
                "public": "true",
                "kind": "news",
            }

            response = self.session.get(
                self.CRYPTOPANIC_URL,
                params=params,
                timeout=self.DEFAULT_TIMEOUT,
            )

            response.raise_for_status()

            payload = response.json()

            results = payload.get(
                "results",
                []
            )

            news_items: List[Dict] = []

            for article in results:

                title = article.get(
                    "title",
                    ""
                )

                summary = article.get(
                    "slug",
                    ""
                )

                if coin_name:

                    text = (
                        f"{title} {summary}"
                    ).lower()

                    if coin_name.lower() not in text:
                        continue

                news_items.append(
                    {
                        "source": "cryptopanic",
                        "title": title,
                        "summary": summary,
                        "url": article.get("url"),
                        "published_at": article.get(
                            "published_at"
                        ),
                    }
                )

                if len(news_items) >= limit:
                    break

            logger.info(
                "Fetched %s CryptoPanic articles for %s",
                len(news_items),
                coin_name,
            )

            return news_items

        except Exception as exc:

            logger.exception(
                "CryptoPanic scraping failed: %s",
                exc,
            )

            raise CryptoPanicScraperError(
                str(exc)
            ) from exc

    # =====================================================
    # COMBINED FEED
    # =====================================================

    def collect(
        self,
        coin_name: str,
        twitter_limit: int = 30,
        news_limit: int = 20,
    ) -> Dict:
        """
        Unified collection entrypoint.

        Returns:
        {
            "coin": "SOL",
            "twitter_posts": [...],
            "news_articles": [...]
        }
        """

        twitter_posts = self.fetch_twitter_posts(
            coin_name=coin_name,
            max_results=twitter_limit,
        )

        news_articles = self.fetch_news(
            coin_name=coin_name,
            limit=news_limit,
        )

        return {
            "coin": coin_name,
            "twitter_posts": twitter_posts,
            "news_articles": news_articles,
        }