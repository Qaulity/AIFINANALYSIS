"""Yahoo Finance and Finnhub integration for market data."""
import yfinance as yf
import pandas as pd
import requests
import time
import random
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from loguru import logger

from ..utils import get_redis_client
from ..config import get_settings


# Major market indices
MARKET_INDICES = {
    "^DJI": {"name": "Dow Jones", "short": "DOW"},
    "^GSPC": {"name": "S&P 500", "short": "S&P"},
    "^IXIC": {"name": "NASDAQ", "short": "NASDAQ"},
    "^RUT": {"name": "Russell 2000", "short": "RUT"},
    "^VIX": {"name": "VIX Volatility", "short": "VIX"},
}

# Popular ETFs for quick access
POPULAR_ETFS = ["SPY", "QQQ", "IWM", "DIA", "VTI", "VOO", "ARKK", "XLF", "XLE", "XLK"]

# Fallback sample data when API is rate limited (approximate market values for demo)
SAMPLE_INDEX_DATA = {
    "^DJI": {"price": 44565.07, "prev": 44424.25, "open": 44450.00, "high": 44620.50, "low": 44380.00},
    "^GSPC": {"price": 6118.71, "prev": 6086.37, "open": 6090.00, "high": 6125.00, "low": 6075.00},
    "^IXIC": {"price": 20053.06, "prev": 19954.30, "open": 19980.00, "high": 20100.00, "low": 19920.00},
    "^RUT": {"price": 2312.55, "prev": 2298.46, "open": 2300.00, "high": 2320.00, "low": 2290.00},
    "^VIX": {"price": 14.85, "prev": 15.10, "open": 15.05, "high": 15.25, "low": 14.70},
}

SAMPLE_STOCK_DATA = {
    "AAPL": {"price": 229.87, "prev": 228.50, "name": "Apple Inc."},
    "MSFT": {"price": 443.52, "prev": 441.20, "name": "Microsoft Corporation"},
    "GOOGL": {"price": 195.89, "prev": 194.30, "name": "Alphabet Inc."},
    "AMZN": {"price": 229.15, "prev": 227.50, "name": "Amazon.com Inc."},
    "TSLA": {"price": 412.38, "prev": 408.75, "name": "Tesla Inc."},
    "META": {"price": 632.25, "prev": 628.00, "name": "Meta Platforms Inc."},
    "NVDA": {"price": 142.62, "prev": 140.50, "name": "NVIDIA Corporation"},
    "AMD": {"price": 123.45, "prev": 122.10, "name": "Advanced Micro Devices"},
    "NFLX": {"price": 952.38, "prev": 948.00, "name": "Netflix Inc."},
    "DIS": {"price": 112.85, "prev": 111.50, "name": "The Walt Disney Company"},
}


@dataclass
class MarketQuote:
    """Market quote data."""
    symbol: str
    name: str
    price: float
    change: float
    change_percent: float
    previous_close: float
    open_price: float
    day_high: float
    day_low: float
    volume: int
    market_cap: Optional[int]
    fifty_two_week_high: Optional[float]
    fifty_two_week_low: Optional[float]
    timestamp: datetime

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "price": self.price,
            "change": self.change,
            "change_percent": self.change_percent,
            "previous_close": self.previous_close,
            "open": self.open_price,
            "day_high": self.day_high,
            "day_low": self.day_low,
            "volume": self.volume,
            "market_cap": self.market_cap,
            "52_week_high": self.fifty_two_week_high,
            "52_week_low": self.fifty_two_week_low,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class HistoricalPrice:
    """Historical price point."""
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


