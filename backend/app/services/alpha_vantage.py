"""Alpha Vantage integration for stock market data."""
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import requests
from loguru import logger

from ..config import get_settings
from ..utils import get_redis_client


@dataclass
class StockQuote:
    """Current stock quote data."""
    symbol: str
    price: float
    change: float
    change_percent: float
    volume: int
    latest_trading_day: str
    previous_close: float
    open_price: float
    high: float
    low: float
    timestamp: datetime

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "price": self.price,
            "change": self.change,
            "change_percent": self.change_percent,
            "volume": self.volume,
            "latest_trading_day": self.latest_trading_day,
            "previous_close": self.previous_close,
            "open": self.open_price,
            "high": self.high,
            "low": self.low,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class CompanyOverview:
    """Company fundamental data."""
    symbol: str
    name: str
    description: str
    sector: str
    industry: str
    market_cap: int
    pe_ratio: Optional[float]
    dividend_yield: Optional[float]
    eps: Optional[float]
    fifty_two_week_high: float
    fifty_two_week_low: float
    analyst_target_price: Optional[float]

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "description": self.description,
            "sector": self.sector,
            "industry": self.industry,
            "market_cap": self.market_cap,
            "pe_ratio": self.pe_ratio,
            "dividend_yield": self.dividend_yield,
            "eps": self.eps,
            "52_week_high": self.fifty_two_week_high,
            "52_week_low": self.fifty_two_week_low,
            "analyst_target_price": self.analyst_target_price
        }


@dataclass
class PricePoint:
    """Single price data point."""
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int

    def to_dict(self) -> Dict:
        return {
            "date": self.date,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume
        }


