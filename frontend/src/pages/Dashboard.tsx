import { Link } from 'react-router-dom'
import {
  Newspaper,
  TrendingUp,
  TrendingDown,
  Activity,
  BarChart3,
  ArrowRight,
} from 'lucide-react'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'
import { useInsightsSummary, useTrends, useArticles } from '../hooks/useApi'
import StatCard from '../components/StatCard'
import ArticleCard from '../components/ArticleCard'
import SentimentBadge from '../components/SentimentBadge'
import MarketOverview from '../components/MarketOverview'
import AIInsightsCard from '../components/AIInsightsCard'

export default function Dashboard() {
  const { data: summary, isLoading: summaryLoading } = useInsightsSummary()
  const { data: trends, isLoading: trendsLoading } = useTrends(7)
  const { data: articlesData, isLoading: articlesLoading } = useArticles({ per_page: 4 })

  const isLoading = summaryLoading || trendsLoading || articlesLoading

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  const sentimentData = summary
    ? [
        { name: 'Bullish', value: summary.sentiment_distribution.positive, color: '#10b981' },
        { name: 'Bearish', value: summary.sentiment_distribution.negative, color: '#ef4444' },
        { name: 'Neutral', value: summary.sentiment_distribution.neutral, color: '#6b7280' },
      ]
    : []

  const moodIcon =
    summary?.market_mood === 'bullish' ? (
      <TrendingUp className="w-6 h-6" />
    ) : summary?.market_mood === 'bearish' ? (
      <TrendingDown className="w-6 h-6" />
    ) : (
      <Activity className="w-6 h-6" />
    )

  const moodColor =
    summary?.market_mood === 'bullish'
      ? 'green'
      : summary?.market_mood === 'bearish'
        ? 'red'
        : 'default'

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
        <p className="mt-1 text-gray-500 dark:text-gray-400">
          Financial news sentiment analysis overview
        </p>
      </div>

      {/* Market Overview */}
      <div className="bg-gray-50 dark:bg-gray-900/50 rounded-2xl border border-gray-200 dark:border-gray-800 p-6">
        <MarketOverview />
      </div>

      {/* AI Insights */}
      <AIInsightsCard />

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Total Articles"
          value={summary?.total_articles.toLocaleString() || '0'}
          icon={<Newspaper className="w-6 h-6" />}
          color="blue"
        />
        <StatCard
          title="Articles Today"
          value={summary?.articles_today || 0}
          icon={<BarChart3 className="w-6 h-6" />}
        />
        <StatCard
          title="Average Sentiment"
          value={`${((summary?.average_sentiment || 0) * 100).toFixed(1)}%`}
          icon={moodIcon}
          color={moodColor}
        />
        <StatCard
          title="Market Mood"
          value={summary?.market_mood?.toUpperCase() || 'N/A'}
          icon={<Activity className="w-6 h-6" />}
          color={moodColor}
        />
      </div>

      {/* Charts and Lists */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Sentiment Distribution */}
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Sentiment Distribution
          </h2>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie
                data={sentimentData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={80}
                paddingAngle={5}
                dataKey="value"
              >
                {sentimentData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1f2937',
                  border: 'none',
                  borderRadius: '8px',
                  color: '#fff',
                }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="flex justify-center gap-4 mt-4">
            {sentimentData.map((entry) => (
              <div key={entry.name} className="flex items-center">
                <div
                  className="w-3 h-3 rounded-full mr-2"
                  style={{ backgroundColor: entry.color }}
                />
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  {entry.name} ({entry.value})
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Top Tickers */}
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Trending Tickers
          </h2>
          {trends?.top_tickers && trends.top_tickers.length > 0 ? (
            <div className="space-y-3">
              {trends.top_tickers.slice(0, 5).map((ticker, index) => (
                <Link
                  key={ticker.ticker}
                  to={`/tickers/${ticker.ticker}`}
                  className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                >
                  <div className="flex items-center">
                    <span className="w-6 h-6 flex items-center justify-center text-sm font-medium text-gray-400">
                      {index + 1}
                    </span>
                    <span className="ml-3 font-medium text-gray-900 dark:text-white">
                      ${ticker.ticker}
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-sm text-gray-500">{ticker.mentions} mentions</span>
                    <SentimentBadge
                      sentiment={{
                        score: ticker.avg_sentiment,
                        label:
                          ticker.avg_sentiment > 0.1
                            ? 'positive'
                            : ticker.avg_sentiment < -0.1
                              ? 'negative'
                              : 'neutral',
                        confidence: 1,
                        model: 'aggregate',
                      }}
                      size="sm"
                    />
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <div className="text-center py-6">
              <p className="text-gray-500 dark:text-gray-400 mb-4">
                Run NLP analysis on articles to see which tickers are being mentioned in the news.
              </p>
              <Link
                to="/nlp"
                className="inline-flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
              >
                NLP Analysis
              </Link>
            </div>
          )}
        </div>

        {/* Top Sources */}
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Top Sources</h2>
          <div className="space-y-3">
            {trends?.top_sources.slice(0, 5).map((source, index) => (
              <div
                key={source.name}
                className="flex items-center justify-between p-3 rounded-lg bg-gray-50 dark:bg-gray-800"
              >
                <div className="flex items-center">
                  <span className="w-6 h-6 flex items-center justify-center text-sm font-medium text-gray-400">
                    {index + 1}
                  </span>
                  <span className="ml-3 font-medium text-gray-900 dark:text-white truncate max-w-[150px]">
                    {source.name}
                  </span>
                </div>
                <span className="text-sm text-gray-500">{source.count} articles</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent Articles */}
      <div>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Recent Articles</h2>
          <Link
            to="/articles"
            className="flex items-center text-sm font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400"
          >
            View all
            <ArrowRight className="w-4 h-4 ml-1" />
          </Link>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {articlesData?.articles.map((article) => (
            <ArticleCard key={article.id} article={article} />
          ))}
        </div>
      </div>
    </div>
  )
}
