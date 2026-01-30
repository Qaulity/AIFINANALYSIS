import { useState } from 'react'
import { Link } from 'react-router-dom'
import { TrendingUp, TrendingDown, Activity, ArrowRight } from 'lucide-react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import { useTrends } from '../hooks/useApi'
import SentimentBadge from '../components/SentimentBadge'

export default function Trends() {
  const [days, setDays] = useState(7)
  const { data, isLoading } = useTrends(days)

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500 dark:text-gray-400">No trend data available.</p>
      </div>
    )
  }

  const moodIcon =
    data.market_mood === 'bullish' ? (
      <TrendingUp className="w-8 h-8 text-green-500" />
    ) : data.market_mood === 'bearish' ? (
      <TrendingDown className="w-8 h-8 text-red-500" />
    ) : (
      <Activity className="w-8 h-8 text-gray-500" />
    )

  const tickerChartData = data.top_tickers.map((t) => ({
    ...t,
    sentiment: t.avg_sentiment * 100,
    color: t.avg_sentiment > 0.1 ? '#10b981' : t.avg_sentiment < -0.1 ? '#ef4444' : '#6b7280',
  }))

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Market Trends</h1>
          <p className="mt-1 text-gray-500 dark:text-gray-400">
            Aggregate sentiment analysis from {data.total_articles} articles
          </p>
        </div>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="px-4 py-2 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value={1}>Last 24 hours</option>
          <option value={7}>Last 7 days</option>
          <option value={14}>Last 14 days</option>
          <option value={30}>Last 30 days</option>
        </select>
      </div>

      {/* Market Mood Card */}
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-8">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
              Overall Market Mood
            </p>
            <p className="mt-2 text-4xl font-bold text-gray-900 dark:text-white capitalize">
              {data.market_mood}
            </p>
            <p className="mt-2 text-lg text-gray-600 dark:text-gray-400">
              Average sentiment:{' '}
              <span
                className={
                  data.average_sentiment > 0
                    ? 'text-green-600'
                    : data.average_sentiment < 0
                      ? 'text-red-600'
                      : 'text-gray-600'
                }
              >
                {data.average_sentiment >= 0 ? '+' : ''}
                {(data.average_sentiment * 100).toFixed(1)}%
              </span>
            </p>
          </div>
          <div
            className={`p-6 rounded-full ${
              data.market_mood === 'bullish'
                ? 'bg-green-100 dark:bg-green-900/30'
                : data.market_mood === 'bearish'
                  ? 'bg-red-100 dark:bg-red-900/30'
                  : 'bg-gray-100 dark:bg-gray-800'
            }`}
          >
            {moodIcon}
          </div>
        </div>
      </div>

      {/* Ticker Sentiment Chart */}
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">
          Top Tickers by Sentiment
        </h2>
        <ResponsiveContainer width="100%" height={400}>
          <BarChart data={tickerChartData} layout="vertical" margin={{ left: 50, right: 30 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
            <XAxis
              type="number"
              domain={[-100, 100]}
              stroke="#9ca3af"
              tick={{ fill: '#9ca3af', fontSize: 12 }}
              tickFormatter={(v) => `${v}%`}
            />
            <YAxis
              type="category"
              dataKey="ticker"
              stroke="#9ca3af"
              tick={{ fill: '#9ca3af', fontSize: 12 }}
              tickFormatter={(v) => `$${v}`}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1f2937',
                border: 'none',
                borderRadius: '8px',
                color: '#fff',
              }}
              formatter={(value: number) => [`${value.toFixed(1)}%`, 'Sentiment']}
              labelFormatter={(label) => `$${label}`}
            />
            <Bar dataKey="sentiment" radius={[0, 4, 4, 0]}>
              {tickerChartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Top Tickers Grid */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Trending Tickers
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.top_tickers.map((ticker) => (
            <Link
              key={ticker.ticker}
              to={`/tickers/${ticker.ticker}`}
              className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5 hover:shadow-lg transition-shadow"
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-xl font-bold text-gray-900 dark:text-white">
                  ${ticker.ticker}
                </span>
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
                />
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-500 dark:text-gray-400">
                  {ticker.mentions} mentions
                </span>
                <ArrowRight className="w-4 h-4 text-gray-400" />
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* Top Sources */}
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Top News Sources
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {data.top_sources.map((source) => (
            <div
              key={source.name}
              className="text-center p-4 rounded-lg bg-gray-50 dark:bg-gray-800"
            >
              <p className="font-medium text-gray-900 dark:text-white truncate">{source.name}</p>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                {source.count} articles
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
