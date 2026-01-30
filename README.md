# Financial News Analysis Pipeline

A comprehensive full-stack application for analyzing financial news using advanced NLP techniques including FinBERT sentiment analysis, Named Entity Recognition, and BERTopic topic modeling.

## Key Features

### NLP Analysis
- **FinBERT Sentiment**: Financial domain-specific sentiment analysis using the ProsusAI/FinBERT model
- **Sentence-Level Analysis**: Granular sentiment scores for each sentence in articles
- **Named Entity Recognition**: Extract companies, people, monetary values, and percentages using spaCy
- **Ticker Extraction**: Automatic stock ticker symbol detection and company name mapping
- **Topic Modeling**: Discover trending topics using BERTopic with sentence transformers
- **Market Sentiment Aggregation**: Statistical analysis of overall market mood

### Data Pipeline
- **Multi-Source Ingestion**: NewsAPI integration and RSS feed parsing
- **Deduplication**: Intelligent article deduplication across sources
- **Background Processing**: Scheduled jobs for continuous news monitoring
- **Redis Storage**: High-performance caching and data storage

### Interactive Dashboard
- **Real-time Metrics**: Live market sentiment and article statistics
- **Trend Visualization**: Charts showing sentiment over time
- **Topic Explorer**: Browse discovered topics and keywords
- **Custom Text Analysis**: Analyze any financial text interactively

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.11, Flask, Flask-RESTX |
| ML/NLP | PyTorch, Transformers (FinBERT), spaCy, BERTopic |
| Frontend | React 18, TypeScript, Vite, TailwindCSS, Recharts |
| Data Store | Redis 7 |
| Deployment | Docker, Docker Compose |

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
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/articles` | GET | List articles with filtering |
| `/api/articles/<id>` | GET | Get single article |
| `/api/articles/fetch` | POST | Trigger news fetching |

### NLP Analysis
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/nlp/analyze` | POST | Run full NLP pipeline on articles |
| `/api/nlp/analyze/<id>` | GET | Get detailed NLP analysis for article |
| `/api/nlp/sentiment` | POST | Analyze sentiment of custom text |
| `/api/nlp/entities` | POST | Extract entities from custom text |
| `/api/nlp/topics` | GET | Get discovered topic summary |
| `/api/nlp/market-sentiment` | GET | Get aggregated market sentiment |

### Trends & Insights
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/trends` | GET | Get market trends |
| `/api/tickers/<symbol>/sentiment` | GET | Get ticker sentiment history |
| `/api/insights/summary` | GET | Dashboard summary |

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
│   │   │   ├── news_fetcher.py
│   │   │   └── rss_parser.py
│   │   └── utils/         # Redis client
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Articles.tsx
│   │   │   ├── Trends.tsx
│   │   │   ├── TickerAnalysis.tsx
│   │   │   └── NLPAnalysis.tsx    # Interactive NLP page
│   │   ├── hooks/
│   │   └── services/
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

## ML Models Used

| Model | Purpose | Size |
|-------|---------|------|
| ProsusAI/FinBERT | Financial sentiment analysis | ~440MB |
| en_core_web_sm | Named entity recognition | ~12MB |
| all-MiniLM-L6-v2 | Sentence embeddings for topics | ~80MB |
| BERTopic | Topic modeling | Runtime |

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEWSAPI_KEY` | NewsAPI API key | Required |
| `REDIS_HOST` | Redis host | localhost |
| `REDIS_PORT` | Redis port | 6379 |
| `SENTIMENT_MODEL` | finbert or textblob | finbert |
| `ENABLE_TOPIC_MODELING` | Enable BERTopic | true |
| `USE_GPU` | Use CUDA if available | true |
| `NLP_BATCH_SIZE` | Batch size for inference | 16 |

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

## Performance Notes

- First request to NLP endpoints may be slow as models load (~10-30s)
- Subsequent requests are fast (cached models)
- GPU acceleration significantly speeds up FinBERT inference
- Topic modeling requires at least 10 documents

## Documentation

See the `docs/` folder for detailed technical documentation:
- `ARCHITECTURE.txt` - System design and technology decisions
- `MARKET_DATA.txt` - Stock data integration (Finnhub + yfinance)
- `NLP_PIPELINE.txt` - Sentiment analysis, entity extraction, topics
- `FRONTEND.txt` - React app structure and patterns
- `TROUBLESHOOTING.txt` - Common issues and fixes

## License

MIT