class MarketDataService:
    """Fetches market data from Finnhub (search) and yfinance (quotes/history). Caches to Redis."""

    # cache TTLs in seconds
    QUOTE_CACHE_TTL = 120       # 2 min - live data
    HISTORY_CACHE_TTL = 1800    # 30 min - historical
    SEARCH_CACHE_TTL = 3600     # 1 hour - search results
    COMPANY_CACHE_TTL = 86400   # 24 hours - fundamentals
    INDICES_CACHE_TTL = 120     # 2 min - live data

    def __init__(self):
        self._cache_enabled = True

    def _get_cache_key(self, prefix: str, *args) -> str:
        """Generate cache key."""
        return f"yf:{prefix}:{':'.join(str(a) for a in args)}"

    def get_quote(self, symbol: str) -> Optional[MarketQuote]:
        """Get current quote for a symbol using fast_info for efficiency."""
        redis = get_redis_client()
        cache_key = self._get_cache_key("quote", symbol.upper())

        # Check cache
        if self._cache_enabled:
            cached = redis.cache_get(cache_key)
            if cached:
                cached["timestamp"] = datetime.fromisoformat(cached["timestamp"])
                return MarketQuote(**cached)

        try:
            ticker = yf.Ticker(symbol)

            # Use fast_info which makes fewer API calls
            fast = ticker.fast_info

            if not fast or fast.get("lastPrice") is None:
                logger.warning(f"No data for symbol: {symbol}")
                return None

            # Get name from history if available
            name = symbol.upper()
            try:
                hist = ticker.history(period="1d")
                if hasattr(ticker, '_short_name'):
                    name = ticker._short_name
            except Exception:
                pass

            last_price = fast.get("lastPrice", 0)
            prev_close = fast.get("previousClose", 0) or fast.get("regularMarketPreviousClose", 0)
            change = last_price - prev_close if prev_close else 0
            change_pct = (change / prev_close * 100) if prev_close else 0

            quote = MarketQuote(
                symbol=symbol.upper(),
                name=MARKET_INDICES.get(symbol.upper(), {}).get("name", name),
                price=last_price,
                change=round(change, 2),
                change_percent=round(change_pct, 2),
                previous_close=prev_close,
                open_price=fast.get("open", 0) or fast.get("regularMarketOpen", 0),
                day_high=fast.get("dayHigh", 0) or fast.get("regularMarketDayHigh", 0),
                day_low=fast.get("dayLow", 0) or fast.get("regularMarketDayLow", 0),
                volume=int(fast.get("lastVolume", 0) or fast.get("volume", 0) or 0),
                market_cap=fast.get("marketCap"),
                fifty_two_week_high=fast.get("fiftyTwoWeekHigh") or fast.get("yearHigh"),
                fifty_two_week_low=fast.get("fiftyTwoWeekLow") or fast.get("yearLow"),
                timestamp=datetime.utcnow()
            )

            # Cache result
            if self._cache_enabled:
                redis.cache_set(cache_key, quote.to_dict(), self.QUOTE_CACHE_TTL)

            return quote

        except Exception as e:
            logger.error(f"Failed to get quote for {symbol}: {e}")
            return None

    def get_multiple_quotes(self, symbols: List[str]) -> List[MarketQuote]:
        """Get quotes for multiple symbols efficiently using batch download."""
        redis = get_redis_client()
        quotes = []

        if not symbols:
            return quotes

        try:
            # Use download for batch data
            data = yf.download(
                symbols,
                period="2d",
                interval="1d",
                group_by="ticker",
                progress=False,
                threads=False
            )

            if data.empty:
                logger.warning("No data returned for multiple quotes")
                return quotes

            # Check if we have MultiIndex columns
            has_multi_index = isinstance(data.columns, pd.MultiIndex)

            for symbol in symbols:
                try:
                    symbol_upper = symbol.upper()

                    # Handle single vs multiple symbols
                    if has_multi_index:
                        if symbol_upper not in data.columns.get_level_values(0):
                            continue
                        ticker_data = data[symbol_upper]
                    else:
                        ticker_data = data

                    if ticker_data is None or ticker_data.empty:
                        continue

                    # Drop NaN values
                    ticker_data = ticker_data.dropna(subset=["Close"])
                    if ticker_data.empty:
                        continue

                    recent = ticker_data.tail(2)
                    if len(recent) < 1:
                        continue

                    last_row = recent.iloc[-1]
                    prev_close = float(recent.iloc[-2]["Close"]) if len(recent) > 1 else float(last_row["Open"])

                    price = float(last_row["Close"])
                    change = price - prev_close
                    change_pct = (change / prev_close * 100) if prev_close else 0

                    quote = MarketQuote(
                        symbol=symbol_upper,
                        name=symbol_upper,  # Name lookup would require extra API calls
                        price=round(price, 2),
                        change=round(change, 2),
                        change_percent=round(change_pct, 2),
                        previous_close=round(prev_close, 2),
                        open_price=round(float(last_row["Open"]), 2),
                        day_high=round(float(last_row["High"]), 2),
                        day_low=round(float(last_row["Low"]), 2),
                        volume=int(last_row["Volume"]) if not pd.isna(last_row["Volume"]) else 0,
                        market_cap=None,
                        fifty_two_week_high=None,
                        fifty_two_week_low=None,
                        timestamp=datetime.utcnow()
                    )
                    quotes.append(quote)

                except Exception as e:
                    logger.warning(f"Failed to process quote for {symbol}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Failed to get multiple quotes: {e}")

        return quotes

    def _download_with_retry(self, symbols, period="2d", interval="1d", max_retries=3):
        """Download data with exponential backoff retry."""
        for attempt in range(max_retries):
            try:
                # Add random delay to avoid rate limiting
                if attempt > 0:
                    delay = (2 ** attempt) + random.uniform(0, 1)
                    logger.debug(f"Retry attempt {attempt + 1}, waiting {delay:.1f}s")
                    time.sleep(delay)

                data = yf.download(
                    symbols,
                    period=period,
                    interval=interval,
                    group_by="ticker" if isinstance(symbols, list) and len(symbols) > 1 else None,
                    progress=False,
                    threads=False
                )

                if not data.empty:
                    return data

            except Exception as e:
                logger.warning(f"Download attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise

        return pd.DataFrame()

    def _download_individually(self, symbols, period="2d", interval="1d"):
        """Download symbols one at a time with rate limit delays."""
        results = {}
        for symbol in symbols:
            try:
                # Add delay between requests
                time.sleep(random.uniform(0.5, 1.5))

                data = yf.download(
                    symbol,
                    period=period,
                    interval=interval,
                    progress=False,
                    threads=False
                )

                if not data.empty:
                    results[symbol] = data

            except Exception as e:
                logger.warning(f"Failed to download {symbol}: {e}")
                continue

        return results

    def get_market_indices(self) -> List[Dict]:
        """Get current data for major market indices using batch download."""
        redis = get_redis_client()
        cache_key = self._get_cache_key("indices")

        # Check cache first - use longer TTL for indices
        if self._cache_enabled:
            cached = redis.cache_get(cache_key)
            if cached:
                logger.debug("Returning cached indices data")
                return cached

        indices = []
        symbols = list(MARKET_INDICES.keys())

        try:
            # Try batch download first
            logger.debug(f"Downloading index data for: {symbols}")
            data = self._download_with_retry(symbols, period="2d", interval="1d")

            if data.empty:
                # Fallback: try downloading one at a time
                logger.info("Batch download failed, trying individual downloads")
                individual_data = self._download_individually(symbols, period="2d", interval="1d")

                for symbol, info in MARKET_INDICES.items():
                    if symbol in individual_data:
                        ticker_data = individual_data[symbol]
                        self._process_index_data(symbol, info, ticker_data, indices)

            else:
                # Process batch data
                has_multi_index = isinstance(data.columns, pd.MultiIndex)
                logger.debug(f"Data shape: {data.shape}, MultiIndex: {has_multi_index}")

                for symbol, info in MARKET_INDICES.items():
                    try:
                        if has_multi_index:
                            if symbol not in data.columns.get_level_values(0):
                                logger.debug(f"Symbol {symbol} not in data columns")
                                continue
                            ticker_data = data[symbol]
                        else:
                            ticker_data = data

                        self._process_index_data(symbol, info, ticker_data, indices)

                    except Exception as e:
                        logger.warning(f"Failed to process index {symbol}: {e}")
                        continue

            logger.debug(f"Successfully processed {len(indices)} indices")

        except Exception as e:
            logger.error(f"Failed to download indices: {e}")

        # If no indices were fetched, use sample data as fallback
        if not indices:
            logger.warning("Using sample data as fallback for market indices")
            indices = self._get_sample_indices()

        # Cache result with longer TTL to reduce API calls
        if self._cache_enabled and indices:
            redis.cache_set(cache_key, indices, self.INDICES_CACHE_TTL)

        return indices

    def _get_sample_indices(self) -> List[Dict]:
        """Return sample index data as fallback when API is unavailable."""
        indices = []
        for symbol, info in MARKET_INDICES.items():
            if symbol in SAMPLE_INDEX_DATA:
                sample = SAMPLE_INDEX_DATA[symbol]
                price = sample["price"]
                prev = sample["prev"]
                change = price - prev
                change_pct = (change / prev * 100) if prev else 0

                # Add slight randomization to make it look more realistic
                jitter = random.uniform(-0.1, 0.1) / 100
                price_adj = price * (1 + jitter)

                indices.append({
                    "symbol": symbol,
                    "name": info["name"],
                    "short_name": info["short"],
                    "display_name": info["name"],
                    "price": round(price_adj, 2),
                    "change": round(change, 2),
                    "change_percent": round(change_pct, 2),
                    "previous_close": round(prev, 2),
                    "open": round(sample["open"], 2),
                    "day_high": round(sample["high"], 2),
                    "day_low": round(sample["low"], 2),
                    "volume": random.randint(1000000, 5000000),
                    "market_cap": None,
                    "52_week_high": None,
                    "52_week_low": None,
                    "timestamp": datetime.utcnow().isoformat(),
                    "is_sample_data": True  # Flag to indicate sample data
                })
        return indices

    def _process_index_data(self, symbol: str, info: Dict, ticker_data: pd.DataFrame, indices: List[Dict]):
        """Process index data from a DataFrame and append to indices list."""
        if ticker_data is None or ticker_data.empty:
            return

        # Drop any rows with NaN in Close
        ticker_data = ticker_data.dropna(subset=["Close"])
        if ticker_data.empty:
            return

        # Get last two days for change calculation
        recent = ticker_data.tail(2)
        if len(recent) < 1:
            return

        last_row = recent.iloc[-1]
        prev_close = float(recent.iloc[-2]["Close"]) if len(recent) > 1 else float(last_row["Open"])

        price = float(last_row["Close"])
        change = price - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0

        indices.append({
            "symbol": symbol,
            "name": info["name"],
            "short_name": info["short"],
            "display_name": info["name"],
            "price": round(price, 2),
            "change": round(change, 2),
            "change_percent": round(change_pct, 2),
            "previous_close": round(prev_close, 2),
            "open": round(float(last_row["Open"]), 2),
            "day_high": round(float(last_row["High"]), 2),
            "day_low": round(float(last_row["Low"]), 2),
            "volume": int(last_row["Volume"]) if not pd.isna(last_row["Volume"]) else 0,
            "market_cap": None,
            "52_week_high": None,
            "52_week_low": None,
            "timestamp": datetime.utcnow().isoformat()
        })

    def get_historical_prices(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d"
    ) -> List[HistoricalPrice]:
        """Get historical prices. Period: 1d/5d/1mo/3mo/6mo/1y/2y/5y/max. Interval: 1m/5m/15m/30m/1h/1d/1wk/1mo."""
        redis = get_redis_client()
        cache_key = self._get_cache_key("history", symbol.upper(), period, interval)

        # Check cache
        if self._cache_enabled:
            cached = redis.cache_get(cache_key)
            if cached:
                return [HistoricalPrice(**p) for p in cached]

        prices = []  # Initialize before try block

        try:
            # Use download instead of Ticker.history - more reliable
            hist = yf.download(
                symbol,
                period=period,
                interval=interval,
                progress=False,
                threads=False
            )

            if not hist.empty:
                # Handle potential MultiIndex columns (shouldn't happen for single symbol, but be safe)
                if isinstance(hist.columns, pd.MultiIndex):
                    hist = hist[symbol.upper()] if symbol.upper() in hist.columns.get_level_values(0) else hist

                # Drop rows with NaN close prices
                hist = hist.dropna(subset=["Close"])

                for date, row in hist.iterrows():
                    try:
                        close_val = float(row["Close"])
                        if pd.isna(close_val):
                            continue

                        prices.append(HistoricalPrice(
                            date=date.strftime("%Y-%m-%d %H:%M") if interval in ["1m", "5m", "15m", "30m", "1h"] else date.strftime("%Y-%m-%d"),
                            open=round(float(row["Open"]), 2) if not pd.isna(row["Open"]) else round(close_val, 2),
                            high=round(float(row["High"]), 2) if not pd.isna(row["High"]) else round(close_val, 2),
                            low=round(float(row["Low"]), 2) if not pd.isna(row["Low"]) else round(close_val, 2),
                            close=round(close_val, 2),
                            volume=int(row["Volume"]) if not pd.isna(row["Volume"]) else 0
                        ))
                    except Exception as e:
                        logger.warning(f"Failed to parse row for {symbol}: {e}")
                        continue

        except Exception as e:
            logger.error(f"Failed to get history for {symbol}: {e}")

        # Return sample historical data if API fails
        if not prices:
            logger.warning(f"Using sample historical data for {symbol}")
            prices = self._generate_sample_history(symbol, period)

        # Cache result
        if self._cache_enabled and prices:
            redis.cache_set(cache_key, [p.to_dict() for p in prices], self.HISTORY_CACHE_TTL)

        return prices

    def _generate_sample_history(self, symbol: str, period: str = "1mo") -> List[HistoricalPrice]:
        """Generate sample historical price data."""
        # Determine number of days based on period
        period_days = {
            "5d": 5,
            "1mo": 22,
            "3mo": 66,
            "6mo": 132,
            "1y": 252,
        }
        days = period_days.get(period, 22)

        # Get base price from sample data or use default
        base_price = 100.0
        if symbol in SAMPLE_INDEX_DATA:
            base_price = SAMPLE_INDEX_DATA[symbol]["price"]
        elif symbol in SAMPLE_STOCK_DATA:
            base_price = SAMPLE_STOCK_DATA[symbol]["price"]

        prices = []
        current_price = base_price * 0.95  # Start slightly lower for upward trend

        for i in range(days):
            date = datetime.utcnow() - timedelta(days=days - i - 1)
            if date.weekday() >= 5:  # Skip weekends
                continue

            # Add realistic daily movement
            daily_change = random.uniform(-0.02, 0.025)
            current_price = current_price * (1 + daily_change)

            open_price = current_price * (1 + random.uniform(-0.005, 0.005))
            high_price = max(current_price, open_price) * (1 + random.uniform(0, 0.01))
            low_price = min(current_price, open_price) * (1 - random.uniform(0, 0.01))

            prices.append(HistoricalPrice(
                date=date.strftime("%Y-%m-%d"),
                open=round(open_price, 2),
                high=round(high_price, 2),
                low=round(low_price, 2),
                close=round(current_price, 2),
                volume=random.randint(1000000, 10000000)
            ))

        return prices

    def _finnhub_search(self, query: str, limit: int = 10) -> Optional[List[Dict]]:
        """Search via Finnhub API. Returns None if not configured or fails."""
        settings = get_settings()
        if not settings.FINNHUB_API_KEY:
            return None

        try:
            response = requests.get(
                "https://finnhub.io/api/v1/search",
                params={"q": query, "token": settings.FINNHUB_API_KEY},
                timeout=5
            )

            if response.status_code == 429:
                logger.warning("Finnhub rate limit hit")
                return None

            if response.status_code != 200:
                logger.warning(f"Finnhub search failed: {response.status_code}")
                return None

            data = response.json()
            results = []

            # Map Finnhub types to our types
            type_map = {
                "Common Stock": "EQUITY",
                "ADR": "EQUITY",
                "ETF": "ETF",
                "REIT": "EQUITY",
                "Unit": "EQUITY",
            }

            for item in data.get("result", [])[:limit]:
                symbol = item.get("symbol", "")
                # Filter out non-US symbols (they have dots like AAPL.SW)
                if "." in symbol and not symbol.startswith("^"):
                    continue

                finnhub_type = item.get("type", "Common Stock")
                results.append({
                    "symbol": symbol,
                    "name": item.get("description", symbol),
                    "type": type_map.get(finnhub_type, "EQUITY"),
                    "exchange": item.get("displaySymbol", "")
                })

            return results if results else None

        except requests.exceptions.Timeout:
            logger.warning("Finnhub search timed out")
            return None
        except Exception as e:
            logger.warning(f"Finnhub search error: {e}")
            return None

    def _fallback_search(self, query: str, limit: int = 10) -> List[Dict]:
        """Fallback search using local stock/ETF/index list."""
        results = []
        query_upper = query.upper()

        # Build list of candidate symbols
        candidates = []
        candidate_meta = {}

        # Add exact query match as first candidate
        candidates.append(query_upper)
        candidate_meta[query_upper] = {"type": "EQUITY", "name": query_upper}

        # Add matching ETFs
        for etf in POPULAR_ETFS:
            if query_upper in etf:
                candidates.append(etf)
                candidate_meta[etf] = {"type": "ETF", "name": etf}

        # Add matching indices
        for symbol, meta in MARKET_INDICES.items():
            if query_upper in meta["name"].upper() or query_upper in meta["short"]:
                candidates.append(symbol)
                candidate_meta[symbol] = {"type": "INDEX", "name": meta["name"]}

        # Common stock symbols for basic search
        common_stocks = {
            "AAPL": "Apple Inc.",
            "MSFT": "Microsoft Corporation",
            "GOOGL": "Alphabet Inc.",
            "AMZN": "Amazon.com Inc.",
            "TSLA": "Tesla Inc.",
            "META": "Meta Platforms Inc.",
            "NVDA": "NVIDIA Corporation",
            "AMD": "Advanced Micro Devices",
            "NFLX": "Netflix Inc.",
            "DIS": "The Walt Disney Company",
            "INTC": "Intel Corporation",
            "JPM": "JPMorgan Chase & Co.",
            "BAC": "Bank of America Corp.",
            "WMT": "Walmart Inc.",
            "V": "Visa Inc.",
            "MA": "Mastercard Inc.",
            "PG": "Procter & Gamble",
            "JNJ": "Johnson & Johnson",
            "UNH": "UnitedHealth Group",
            "HD": "The Home Depot",
        }

        for symbol, name in common_stocks.items():
            if query_upper in symbol or query_upper in name.upper():
                if symbol not in candidates:
                    candidates.append(symbol)
                    candidate_meta[symbol] = {"type": "EQUITY", "name": name}

        # Remove duplicates while preserving order
        candidates = list(dict.fromkeys(candidates))

        for symbol in candidates[:limit]:
            meta = candidate_meta.get(symbol, {})
            results.append({
                "symbol": symbol,
                "name": meta.get("name", symbol),
                "type": meta.get("type", "EQUITY"),
                "exchange": ""
            })

        return results

    def search_symbols(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for symbols. Uses Finnhub primary, falls back to local list."""
        redis = get_redis_client()
        cache_key = self._get_cache_key("search", query.upper())

        # Check cache first
        if self._cache_enabled:
            cached = redis.cache_get(cache_key)
            if cached:
                return cached[:limit]

        # Try Finnhub first (fast, dedicated search API)
        results = self._finnhub_search(query, limit)

        if results:
            logger.debug(f"Finnhub search returned {len(results)} results for '{query}'")
        else:
            # Fallback to local candidate search
            logger.info(f"Using fallback search for '{query}'")
            results = self._fallback_search(query, limit)

        # Cache results
        if self._cache_enabled and results:
            redis.cache_set(cache_key, results, self.SEARCH_CACHE_TTL)

        return results[:limit]

    def get_company_info(self, symbol: str) -> Optional[Dict]:
        """Get detailed company information."""
        redis = get_redis_client()
        cache_key = self._get_cache_key("company", symbol.upper())

        # Check cache
        if self._cache_enabled:
            cached = redis.cache_get(cache_key)
            if cached:
                return cached

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            if not info:
                return None

            company_info = {
                "symbol": symbol.upper(),
                "name": info.get("shortName") or info.get("longName"),
                "description": info.get("longBusinessSummary"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "website": info.get("website"),
                "market_cap": info.get("marketCap"),
                "employees": info.get("fullTimeEmployees"),
                "country": info.get("country"),
                "city": info.get("city"),
                "pe_ratio": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "eps": info.get("trailingEps"),
                "dividend_yield": info.get("dividendYield"),
                "beta": info.get("beta"),
                "52_week_high": info.get("fiftyTwoWeekHigh"),
                "52_week_low": info.get("fiftyTwoWeekLow"),
                "50_day_avg": info.get("fiftyDayAverage"),
                "200_day_avg": info.get("twoHundredDayAverage"),
                "avg_volume": info.get("averageVolume"),
            }

            # Cache result with longer TTL
            if self._cache_enabled:
                redis.cache_set(cache_key, company_info, self.COMPANY_CACHE_TTL)

            return company_info

        except Exception as e:
            logger.error(f"Failed to get company info for {symbol}: {e}")
            return None

    def get_trending_tickers(self) -> List[Dict]:
        """Get trending/most active tickers (using volume as proxy)."""
        redis = get_redis_client()
        cache_key = self._get_cache_key("trending")

        # Check cache
        if self._cache_enabled:
            cached = redis.cache_get(cache_key)
            if cached:
                return cached

        # This is a simplified version - for real trending data you'd need a different API
        popular = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "AMD", "NFLX", "DIS"]

        quotes = self.get_multiple_quotes(popular)

        # If no quotes returned, use sample data
        if not quotes:
            logger.warning("Using sample data for trending tickers")
            result = self._get_sample_trending()
        else:
            # Sort by volume
            quotes_sorted = sorted(quotes, key=lambda q: q.volume or 0, reverse=True)
            result = [q.to_dict() for q in quotes_sorted]

        # Cache result
        if self._cache_enabled and result:
            redis.cache_set(cache_key, result, self.QUOTE_CACHE_TTL)

        return result

    def _get_sample_trending(self) -> List[Dict]:
        """Return sample trending data as fallback."""
        trending = []
        for symbol, data in SAMPLE_STOCK_DATA.items():
            price = data["price"]
            prev = data["prev"]
            change = price - prev
            change_pct = (change / prev * 100) if prev else 0

            # Add slight randomization
            jitter = random.uniform(-0.1, 0.1) / 100
            price_adj = price * (1 + jitter)

            trending.append({
                "symbol": symbol,
                "name": data["name"],
                "price": round(price_adj, 2),
                "change": round(change, 2),
                "change_percent": round(change_pct, 2),
                "previous_close": round(prev, 2),
                "open": round(prev * 1.001, 2),
                "day_high": round(price * 1.01, 2),
                "day_low": round(prev * 0.99, 2),
                "volume": random.randint(10000000, 100000000),
                "market_cap": None,
                "52_week_high": None,
                "52_week_low": None,
                "timestamp": datetime.utcnow().isoformat(),
                "is_sample_data": True
            })
        return sorted(trending, key=lambda x: x["volume"], reverse=True)


# Singleton instance
_market_data_service: Optional[MarketDataService] = None


def get_market_data_service() -> MarketDataService:
    """Get singleton MarketDataService instance."""
    global _market_data_service
    if _market_data_service is None:
        _market_data_service = MarketDataService()
    return _market_data_service
