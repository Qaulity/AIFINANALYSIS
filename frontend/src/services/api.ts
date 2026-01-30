// API service - all backend calls route through here
// base URL from VITE_API_URL, defaults to same origin
import axios from 'axios'
import type {
  ArticleListResponse,
  Article,
  TrendData,
  TickerSentimentData,
  InsightsSummary,
  ArticleNLPAnalysis,
  TopicSummary,
  MarketSentimentAnalysis,
  AIInsightsResponse,
  AIInsightsStatus,
} from '../types'

const API_BASE = import.meta.env.VITE_API_URL || ''

const api = axios.create({
  baseURL: `${API_BASE}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
})

// --- Articles ---

// fetch articles with pagination and optional filters
export async function getArticles(params?: {
  page?: number
  per_page?: number
  sentiment?: string
  source?: string
  ticker?: string
  days?: number
}): Promise<ArticleListResponse> {
  const { data } = await api.get('/articles', { params })
  return data
}

// get single article by id
export async function getArticle(id: string): Promise<Article> {
  const { data } = await api.get(`/articles/${id}`)
  return data
}

// trigger fetch from NewsAPI and/or RSS feeds
export async function fetchArticles(source: 'all' | 'newsapi' | 'rss' = 'all'): Promise<{
  status: string
  fetched: number
  sources: { name: string; count: number }[]
}> {
  const { data } = await api.post('/articles/fetch', null, { params: { source } })
  return data
}

// run sentiment analysis on unprocessed articles
export async function analyzeArticles(limit = 100): Promise<{
  status: string
  processed: number
}> {
  const { data } = await api.post('/articles/analyze', null, { params: { limit } })
  return data
}

// --- Trends ---

// get trend analysis for last N days
export async function getTrends(days = 7): Promise<TrendData> {
  const { data } = await api.get('/trends', { params: { days } })
  return data
}

// get sentiment history for a ticker
export async function getTickerSentiment(
  symbol: string,
  days = 30
): Promise<TickerSentimentData> {
  const { data } = await api.get(`/tickers/${symbol}/sentiment`, { params: { days } })
  return data
}

// get dashboard summary stats
export async function getInsightsSummary(): Promise<InsightsSummary> {
  const { data } = await api.get('/insights/summary')
  return data
}

// --- Health ---

// check backend and redis status
export async function checkHealth(): Promise<{
  status: string
  redis: string
  timestamp: string
}> {
  const { data } = await api.get('/health')
  return data
}

// --- NLP ---

// run full NLP pipeline on articles (sentiment, NER, topics)
export async function runNLPAnalysis(
  limit = 50,
  fitTopics = true
): Promise<{
  status: string
  processed: number
  stored: number
  ticker_updates: number
  topics_fitted: boolean
}> {
  const { data } = await api.post('/nlp/analyze', null, {
    params: { limit, fit_topics: fitTopics },
  })
  return data
}

// get NLP analysis for a specific article
export async function getArticleNLPAnalysis(articleId: string): Promise<ArticleNLPAnalysis> {
  const { data } = await api.get(`/nlp/analyze/${articleId}`)
  return data
}

// analyze sentiment of arbitrary text
export async function analyzeSentiment(text: string): Promise<{
  overall: { score: number; label: string; confidence: number; model: string }
  sentences: { text: string; score: number; label: string }[]
  positive_sentences: number
  negative_sentences: number
  neutral_sentences: number
}> {
  const { data } = await api.post('/nlp/sentiment', { text })
  return data
}

// extract entities from text (tickers, people, metrics)
export async function extractEntities(text: string): Promise<{
  entities: { text: string; label: string }[]
  tickers: { symbol: string; company_name: string | null }[]
  metrics: {
    monetary: { value: string; context: string }[]
    percentages: { value: string; context: string }[]
  }
  people: { name: string; title: string | null }[]
}> {
  const { data } = await api.post('/nlp/entities', { text })
  return data
}

// get topic model summary
export async function getTopicSummary(): Promise<TopicSummary> {
  const { data } = await api.get('/nlp/topics')
  return data
}

// get aggregated market sentiment across articles
export async function getMarketSentiment(
  days = 7,
  limit = 100
): Promise<MarketSentimentAnalysis> {
  const { data } = await api.get('/nlp/market-sentiment', { params: { days, limit } })
  return data
}

// --- Stock Data (Alpha Vantage) ---

export interface StockQuote {
  symbol: string
  price: number
  change: number
  change_percent: number
  volume: number
  latest_trading_day: string
  previous_close: number
  open: number
  high: number
  low: number
  timestamp: string
}

export interface StockPrice {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface CompanyOverview {
  symbol: string
  name: string
  description: string
  sector: string
  industry: string
  market_cap: number
  pe_ratio: number | null
  dividend_yield: number | null
  eps: number | null
  '52_week_high': number
  '52_week_low': number
  analyst_target_price: number | null
}

export interface StockAnalysis {
  symbol: string
  current_quote: StockQuote | null
  company: CompanyOverview | null
  price_sentiment_data: {
    date: string
    close: number
    volume: number
    price_change: number
    avg_sentiment: number | null
    news_count: number
  }[]
  total_articles: number
  sentiment_price_correlation: number | null
  correlation_insight: string
  analysis_period_days: number
}

export async function searchStocks(query: string): Promise<{
  results: { symbol: string; name: string; type: string; region: string; currency: string }[]
  count: number
}> {
  const { data } = await api.get('/stocks/search', { params: { q: query } })
  return data
}

export async function getStockQuote(symbol: string): Promise<StockQuote> {
  const { data } = await api.get(`/stocks/${symbol}/quote`)
  return data
}

export async function getStockHistory(symbol: string, days = 30): Promise<{
  symbol: string
  days: number
  prices: StockPrice[]
}> {
  const { data } = await api.get(`/stocks/${symbol}/history`, { params: { days } })
  return data
}

export async function getCompanyOverview(symbol: string): Promise<CompanyOverview> {
  const { data } = await api.get(`/stocks/${symbol}/overview`)
  return data
}

export async function getStockAnalysis(symbol: string, days = 30): Promise<StockAnalysis> {
  const { data } = await api.get(`/stocks/${symbol}/analysis`, { params: { days } })
  return data
}

// --- Market Data (yfinance) ---

export interface MarketIndex {
  symbol: string
  name: string
  short_name: string
  display_name: string
  price: number
  change: number
  change_percent: number
  previous_close: number
  open: number
  day_high: number
  day_low: number
  volume: number
  timestamp: string
}

export interface MarketQuoteData {
  symbol: string
  name: string
  price: number
  change: number
  change_percent: number
  previous_close: number
  open: number
  day_high: number
  day_low: number
  volume: number
  market_cap: number | null
  '52_week_high': number | null
  '52_week_low': number | null
  timestamp: string
}

export interface MarketHistoryPrice {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface MarketSearchResult {
  symbol: string
  name: string
  type: string
  exchange: string
}

// get major market indices (DOW, S&P, NASDAQ, etc)
export async function getMarketIndices(): Promise<{ indices: MarketIndex[]; count: number }> {
  const { data } = await api.get('/market/indices')
  return data
}

// get quote for any symbol
export async function getMarketQuote(symbol: string): Promise<MarketQuoteData> {
  const { data } = await api.get(`/market/quote/${symbol}`)
  return data
}

// batch get quotes for multiple symbols
export async function getMarketQuotes(symbols: string[]): Promise<{ quotes: MarketQuoteData[]; count: number }> {
  const { data } = await api.get('/market/quotes', { params: { symbols: symbols.join(',') } })
  return data
}

// get historical price data
export async function getMarketHistory(
  symbol: string,
  period = '1mo',
  interval = '1d'
): Promise<{ symbol: string; period: string; interval: string; prices: MarketHistoryPrice[]; count: number }> {
  const { data } = await api.get(`/market/history/${symbol}`, { params: { period, interval } })
  return data
}

// search stocks/ETFs by symbol or name
export async function searchMarket(query: string, limit = 10): Promise<{ results: MarketSearchResult[]; count: number }> {
  const { data } = await api.get('/market/search', { params: { q: query, limit } })
  return data
}

// get company info
export async function getMarketCompanyInfo(symbol: string): Promise<Record<string, unknown>> {
  const { data } = await api.get(`/market/company/${symbol}`)
  return data
}

// get trending/most active stocks
export async function getMarketTrending(): Promise<{ tickers: MarketQuoteData[]; count: number }> {
  const { data } = await api.get('/market/trending')
  return data
}

// --- AI Insights ---

// get cached AI insights (returns instantly)
export async function getAIInsights(): Promise<AIInsightsResponse> {
  const { data } = await api.get('/ai/insights')
  return data
}

// manually refresh AI insights (rate limited to 1/min)
export async function refreshAIInsights(): Promise<AIInsightsResponse> {
  const { data } = await api.post('/ai/insights/refresh')
  return data
}

// get AI insights service status
export async function getAIInsightsStatus(): Promise<AIInsightsStatus> {
  const { data } = await api.get('/ai/insights/status')
  return data
}
