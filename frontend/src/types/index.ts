// TypeScript types matching backend API response shapes

// --- Core Article Types ---

// sentiment result from FinBERT
export interface Sentiment {
  score: number                              // -1 to 1
  label: 'positive' | 'negative' | 'neutral'
  confidence: number                         // 0 to 1
  model: string                              // e.g. "finbert"
}

// news article with sentiment and extracted data
export interface Article {
  id: string
  title: string
  description: string | null
  content: string | null
  url: string
  source_name: string
  source_type: 'newsapi' | 'rss' | 'scraper'
  author: string | null
  published_at: string                       // ISO date string
  image_url: string | null
  sentiment: Sentiment | null
  tickers: string[]                          // extracted stock symbols
  topics: string[]                           // topic labels
}

// paginated article list response
export interface ArticleListResponse {
  articles: Article[]
  total: number
  page: number
  per_page: number
}

// --- Trends & Analytics Types ---

// ticker mention count with sentiment
export interface TickerMention {
  ticker: string
  mentions: number
  avg_sentiment: number
}

// news source article count
export interface SourceCount {
  name: string
  count: number
}

// trend analysis for a time period
export interface TrendData {
  period_days: number
  total_articles: number
  average_sentiment: number
  market_mood: 'bullish' | 'bearish' | 'neutral'
  top_tickers: TickerMention[]
  top_sources: SourceCount[]
}

// daily sentiment for a specific ticker
export interface DailySentiment {
  date: string
  avg_sentiment: number
  article_count: number
}

// full sentiment data for a ticker
export interface TickerSentimentData {
  ticker: string
  summary: {
    ticker: string
    mentions: number
    avg_sentiment: number
    recent_sentiments: number[]
  }
  trend: DailySentiment[]
  recent_articles: Article[]
}

// dashboard summary stats
export interface InsightsSummary {
  total_articles: number
  articles_today: number
  average_sentiment: number
  sentiment_distribution: {
    positive: number
    negative: number
    neutral: number
  }
  market_mood: 'bullish' | 'bearish' | 'neutral'
  last_updated: string
}

// --- NLP Analysis Types ---

// named entity from spaCy NER
export interface ExtractedEntity {
  text: string
  label: string      // ORG, PERSON, MONEY, PERCENT, etc.
  start: number
  end: number
  confidence: number
}

// stock ticker extracted from text
export interface TickerExtraction {
  symbol: string
  company_name: string | null
  exchange: string | null
  mentions: number
}

// financial numbers extracted from text
export interface FinancialMetrics {
  monetary: { value: string; context: string }[]
  percentages: { value: string; context: string }[]
  dates: string[]
  quantities: { value: string; context: string }[]
}

// person mentioned in article
export interface PersonMention {
  name: string
  title: string | null
  context: string
}

// sentiment for a single sentence
export interface SentenceSentiment {
  text: string
  score: number
  label: string
}

// full NLP analysis for an article
export interface ArticleNLPAnalysis {
  article_id: string
  sentiment: Sentiment
  sentence_sentiments: SentenceSentiment[]
  tickers: TickerExtraction[]
  entities: ExtractedEntity[]
  people: PersonMention[]
  financial_metrics: FinancialMetrics
  topics: string[]
  topic_id: number | null
  analyzed_at: string
}

// topic from BERTopic model
export interface TopicInfo {
  id: number
  name: string
  keywords: string[]
  count: number
  percentage: number
}

// topic modeling summary
export interface TopicSummary {
  total_documents: number
  num_topics: number
  outliers: number
  topics: TopicInfo[]
}

// aggregated market sentiment analysis
export interface MarketSentimentAnalysis {
  total_articles: number
  average_sentiment: number
  sentiment_std: number
  median_sentiment: number
  positive_count: number
  negative_count: number
  neutral_count: number
  positive_ratio: number
  negative_ratio: number
  market_mood: 'bullish' | 'bearish' | 'neutral'
  confidence: number
  period_days: number
  analyzed_at: string
}

// --- AI Insights Types ---

// single trend alert for a ticker
export interface TrendAlert {
  ticker: string
  alert_type: 'bullish' | 'bearish' | 'volatile' | 'momentum'
  message: string
}

// AI-generated market insights
export interface AIInsights {
  market_summary: string          // 2-3 sentence overview
  trend_alerts: TrendAlert[]      // ticker-specific alerts
  sector_analysis: string         // sector coverage analysis
  key_observations: string[]      // bullet point observations
  sentiment_outlook: string       // near-term outlook
  generated_at: string            // when insights were created
  data_timestamp: string          // when source data was gathered
  is_stale: boolean              // true if older than generation interval
}

// response from /api/ai/insights endpoint
export interface AIInsightsResponse {
  status: string                  // "success", "rate_limited", "unavailable", etc.
  insights: AIInsights | null
  is_generating: boolean          // true if generation in progress
  retry_after?: number            // seconds until rate limit resets
  message?: string                // error or info message
  warning?: string                // non-fatal warning
}

// response from /api/ai/insights/status endpoint
export interface AIInsightsStatus {
  configured: boolean             // true if API key is set
  enabled: boolean                // true if feature is enabled
  has_cached_insights: boolean
  is_generating: boolean
  is_rate_limited: boolean
  rate_limit_remaining: number | null
  generation_interval_minutes: number
  cache_ttl_seconds: number
  last_generated: string | null
}
