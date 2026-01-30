# Financial News Analysis Pipeline

A comprehensive full-stack application for analyzing financial news using advanced NLP techniques including FinBERT sentiment analysis, Named Entity Recognition, BERTopic topic modeling, and AI-powered market insights via Claude.

## Key Features

### AI-Powered Insights (NEW)

- **Claude Integration**: Anthropic Claude API generates intelligent market analysis
- **Market Summaries**: Automated 2-3 sentence market overview
- **Trend Alerts**: Ticker-specific signals (bullish, bearish, volatile, momentum)
- **Sector Analysis**: Industry-grouped sentiment insights
- **Key Observations**: AI-curated bullet points of notable market events
- **Background Generation**: Insights auto-refresh every 15 minutes with 20-minute caching

### NLP Analysis

- **FinBERT Sentiment**: Financial domain-specific sentiment analysis using the ProsusAI/FinBERT model
- **Sentence-Level Analysis**: Granular sentiment scores for each sentence in articles
- **Named Entity Recognition**: Extract companies, people, monetary values, and percentages using spaCy
- **Ticker Extraction**: Automatic stock ticker symbol detection and company name mapping (50+ companies)
- **Topic Modeling**: Discover trending topics using BERTopic with sentence transformers
- **Market Sentiment Aggregation**: Statistical analysis of overall market mood
- **Fallback Support**: Graceful degradation to TextBlob if FinBERT unavailable

### Real-Time Market Data (NEW)

- **Finnhub Integration**: Lightning-fast stock symbol search and typeahead
- **Yahoo Finance**: Historical price data, current quotes, and company info
- **Market Indices**: Live tracking of Dow, S&P 500, NASDAQ, Russell 2000, and VIX
- **Popular ETFs**: Quick access to SPY, QQQ, IWM, and more
- **Alpha Vantage**: Optional additional stock data source
- **Smart Caching**: Tiered caching (2min quotes, 30min history, 24hr company info)

### Data Pipeline

- **Multi-Source Ingestion**: NewsAPI integration and RSS feed parsing
- **Deduplication**: Intelligent article deduplication across sources
- **Background Processing**: Scheduled jobs for continuous news monitoring
- **Redis Storage**: High-performance caching and data storage
- **Rate Limit Management**: Automatic tracking of API daily limits

### Interactive Dashboard

- **Real-time Metrics**: Live market sentiment and article statistics
- **AI Insights Card**: Claude-powered market analysis with manual refresh
- **Market Overview**: Live indices and trending stocks display
- **Trend Visualization**: Charts showing sentiment over time
- **Topic Explorer**: Browse discovered topics and keywords
- **Custom Text Analysis**: Analyze any financial text interactively
- **Stock Search**: Typeahead search with detailed ticker analysis

## Tech Stack

| Component   | Technology                                                              |
| ----------- | ----------------------------------------------------------------------- |
| Backend     | Python 3.11, Flask, Flask-RESTX, Gunicorn                               |
| ML/NLP      | PyTorch, Transformers (FinBERT), spaCy, BERTopic, sentence-transformers |
| AI Insights | Anthropic Claude API                                                    |
| Market Data | Finnhub API, Yahoo Finance (yfinance), Alpha Vantage                    |
| Frontend    | React 18, TypeScript, Vite, TailwindCSS, React Query, Recharts          |
| Data Store  | Redis 7                                                                 |
| Deployment  | Docker, Docker Compose                                                  |

## Quick Start

### Prerequisites

