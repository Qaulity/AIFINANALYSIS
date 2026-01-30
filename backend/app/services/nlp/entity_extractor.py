"""Named Entity Recognition for financial news using spaCy."""
import re
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class ExtractedEntity:
    """Represents an extracted named entity."""
    text: str
    label: str  # ORG, PERSON, MONEY, PERCENT, DATE, GPE, etc.
    start: int
    end: int
    confidence: float = 1.0

    def to_dict(self) -> Dict:
        return {
            "text": self.text,
            "label": self.label,
            "start": self.start,
            "end": self.end,
            "confidence": self.confidence
        }


@dataclass
class TickerMention:
    """Represents a stock ticker mention."""
    symbol: str
    company_name: Optional[str] = None
    exchange: Optional[str] = None
    mentions: int = 1
    contexts: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "company_name": self.company_name,
            "exchange": self.exchange,
            "mentions": self.mentions
        }


class EntityExtractor:
    """Extract named entities from financial text using spaCy NER and custom ticker patterns."""

    TICKER_PATTERN = re.compile(r'\$([A-Z]{1,5})\b|\b([A-Z]{2,5})\s+(?:stock|shares|Inc\.|Corp\.)')

    # company name to ticker map
    COMPANY_TICKERS = {
        "apple": "AAPL", "microsoft": "MSFT", "google": "GOOGL", "alphabet": "GOOGL",
        "amazon": "AMZN", "meta": "META", "facebook": "META", "tesla": "TSLA",
        "nvidia": "NVDA", "netflix": "NFLX", "jpmorgan": "JPM", "goldman sachs": "GS",
        "bank of america": "BAC", "wells fargo": "WFC", "citigroup": "C",
        "berkshire hathaway": "BRK.A", "johnson & johnson": "JNJ", "walmart": "WMT",
        "visa": "V", "mastercard": "MA", "paypal": "PYPL", "intel": "INTC",
        "amd": "AMD", "salesforce": "CRM", "adobe": "ADBE", "oracle": "ORCL",
        "ibm": "IBM", "cisco": "CSCO", "qualcomm": "QCOM", "broadcom": "AVGO",
        "boeing": "BA", "lockheed martin": "LMT", "disney": "DIS", "coca-cola": "KO",
        "pepsi": "PEP", "mcdonald's": "MCD", "starbucks": "SBUX", "nike": "NKE",
        "exxon": "XOM", "chevron": "CVX", "pfizer": "PFE", "moderna": "MRNA",
        "united health": "UNH", "cvs": "CVS", "walgreens": "WBA",
        "at&t": "T", "verizon": "VZ", "t-mobile": "TMUS", "comcast": "CMCSA",
        "uber": "UBER", "lyft": "LYFT", "airbnb": "ABNB", "doordash": "DASH",
        "spotify": "SPOT", "zoom": "ZM", "slack": "WORK", "twitter": "X",
        "snap": "SNAP", "pinterest": "PINS", "roku": "ROKU", "square": "SQ",
        "block": "SQ", "coinbase": "COIN", "robinhood": "HOOD"
    }

    # Financial entity types to extract
    FINANCIAL_ENTITY_TYPES = {"ORG", "PERSON", "MONEY", "PERCENT", "DATE", "GPE", "CARDINAL"}

    def __init__(self, model_name: str = "en_core_web_sm"):
        """Initialize with spaCy model (sm/md/lg)."""
        self._nlp = None
        self._model_name = model_name
        self._loaded = False

    def _load_model(self):
        """Lazy load spaCy model."""
        if self._loaded:
            return

        import spacy

        try:
            self._nlp = spacy.load(self._model_name)
            self._loaded = True
            logger.info(f"spaCy model '{self._model_name}' loaded")
        except OSError:
            logger.warning(f"Model {self._model_name} not found, downloading...")
            import subprocess
            subprocess.run(["python", "-m", "spacy", "download", self._model_name])
            self._nlp = spacy.load(self._model_name)
            self._loaded = True
            logger.info(f"spaCy model '{self._model_name}' downloaded and loaded")

    def extract_entities(self, text: str) -> List[ExtractedEntity]:
        """Extract all named entities from text."""
        if not text:
            return []

        self._load_model()
        doc = self._nlp(text)

        entities = []
        for ent in doc.ents:
            if ent.label_ in self.FINANCIAL_ENTITY_TYPES:
                entities.append(ExtractedEntity(
                    text=ent.text,
                    label=ent.label_,
                    start=ent.start_char,
                    end=ent.end_char
                ))

        return entities

    def extract_tickers(self, text: str) -> List[TickerMention]:
        """Extract stock tickers using pattern matching ($AAPL) and company name lookup."""
        if not text:
            return []

        self._load_model()

        tickers: Dict[str, TickerMention] = {}
        text_lower = text.lower()

        # Pattern matching for explicit tickers ($AAPL, MSFT stock, etc.)
        for match in self.TICKER_PATTERN.finditer(text):
            symbol = match.group(1) or match.group(2)
            if symbol:
                symbol = symbol.upper()
                if symbol not in tickers:
                    # Get context around the mention
                    start = max(0, match.start() - 50)
                    end = min(len(text), match.end() + 50)
                    context = text[start:end].strip()

                    tickers[symbol] = TickerMention(
                        symbol=symbol,
                        contexts=[context]
                    )
                else:
                    tickers[symbol].mentions += 1

        # Company name to ticker mapping
        for company, ticker in self.COMPANY_TICKERS.items():
            if company in text_lower:
                if ticker not in tickers:
                    # Find context
                    idx = text_lower.find(company)
                    start = max(0, idx - 30)
                    end = min(len(text), idx + len(company) + 30)
                    context = text[start:end].strip()

                    tickers[ticker] = TickerMention(
                        symbol=ticker,
                        company_name=company.title(),
                        contexts=[context]
                    )
                else:
                    tickers[ticker].mentions += 1
                    if not tickers[ticker].company_name:
                        tickers[ticker].company_name = company.title()

        # Use spaCy NER to find ORG entities that might be companies
        doc = self._nlp(text)
        for ent in doc.ents:
            if ent.label_ == "ORG":
                org_lower = ent.text.lower()
                # Check if this org matches any known company
                for company, ticker in self.COMPANY_TICKERS.items():
                    if company in org_lower or org_lower in company:
                        if ticker not in tickers:
                            tickers[ticker] = TickerMention(
                                symbol=ticker,
                                company_name=ent.text
                            )
                        else:
                            tickers[ticker].mentions += 1
                        break

        return list(tickers.values())

    def extract_financial_metrics(self, text: str) -> Dict:
        """Extract monetary values, percentages, dates, and quantities from text."""
        if not text:
            return {"monetary": [], "percentages": [], "dates": [], "quantities": []}

        self._load_model()
        doc = self._nlp(text)

        metrics = {
            "monetary": [],
            "percentages": [],
            "dates": [],
            "quantities": []
        }

        for ent in doc.ents:
            if ent.label_ == "MONEY":
                metrics["monetary"].append({
                    "value": ent.text,
                    "context": text[max(0, ent.start_char-20):min(len(text), ent.end_char+20)]
                })
            elif ent.label_ == "PERCENT":
                metrics["percentages"].append({
                    "value": ent.text,
                    "context": text[max(0, ent.start_char-20):min(len(text), ent.end_char+20)]
                })
            elif ent.label_ == "DATE":
                metrics["dates"].append(ent.text)
            elif ent.label_ == "CARDINAL":
                metrics["quantities"].append({
                    "value": ent.text,
                    "context": text[max(0, ent.start_char-20):min(len(text), ent.end_char+20)]
                })

        return metrics

    def extract_people(self, text: str) -> List[Dict]:
        """Extract people mentioned in text (tries to identify their role/title)."""
        if not text:
            return []

        self._load_model()
        doc = self._nlp(text)

        people = []
        seen = set()

        for ent in doc.ents:
            if ent.label_ == "PERSON" and ent.text not in seen:
                seen.add(ent.text)

                # Try to find their role/title from context
                context_start = max(0, ent.start_char - 50)
                context_end = min(len(text), ent.end_char + 50)
                context = text[context_start:context_end]

                # Common title patterns
                title = None
                title_patterns = [
                    r"(?:CEO|Chief Executive|Chairman|CFO|CTO|COO|President|Director|Analyst|Manager)",
                ]
                for pattern in title_patterns:
                    match = re.search(pattern, context, re.IGNORECASE)
                    if match:
                        title = match.group()
                        break

                people.append({
                    "name": ent.text,
                    "title": title,
                    "context": context.strip()
                })

        return people

    def full_extraction(self, text: str) -> Dict:
        """Perform complete extraction - entities, tickers, metrics, people."""
        return {
            "entities": [e.to_dict() for e in self.extract_entities(text)],
            "tickers": [t.to_dict() for t in self.extract_tickers(text)],
            "metrics": self.extract_financial_metrics(text),
            "people": self.extract_people(text)
        }
