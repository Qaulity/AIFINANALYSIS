import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as api from '../services/api'

// Articles
export function useArticles(params?: Parameters<typeof api.getArticles>[0]) {
  return useQuery({
    queryKey: ['articles', params],
    queryFn: () => api.getArticles(params),
  })
}

export function useArticle(id: string) {
  return useQuery({
    queryKey: ['article', id],
    queryFn: () => api.getArticle(id),
    enabled: !!id,
  })
}

export function useFetchArticles() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: api.fetchArticles,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['articles'] })
      queryClient.invalidateQueries({ queryKey: ['insights'] })
      queryClient.invalidateQueries({ queryKey: ['trends'] })
    },
  })
}

export function useAnalyzeArticles() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: api.analyzeArticles,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['articles'] })
      queryClient.invalidateQueries({ queryKey: ['insights'] })
      queryClient.invalidateQueries({ queryKey: ['trends'] })
    },
  })
}

// Trends
export function useTrends(days = 7) {
  return useQuery({
    queryKey: ['trends', days],
    queryFn: () => api.getTrends(days),
  })
}

// Tickers
export function useTickerSentiment(symbol: string, days = 30) {
  return useQuery({
    queryKey: ['ticker', symbol, days],
    queryFn: () => api.getTickerSentiment(symbol, days),
    enabled: !!symbol,
  })
}

// Insights
export function useInsightsSummary() {
  return useQuery({
    queryKey: ['insights', 'summary'],
    queryFn: api.getInsightsSummary,
    refetchInterval: 1000 * 60 * 2, // Refresh every 2 minutes
  })
}

// Health
export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: api.checkHealth,
    refetchInterval: 1000 * 30, // Check every 30 seconds
  })
}

// NLP Analysis
export function useRunNLPAnalysis() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ limit, fitTopics }: { limit?: number; fitTopics?: boolean }) =>
      api.runNLPAnalysis(limit, fitTopics),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['articles'] })
      queryClient.invalidateQueries({ queryKey: ['insights'] })
      queryClient.invalidateQueries({ queryKey: ['trends'] })
      queryClient.invalidateQueries({ queryKey: ['topics'] })
      queryClient.invalidateQueries({ queryKey: ['market-sentiment'] })
    },
  })
}

export function useArticleNLPAnalysis(articleId: string) {
  return useQuery({
    queryKey: ['nlp', 'article', articleId],
    queryFn: () => api.getArticleNLPAnalysis(articleId),
    enabled: !!articleId,
  })
}

export function useTopicSummary() {
  return useQuery({
    queryKey: ['topics', 'summary'],
    queryFn: api.getTopicSummary,
  })
}

export function useMarketSentiment(days = 7, limit = 100) {
  return useQuery({
    queryKey: ['market-sentiment', days, limit],
    queryFn: () => api.getMarketSentiment(days, limit),
  })
}

// Stock Data (Alpha Vantage)
export function useStockSearch(query: string) {
  return useQuery({
    queryKey: ['stocks', 'search', query],
    queryFn: () => api.searchStocks(query),
    enabled: query.length >= 2,
  })
}

export function useStockQuote(symbol: string) {
  return useQuery({
    queryKey: ['stocks', 'quote', symbol],
    queryFn: () => api.getStockQuote(symbol),
    enabled: !!symbol,
    refetchInterval: 1000 * 60, // Refresh every minute
  })
}

export function useStockHistory(symbol: string, days = 30) {
  return useQuery({
    queryKey: ['stocks', 'history', symbol, days],
    queryFn: () => api.getStockHistory(symbol, days),
    enabled: !!symbol,
  })
}

export function useCompanyOverview(symbol: string) {
  return useQuery({
    queryKey: ['stocks', 'overview', symbol],
    queryFn: () => api.getCompanyOverview(symbol),
    enabled: !!symbol,
  })
}

export function useStockAnalysis(symbol: string, days = 30) {
  return useQuery({
    queryKey: ['stocks', 'analysis', symbol, days],
    queryFn: () => api.getStockAnalysis(symbol, days),
    enabled: !!symbol,
    retry: 1,
    staleTime: 1000 * 60 * 5, // Cache for 5 minutes
  })
}

// Market Data (Yahoo Finance)
export function useMarketIndices() {
  return useQuery({
    queryKey: ['market', 'indices'],
    queryFn: api.getMarketIndices,
    refetchInterval: 1000 * 60, // Refresh every minute
    staleTime: 1000 * 30, // Consider stale after 30 seconds
  })
}

export function useMarketQuote(symbol: string) {
  return useQuery({
    queryKey: ['market', 'quote', symbol],
    queryFn: () => api.getMarketQuote(symbol),
    enabled: !!symbol,
    refetchInterval: 1000 * 60,
    staleTime: 1000 * 30,
  })
}

export function useMarketQuotes(symbols: string[]) {
  return useQuery({
    queryKey: ['market', 'quotes', symbols.join(',')],
    queryFn: () => api.getMarketQuotes(symbols),
    enabled: symbols.length > 0,
    refetchInterval: 1000 * 60,
    staleTime: 1000 * 30,
  })
}

export function useMarketHistory(symbol: string, period = '1mo', interval = '1d') {
  return useQuery({
    queryKey: ['market', 'history', symbol, period, interval],
    queryFn: () => api.getMarketHistory(symbol, period, interval),
    enabled: !!symbol,
    staleTime: 1000 * 60 * 5,
  })
}

export function useMarketSearch(query: string, limit = 10) {
  return useQuery({
    queryKey: ['market', 'search', query],
    queryFn: () => api.searchMarket(query, limit),
    enabled: query.length >= 1,
    staleTime: 1000 * 60 * 5,
  })
}

export function useMarketCompanyInfo(symbol: string) {
  return useQuery({
    queryKey: ['market', 'company', symbol],
    queryFn: () => api.getMarketCompanyInfo(symbol),
    enabled: !!symbol,
    staleTime: 1000 * 60 * 10,
  })
}

export function useMarketTrending() {
  return useQuery({
    queryKey: ['market', 'trending'],
    queryFn: api.getMarketTrending,
    refetchInterval: 1000 * 60 * 2,
    staleTime: 1000 * 60,
  })
}

// AI Insights
export function useAIInsights() {
  return useQuery({
    queryKey: ['ai', 'insights'],
    queryFn: api.getAIInsights,
    refetchInterval: 1000 * 60 * 2, // Refresh every 2 minutes
    staleTime: 1000 * 60, // Consider stale after 1 minute
    retry: 1,
  })
}

export function useRefreshAIInsights() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: api.refreshAIInsights,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai', 'insights'] })
    },
  })
}

export function useAIInsightsStatus() {
  return useQuery({
    queryKey: ['ai', 'insights', 'status'],
    queryFn: api.getAIInsightsStatus,
    refetchInterval: 1000 * 30, // Check every 30 seconds
  })
}