class AlphaVantageClient:
    """Client for Alpha Vantage API with rate limiting and caching."""

    BASE_URL = "https://www.alphavantage.co/query"

    # Rate limits: 5 requests/minute, 25 requests/day (free tier)
    REQUESTS_PER_MINUTE = 5
    REQUESTS_PER_DAY = 25

    # Cache TTLs (in seconds)
    QUOTE_CACHE_TTL = 60  # 1 minute for quotes
    DAILY_CACHE_TTL = 3600  # 1 hour for daily data
    OVERVIEW_CACHE_TTL = 86400  # 24 hours for company info

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.ALPHAVANTAGE_KEY
        self._request_times: List[datetime] = []
        self._daily_count = 0
        self._daily_reset = datetime.utcnow().date()

    def _check_rate_limit(self) -> bool:
        """Check and enforce rate limits."""
        now = datetime.utcnow()
        today = now.date()

        # Reset daily counter if new day
        if today > self._daily_reset:
            self._daily_count = 0
            self._daily_reset = today

        # Check daily limit
        if self._daily_count >= self.REQUESTS_PER_DAY:
            logger.warning("Alpha Vantage daily rate limit reached")
            return False

        # Check per-minute limit
        one_minute_ago = now - timedelta(minutes=1)
        self._request_times = [t for t in self._request_times if t > one_minute_ago]

        if len(self._request_times) >= self.REQUESTS_PER_MINUTE:
            wait_time = (self._request_times[0] + timedelta(minutes=1) - now).total_seconds()
            if wait_time > 0:
                logger.info(f"Rate limit: waiting {wait_time:.1f}s")
                time.sleep(wait_time)

        return True

    def _make_request(self, params: Dict) -> Optional[Dict]:
        """Make API request with rate limiting."""
        if not self.api_key:
            logger.error("ALPHAVANTAGE_KEY not configured")
            return None

        if not self._check_rate_limit():
            return None

        params["apikey"] = self.api_key

        try:
            self._request_times.append(datetime.utcnow())
            self._daily_count += 1

            response = requests.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Check for API error messages
            if "Error Message" in data:
                logger.error(f"Alpha Vantage error: {data['Error Message']}")
                return None
            if "Note" in data:
                logger.warning(f"Alpha Vantage note: {data['Note']}")
                return None

            return data

        except requests.RequestException as e:
            logger.error(f"Alpha Vantage request failed: {e}")
            return None

    def get_quote(self, symbol: str) -> Optional[StockQuote]:
        """Get current stock quote."""
        redis = get_redis_client()
        cache_key = f"av:quote:{symbol.upper()}"

        # Check cache first
        cached = redis.cache_get(cache_key)
        if cached:
            cached["timestamp"] = datetime.fromisoformat(cached["timestamp"])
            return StockQuote(**cached)

        # Fetch from API
        data = self._make_request({
            "function": "GLOBAL_QUOTE",
            "symbol": symbol
        })

        if not data or "Global Quote" not in data:
            return None

        quote_data = data["Global Quote"]
        if not quote_data:
            logger.warning(f"No quote data for {symbol}")
            return None

        try:
            quote = StockQuote(
                symbol=quote_data.get("01. symbol", symbol),
                price=float(quote_data.get("05. price", 0)),
                change=float(quote_data.get("09. change", 0)),
                change_percent=float(quote_data.get("10. change percent", "0%").rstrip("%")),
                volume=int(quote_data.get("06. volume", 0)),
                latest_trading_day=quote_data.get("07. latest trading day", ""),
                previous_close=float(quote_data.get("08. previous close", 0)),
                open_price=float(quote_data.get("02. open", 0)),
                high=float(quote_data.get("03. high", 0)),
                low=float(quote_data.get("04. low", 0)),
                timestamp=datetime.utcnow()
            )

            # Cache the result
            redis.cache_set(cache_key, quote.to_dict(), self.QUOTE_CACHE_TTL)

            return quote

        except (ValueError, KeyError) as e:
            logger.error(f"Failed to parse quote for {symbol}: {e}")
            return None

    def get_daily_prices(
        self,
        symbol: str,
        days: int = 30,
        full: bool = False
    ) -> List[PricePoint]:
        """Get daily historical prices."""
        redis = get_redis_client()
        cache_key = f"av:daily:{symbol.upper()}:{days}"

        # Check cache
        cached = redis.cache_get(cache_key)
        if cached:
            return [PricePoint(**p) for p in cached]

        # Fetch from API
        data = self._make_request({
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "outputsize": "full" if full or days > 100 else "compact"
        })

        if not data or "Time Series (Daily)" not in data:
            return []

        time_series = data["Time Series (Daily)"]
        prices = []

        for date_str, values in sorted(time_series.items(), reverse=True)[:days]:
            try:
                prices.append(PricePoint(
                    date=date_str,
                    open=float(values["1. open"]),
                    high=float(values["2. high"]),
                    low=float(values["3. low"]),
                    close=float(values["4. close"]),
                    volume=int(values["5. volume"])
                ))
            except (ValueError, KeyError) as e:
                logger.warning(f"Failed to parse price for {date_str}: {e}")
                continue

        # Cache results
        if prices:
            redis.cache_set(cache_key, [p.to_dict() for p in prices], self.DAILY_CACHE_TTL)

        return prices

    def get_company_overview(self, symbol: str) -> Optional[CompanyOverview]:
        """Get company fundamental data."""
        redis = get_redis_client()
        cache_key = f"av:overview:{symbol.upper()}"

        # Check cache
        cached = redis.cache_get(cache_key)
        if cached:
            return CompanyOverview(**cached)

        # Fetch from API
        data = self._make_request({
            "function": "OVERVIEW",
            "symbol": symbol
        })

        if not data or "Symbol" not in data:
            return None

        try:
            def safe_float(val, default=None):
                try:
                    return float(val) if val and val != "None" else default
                except ValueError:
                    return default

            def safe_int(val, default=0):
                try:
                    return int(val) if val and val != "None" else default
                except ValueError:
                    return default

            overview = CompanyOverview(
                symbol=data.get("Symbol", symbol),
                name=data.get("Name", ""),
                description=data.get("Description", ""),
                sector=data.get("Sector", ""),
                industry=data.get("Industry", ""),
                market_cap=safe_int(data.get("MarketCapitalization")),
                pe_ratio=safe_float(data.get("PERatio")),
                dividend_yield=safe_float(data.get("DividendYield")),
                eps=safe_float(data.get("EPS")),
                fifty_two_week_high=safe_float(data.get("52WeekHigh"), 0),
                fifty_two_week_low=safe_float(data.get("52WeekLow"), 0),
                analyst_target_price=safe_float(data.get("AnalystTargetPrice"))
            )

            # Cache result
            redis.cache_set(cache_key, overview.to_dict(), self.OVERVIEW_CACHE_TTL)

            return overview

        except Exception as e:
            logger.error(f"Failed to parse overview for {symbol}: {e}")
            return None

    def get_intraday_prices(
        self,
        symbol: str,
        interval: str = "15min"
    ) -> List[Dict[str, Any]]:
        """Get intraday prices (uses more API calls)."""
        data = self._make_request({
            "function": "TIME_SERIES_INTRADAY",
            "symbol": symbol,
            "interval": interval,
            "outputsize": "compact"
        })

        key = f"Time Series ({interval})"
        if not data or key not in data:
            return []

        time_series = data[key]
        prices = []

        for timestamp, values in sorted(time_series.items(), reverse=True):
            try:
                prices.append({
                    "timestamp": timestamp,
                    "open": float(values["1. open"]),
                    "high": float(values["2. high"]),
                    "low": float(values["3. low"]),
                    "close": float(values["4. close"]),
                    "volume": int(values["5. volume"])
                })
            except (ValueError, KeyError):
                continue

        return prices

    def search_symbol(self, keywords: str) -> List[Dict[str, str]]:
        """Search for stock symbols by company name."""
        data = self._make_request({
            "function": "SYMBOL_SEARCH",
            "keywords": keywords
        })

        if not data or "bestMatches" not in data:
            return []

        results = []
        for match in data["bestMatches"]:
            results.append({
                "symbol": match.get("1. symbol", ""),
                "name": match.get("2. name", ""),
                "type": match.get("3. type", ""),
                "region": match.get("4. region", ""),
                "currency": match.get("8. currency", "")
            })

        return results


# Singleton instance
_alpha_vantage_client: Optional[AlphaVantageClient] = None


def get_alpha_vantage_client() -> AlphaVantageClient:
    """Get singleton Alpha Vantage client instance."""
    global _alpha_vantage_client
    if _alpha_vantage_client is None:
        _alpha_vantage_client = AlphaVantageClient()
    return _alpha_vantage_client
