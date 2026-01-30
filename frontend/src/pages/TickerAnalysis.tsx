import { useParams, Link } from 'react-router-dom'
import {
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  BarChart3,
  Newspaper,
  DollarSign,
  Building2,
  Activity,
  Target,
  AlertCircle,
} from 'lucide-react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ComposedChart,
  Bar,
} from 'recharts'
import { useTickerSentiment, useStockAnalysis } from '../hooks/useApi'
import SentimentBadge from '../components/SentimentBadge'
import ArticleCard from '../components/ArticleCard'
import StatCard from '../components/StatCard'

function formatMarketCap(value: number): string {
  if (value >= 1e12) return `$${(value / 1e12).toFixed(2)}T`
  if (value >= 1e9) return `$${(value / 1e9).toFixed(2)}B`
  if (value >= 1e6) return `$${(value / 1e6).toFixed(2)}M`
  return `$${value.toLocaleString()}`
}

function formatNumber(value: number): string {
  return value.toLocaleString(undefined, { maximumFractionDigits: 2 })
}

export default function TickerAnalysis() {
  const { symbol } = useParams<{ symbol: string }>()
  const { data: sentimentData, isLoading: sentimentLoading } = useTickerSentiment(symbol || '', 30)
  const { data: stockData, isLoading: stockLoading, error: stockError } = useStockAnalysis(symbol || '', 30)

  // Only wait for sentiment data - stock data can load in background
  if (sentimentLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (!sentimentData && !stockData) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500 dark:text-gray-400">No data available for this ticker.</p>
        <Link
          to="/"
          className="mt-4 inline-flex items-center text-blue-600 hover:text-blue-700"
        >
          <ArrowLeft className="w-4 h-4 mr-1" />
          Back to Dashboard
        </Link>
      </div>
    )
  }

  const quote = stockData?.current_quote
  const company = stockData?.company
  const avgSentiment = sentimentData?.summary?.avg_sentiment || 0
  const sentimentLabel =
    avgSentiment > 0.1 ? 'positive' : avgSentiment < -0.1 ? 'negative' : 'neutral'

  // Prepare combined chart data
  const chartData = stockData?.price_sentiment_data?.map((d) => ({
    date: d.date.slice(5), // MM-DD format
    price: d.close,
    sentiment: d.avg_sentiment ? d.avg_sentiment * 100 : null,
    newsCount: d.news_count,
  })).reverse() || []

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          to="/"
          className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
        >
          <ArrowLeft className="w-5 h-5 text-gray-500" />
        </Link>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              ${symbol?.toUpperCase()}
            </h1>
            {quote && (
              <span
                className={`px-2 py-1 rounded text-sm font-medium ${
                  quote.change >= 0
                    ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                    : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                }`}
              >
                {quote.change >= 0 ? '+' : ''}{quote.change_percent.toFixed(2)}%
              </span>
            )}
          </div>
          <p className="mt-1 text-gray-500 dark:text-gray-400">
            {company?.name || 'Stock analysis with sentiment correlation'}
          </p>
        </div>
      </div>

      {/* Stock Quote Section */}
      {quote && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4">
            <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">Price</p>
            <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">
              ${formatNumber(quote.price)}
            </p>
          </div>
          <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4">
            <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">Change</p>
            <p className={`mt-1 text-2xl font-bold ${quote.change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {quote.change >= 0 ? '+' : ''}{formatNumber(quote.change)}
            </p>
          </div>
          <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4">
            <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">Volume</p>
            <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">
              {(quote.volume / 1e6).toFixed(1)}M
            </p>
          </div>
          <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4">
            <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">Open</p>
            <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">
              ${formatNumber(quote.open)}
            </p>
          </div>
          <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4">
            <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">High</p>
            <p className="mt-1 text-2xl font-bold text-green-600">
              ${formatNumber(quote.high)}
            </p>
          </div>
          <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4">
            <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">Low</p>
            <p className="mt-1 text-2xl font-bold text-red-600">
              ${formatNumber(quote.low)}
            </p>
          </div>
        </div>
      )}

      {/* Alpha Vantage Error Notice */}
      {stockError && (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-xl p-4 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-yellow-600 dark:text-yellow-400 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
              Stock data unavailable
            </p>
            <p className="text-sm text-yellow-700 dark:text-yellow-300">
              Alpha Vantage API rate limit may have been reached. Showing sentiment data only.
            </p>
          </div>
        </div>
      )}

      {/* Company Overview */}
      {company && (
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <Building2 className="w-5 h-5" />
            Company Overview
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-4">
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Market Cap</p>
              <p className="text-lg font-semibold text-gray-900 dark:text-white">
                {formatMarketCap(company.market_cap)}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Sector</p>
              <p className="text-lg font-semibold text-gray-900 dark:text-white">
                {company.sector || 'N/A'}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">P/E Ratio</p>
              <p className="text-lg font-semibold text-gray-900 dark:text-white">
                {company.pe_ratio?.toFixed(2) || 'N/A'}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">EPS</p>
              <p className="text-lg font-semibold text-gray-900 dark:text-white">
                ${company.eps?.toFixed(2) || 'N/A'}
              </p>
            </div>
          </div>
          {company.description && (
            <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-3">
              {company.description}
            </p>
          )}
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <StatCard
          title="News Mentions"
          value={stockData?.total_articles || sentimentData?.summary?.mentions || 0}
          icon={<Newspaper className="w-6 h-6" />}
          color="blue"
        />
        <StatCard
          title="Avg Sentiment"
          value={`${(avgSentiment * 100).toFixed(1)}%`}
          icon={avgSentiment >= 0 ? <TrendingUp className="w-6 h-6" /> : <TrendingDown className="w-6 h-6" />}
          color={sentimentLabel === 'positive' ? 'green' : sentimentLabel === 'negative' ? 'red' : 'default'}
        />
        <StatCard
          title="Correlation"
          value={stockData?.sentiment_price_correlation?.toFixed(2) || 'N/A'}
          icon={<Activity className="w-6 h-6" />}
          color={(stockData?.sentiment_price_correlation || 0) > 0.3 ? 'green' : 'default'}
        />
        <StatCard
          title="Analyst Target"
          value={company?.analyst_target_price ? `$${company.analyst_target_price.toFixed(0)}` : 'N/A'}
          icon={<Target className="w-6 h-6" />}
        />
      </div>

      {/* Correlation Insight */}
      {stockData?.correlation_insight && (
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-xl border border-blue-200 dark:border-blue-800 p-6">
          <h3 className="text-sm font-medium text-blue-800 dark:text-blue-200 uppercase tracking-wide mb-2">
            AI Insight
          </h3>
          <p className="text-lg font-semibold text-blue-900 dark:text-blue-100">
            {stockData.correlation_insight}
          </p>
          {stockData.sentiment_price_correlation && (
            <p className="mt-2 text-sm text-blue-700 dark:text-blue-300">
              Correlation coefficient: {stockData.sentiment_price_correlation.toFixed(4)}
            </p>
          )}
        </div>
      )}

      {/* Combined Price + Sentiment Chart */}
      {chartData.length > 0 && (
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Price vs Sentiment Correlation
          </h2>
          <ResponsiveContainer width="100%" height={400}>
            <ComposedChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.2} />
              <XAxis dataKey="date" stroke="#9CA3AF" fontSize={12} />
              <YAxis yAxisId="price" orientation="left" stroke="#3B82F6" fontSize={12} />
              <YAxis yAxisId="sentiment" orientation="right" stroke="#10B981" fontSize={12} domain={[-100, 100]} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1F2937',
                  border: 'none',
                  borderRadius: '8px',
                  color: '#F9FAFB',
                }}
              />
              <Legend />
              <Line
                yAxisId="price"
                type="monotone"
                dataKey="price"
                stroke="#3B82F6"
                strokeWidth={2}
                dot={false}
                name="Stock Price ($)"
              />
              <Line
                yAxisId="sentiment"
                type="monotone"
                dataKey="sentiment"
                stroke="#10B981"
                strokeWidth={2}
                dot={false}
                name="Sentiment (%)"
                connectNulls
              />
              <Bar
                yAxisId="sentiment"
                dataKey="newsCount"
                fill="#6366F1"
                opacity={0.3}
                name="News Count"
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Sentiment History Chart */}
      {sentimentData?.trend && sentimentData.trend.length > 0 && (
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Sentiment History
          </h2>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={sentimentData.trend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.2} />
              <XAxis dataKey="date" stroke="#9CA3AF" fontSize={12} />
              <YAxis stroke="#9CA3AF" fontSize={12} domain={[-1, 1]} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1F2937',
                  border: 'none',
                  borderRadius: '8px',
                  color: '#F9FAFB',
                }}
              />
              <Line
                type="monotone"
                dataKey="avg_sentiment"
                stroke="#10B981"
                strokeWidth={2}
                dot={{ fill: '#10B981', r: 4 }}
                name="Avg Sentiment"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Recent Sentiments */}
      {sentimentData?.summary?.recent_sentiments && sentimentData.summary.recent_sentiments.length > 0 && (
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Recent Sentiment Scores
          </h2>
          <div className="flex flex-wrap gap-2">
            {sentimentData.summary.recent_sentiments.map((score, index) => (
              <SentimentBadge
                key={index}
                sentiment={{
                  score,
                  label: score > 0.1 ? 'positive' : score < -0.1 ? 'negative' : 'neutral',
                  confidence: 1,
                  model: 'aggregate',
                }}
                showScore
              />
            ))}
          </div>
        </div>
      )}

      {/* Recent Articles */}
      {sentimentData?.recent_articles && sentimentData.recent_articles.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Recent Articles
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {sentimentData.recent_articles.map((article) => (
              <ArticleCard key={article.id} article={article} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