- Docker and Docker Compose
- NewsAPI key (get one free at https://newsapi.org)
- ~4GB disk space (ML models are large)

### Setup

1. **Clone and configure:**

   ```bash
   cd FinancialNewsAnalysis
   copy backend\.env.example backend\.env
   # Edit backend\.env and add your NEWSAPI_KEY
   ```

2. **Start with Docker:**

   ```bash
   docker compose build
   docker compose up -d
   ```

   Note: First build downloads ~2GB of ML models and may take several minutes.

3. **Access the application:**
   - Dashboard: http://localhost:5173
   - API: http://localhost:5000
   - API Docs (Swagger): http://localhost:5000/api/docs

## API Endpoints

### Articles

| Endpoint              | Method | Description                  |
| --------------------- | ------ | ---------------------------- |
| `/api/articles`       | GET    | List articles with filtering |
| `/api/articles/<id>`  | GET    | Get single article           |
| `/api/articles/fetch` | POST   | Trigger news fetching        |

### NLP Analysis

| Endpoint                    | Method | Description                           |
| --------------------------- | ------ | ------------------------------------- |
| `/api/nlp/analyze`          | POST   | Run full NLP pipeline on articles     |
| `/api/nlp/analyze/<id>`     | GET    | Get detailed NLP analysis for article |
| `/api/nlp/sentiment`        | POST   | Analyze sentiment of custom text      |
| `/api/nlp/entities`         | POST   | Extract entities from custom text     |
| `/api/nlp/topics`           | GET    | Get discovered topic summary          |
| `/api/nlp/market-sentiment` | GET    | Get aggregated market sentiment       |

### AI Insights (NEW)

| Endpoint                   | Method | Description                             |
| -------------------------- | ------ | --------------------------------------- |
| `/api/ai/insights`         | GET    | Get cached AI-generated market insights |
| `/api/ai/insights/refresh` | POST   | Manual refresh (rate-limited: 1/min)    |
| `/api/ai/insights/status`  | GET    | Check AI insights service status        |

### Market Data (NEW)

| Endpoint                       | Method | Description                           |
| ------------------------------ | ------ | ------------------------------------- |
| `/api/market/search`           | GET    | Search for stocks (Finnhub typeahead) |
| `/api/market/quote/<symbol>`   | GET    | Get current stock quote               |
| `/api/market/history/<symbol>` | GET    | Get historical price data             |
| `/api/market/indices`          | GET    | Get major market indices              |

### Trends & Insights

| Endpoint                          | Method | Description                  |
| --------------------------------- | ------ | ---------------------------- |
| `/api/trends`                     | GET    | Get market trends            |
| `/api/tickers/<symbol>/sentiment` | GET    | Get ticker sentiment history |
| `/api/insights/summary`           | GET    | Dashboard summary            |

## Project Structure

```
FinancialNewsAnalysis/
├── backend/
│   ├── app/
│   │   ├── api/           # Flask routes
│   │   ├── models/        # Pydantic data models
│   │   ├── services/
│   │   │   ├── nlp/       # NLP services
│   │   │   │   ├── finbert_analyzer.py   # FinBERT sentiment
│   │   │   │   ├── entity_extractor.py   # spaCy NER
│   │   │   │   ├── topic_modeler.py      # BERTopic
│   │   │   │   └── nlp_pipeline.py       # Unified pipeline
│   │   │   ├── ai_insights.py            # Claude AI integration (NEW)
│   │   │   ├── market_data.py            # Finnhub/yfinance (NEW)
│   │   │   ├── news_fetcher.py
│   │   │   └── rss_parser.py
│   │   └── utils/         # Redis client
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── AIInsightsCard.tsx        # AI insights display (NEW)
│   │   │   ├── MarketOverview.tsx        # Indices & stocks (NEW)
│   │   │   └── ...
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Articles.tsx
│   │   │   ├── Markets.tsx               # Market data page (NEW)
│   │   │   ├── Trends.tsx
│   │   │   ├── TickerAnalysis.tsx
│   │   │   └── NLPAnalysis.tsx
│   │   ├── hooks/
│   │   └── services/
│   └── Dockerfile
├── docs/                  # Technical documentation
├── docker-compose.yml
└── README.md
```

## ML Models Used

| Model            | Purpose                        | Size    |
| ---------------- | ------------------------------ | ------- |
| ProsusAI/FinBERT | Financial sentiment analysis   | ~440MB  |
| en_core_web_sm   | Named entity recognition       | ~12MB   |
| all-MiniLM-L6-v2 | Sentence embeddings for topics | ~80MB   |
| BERTopic         | Topic modeling                 | Runtime |

## Configuration

### Environment Variables

#### Required

| Variable            | Description                               |
| ------------------- | ----------------------------------------- |
| `NEWSAPI_KEY`       | NewsAPI API key (get free at newsapi.org) |
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude AI insights  |

#### Optional - Market Data

| Variable           | Description                  | Default                      |
| ------------------ | ---------------------------- | ---------------------------- |
| `FINNHUB_API_KEY`  | Finnhub API for stock search | Falls back to local matching |
| `ALPHAVANTAGE_KEY` | Alpha Vantage API (optional) | None                         |

#### Optional - General

| Variable                | Description              | Default   |
| ----------------------- | ------------------------ | --------- |
| `REDIS_HOST`            | Redis host               | localhost |
| `REDIS_PORT`            | Redis port               | 6379      |
| `SENTIMENT_MODEL`       | finbert or textblob      | finbert   |
| `ENABLE_TOPIC_MODELING` | Enable BERTopic          | true      |
| `USE_GPU`               | Use CUDA if available    | true      |
| `NLP_BATCH_SIZE`        | Batch size for inference | 16        |

#### Optional - AI Insights

| Variable                          | Description                     | Default                  |
| --------------------------------- | ------------------------------- | ------------------------ |
| `AI_INSIGHTS_GENERATION_INTERVAL` | Auto-refresh interval (minutes) | 15                       |
| `AI_INSIGHTS_CACHE_TTL`           | Cache duration (seconds)        | 1200                     |
| `AI_MODEL`                        | Claude model to use             | claude-sonnet-4-20250514 |

## Usage Examples

### Analyze Custom Text (API)

```bash
curl -X POST http://localhost:5000/api/nlp/sentiment \
  -H "Content-Type: application/json" \
  -d '{"text": "Apple reported record earnings, beating analyst expectations."}'
```

### Run Full NLP Pipeline

```bash
curl -X POST "http://localhost:5000/api/nlp/analyze?limit=50&fit_topics=true"
```

### Get Market Sentiment

```bash
curl "http://localhost:5000/api/nlp/market-sentiment?days=7"
```

### Get AI-Generated Market Insights (NEW)

```bash
curl "http://localhost:5000/api/ai/insights"
```

### Search for Stocks (NEW)

```bash
curl "http://localhost:5000/api/market/search?q=apple"
```

### Get Stock Quote (NEW)

```bash
curl "http://localhost:5000/api/market/quote/AAPL"
```

### Get Market Indices (NEW)

```bash
curl "http://localhost:5000/api/market/indices"
```

## Background Worker

The pipeline worker runs scheduled tasks for continuous monitoring:

| Task                   | Interval | Description                               |
| ---------------------- | -------- | ----------------------------------------- |
| News Fetch             | 30 min   | Pulls articles from NewsAPI and RSS feeds |
| Sentiment Analysis     | 15 min   | Runs FinBERT on newly ingested articles   |
| AI Insights Generation | 15 min   | Generates Claude-powered market analysis  |

## Performance Notes

- First request to NLP endpoints may be slow as models load (~10-30s)
- Subsequent requests are fast (cached models)
- GPU acceleration significantly speeds up FinBERT inference
- Topic modeling requires at least 10 documents
- AI insights are cached for 20 minutes for instant UI response
- Market quotes cached for 2 minutes, history for 30 minutes

## Frontend Pages

| Page                | Description                                                              |
| ------------------- | ------------------------------------------------------------------------ |
| **Dashboard**       | Key metrics, recent articles, market overview, AI insights card          |
| **Articles**        | Browse articles with filtering by sentiment, source, ticker, date        |
| **Markets**         | Live indices, stock search with typeahead, price charts, trending stocks |
| **Trends**          | Sentiment trends, topic distribution, top tickers and sources            |
| **Ticker Analysis** | Deep-dive on individual stocks with sentiment correlation                |
| **NLP Analysis**    | Interactive tool to analyze any financial text                           |

## Documentation

See the `docs/` folder for detailed technical documentation:

- `ARCHITECTURE.txt` - System design and technology decisions
- `AI_INSIGHTS.txt` - Claude integration and market analysis generation
- `MARKET_DATA.txt` - Stock data integration (Finnhub + yfinance)
- `NLP_PIPELINE.txt` - Sentiment analysis, entity extraction, topics
- `FRONTEND.txt` - React app structure and patterns
- `TROUBLESHOOTING.txt` - Common issues and fixes
