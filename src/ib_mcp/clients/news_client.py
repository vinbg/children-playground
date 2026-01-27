"""News API Client for Finnhub."""

import logging
from datetime import datetime, timedelta
from typing import Any

import aiohttp
from cachetools import TTLCache

from ..config import NewsConfig

logger = logging.getLogger(__name__)


class NewsClient:
    """Client for fetching financial news from Finnhub."""

    FINNHUB_BASE_URL = "https://finnhub.io/api/v1"

    def __init__(self, config: NewsConfig):
        self.config = config
        self._cache = TTLCache(maxsize=1000, ttl=config.cache_ttl)
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    def check_api_keys(self) -> dict[str, Any]:
        """Check which API keys are configured."""
        return {
            "finnhub": {
                "configured": bool(self.config.finnhub_api_key),
                "status": "ready" if self.config.finnhub_api_key else "missing",
            },
        }

    async def _finnhub_request(self, endpoint: str, params: dict[str, Any] = None) -> dict[str, Any]:
        """Make a request to Finnhub API."""
        if not self.config.finnhub_api_key:
            raise ValueError("Finnhub API key not configured. Set FINNHUB_API_KEY in .env")

        session = await self._get_session()
        url = f"{self.FINNHUB_BASE_URL}/{endpoint}"

        params = params or {}
        params["token"] = self.config.finnhub_api_key

        try:
            async with session.get(url, params=params) as response:
                if response.status == 401:
                    raise ValueError("Invalid Finnhub API key")
                elif response.status == 429:
                    raise ValueError("Finnhub rate limit exceeded. Please wait and try again.")
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"Finnhub request failed: {e}")
            raise

    async def get_company_news(
        self, symbol: str, limit: int = 10
    ) -> dict[str, Any]:
        """Get company-specific news from Finnhub."""
        cache_key = f"company_news_{symbol}_{limit}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Finnhub requires date range
        to_date = datetime.now().strftime("%Y-%m-%d")
        from_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        try:
            data = await self._finnhub_request(
                "company-news",
                {"symbol": symbol.upper(), "from": from_date, "to": to_date}
            )

            articles = []
            for item in data[:limit]:
                articles.append({
                    "headline": item.get("headline"),
                    "summary": item.get("summary"),
                    "source": item.get("source"),
                    "url": item.get("url"),
                    "datetime": datetime.fromtimestamp(item.get("datetime", 0)).isoformat()
                    if item.get("datetime")
                    else None,
                    "category": item.get("category"),
                    "related": item.get("related"),
                })

            result = {
                "symbol": symbol.upper(),
                "source": "finnhub",
                "articles": articles,
                "count": len(articles),
                "timestamp": datetime.now().isoformat(),
            }

            self._cache[cache_key] = result
            return result

        except Exception as e:
            logger.error(f"Failed to get company news for {symbol}: {e}")
            return {
                "symbol": symbol.upper(),
                "error": str(e),
                "articles": [],
                "count": 0,
            }

    async def get_market_news(
        self, category: str = "general", limit: int = 10
    ) -> dict[str, Any]:
        """Get general market news from Finnhub."""
        cache_key = f"market_news_{category}_{limit}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            data = await self._finnhub_request(
                "news",
                {"category": category}
            )

            articles = []
            for item in data[:limit]:
                articles.append({
                    "headline": item.get("headline"),
                    "summary": item.get("summary"),
                    "source": item.get("source"),
                    "url": item.get("url"),
                    "datetime": datetime.fromtimestamp(item.get("datetime", 0)).isoformat()
                    if item.get("datetime")
                    else None,
                    "category": item.get("category"),
                })

            result = {
                "category": category,
                "source": "finnhub",
                "articles": articles,
                "count": len(articles),
                "timestamp": datetime.now().isoformat(),
            }

            self._cache[cache_key] = result
            return result

        except Exception as e:
            logger.error(f"Failed to get market news: {e}")
            return {
                "error": str(e),
                "category": category,
                "articles": [],
                "count": 0,
            }

    async def search_news(
        self,
        symbol: str | None = None,
        keywords: str | None = None,
        category: str = "general",
        from_date: str | None = None,
        to_date: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Search news by symbol or keywords."""
        if symbol:
            return await self.get_company_news(symbol, limit)
        else:
            return await self.get_market_news(category, limit)

    async def get_social_sentiment(self, symbol: str) -> dict[str, Any]:
        """Get social media sentiment from Finnhub."""
        cache_key = f"social_sentiment_{symbol}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            data = await self._finnhub_request(
                "stock/social-sentiment",
                {"symbol": symbol.upper()}
            )

            result = {
                "symbol": symbol.upper(),
                "source": "finnhub",
                "reddit": data.get("reddit", []),
                "twitter": data.get("twitter", []),
                "timestamp": datetime.now().isoformat(),
            }

            # Calculate aggregate sentiment
            reddit_data = data.get("reddit", [])
            twitter_data = data.get("twitter", [])

            if reddit_data:
                result["reddit_summary"] = {
                    "total_mentions": sum(r.get("mention", 0) for r in reddit_data),
                    "positive_mentions": sum(r.get("positiveMention", 0) for r in reddit_data),
                    "negative_mentions": sum(r.get("negativeMention", 0) for r in reddit_data),
                }

            if twitter_data:
                result["twitter_summary"] = {
                    "total_mentions": sum(t.get("mention", 0) for t in twitter_data),
                    "positive_mentions": sum(t.get("positiveMention", 0) for t in twitter_data),
                    "negative_mentions": sum(t.get("negativeMention", 0) for t in twitter_data),
                }

            self._cache[cache_key] = result
            return result

        except Exception as e:
            logger.error(f"Failed to get social sentiment for {symbol}: {e}")
            return {
                "symbol": symbol.upper(),
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def get_insider_sentiment(self, symbol: str) -> dict[str, Any]:
        """Get insider trading sentiment from Finnhub."""
        cache_key = f"insider_sentiment_{symbol}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            data = await self._finnhub_request(
                "stock/insider-sentiment",
                {"symbol": symbol.upper()}
            )

            result = {
                "symbol": symbol.upper(),
                "source": "finnhub",
                "data": data.get("data", []),
                "timestamp": datetime.now().isoformat(),
            }

            # Calculate summary
            insider_data = data.get("data", [])
            if insider_data:
                recent = insider_data[-1] if insider_data else {}
                result["summary"] = {
                    "mspr": recent.get("mspr"),  # Monthly Share Purchase Ratio
                    "change": recent.get("change"),
                    "period": recent.get("month"),
                }

            self._cache[cache_key] = result
            return result

        except Exception as e:
            logger.error(f"Failed to get insider sentiment for {symbol}: {e}")
            return {
                "symbol": symbol.upper(),
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }
