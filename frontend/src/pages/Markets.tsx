import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  TrendingUp,
  TrendingDown,
  Search,
  Loader2,
  BarChart3,
  Activity,
  AlertTriangle,
} from 'lucide-react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import {
  useMarketIndices,
  useMarketSearch,
  useMarketTrending,
  useMarketHistory,
} from '../hooks/useApi'

function formatNumber(value: number): string {
  return value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function formatVolume(value: number): string {
  if (value >= 1e9) return `${(value / 1e9).toFixed(1)}B`
  if (value >= 1e6) return `${(value / 1e6).toFixed(1)}M`
  if (value >= 1e3) return `${(value / 1e3).toFixed(1)}K`
  return value.toString()
}

export default function Markets() {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState('^GSPC')
  const [chartPeriod, setChartPeriod] = useState('1mo')

  const { data: indicesData, isLoading: indicesLoading } = useMarketIndices()
  const { data: searchData, isLoading: searchLoading, error: searchError, isError: isSearchError } = useMarketSearch(searchQuery, 10)
  const { data: trendingData, isLoading: trendingLoading, error: trendingError, isError: isTrendingError } = useMarketTrending()
  const { data: historyData, isLoading: historyLoading } = useMarketHistory(selectedIndex, chartPeriod, '1d')

  const indices = indicesData?.indices || []
  const trending = trendingData?.tickers || []

  const chartData = historyData?.prices?.map((p) => ({
    date: p.date.slice(5), // MM-DD
    price: p.close,
  })) || []

  const selectedIndexData = indices.find((i) => i.symbol === selectedIndex)

  // Check if any data is sample/fallback data
  const hasStaleIndices = indices.some((i: any) => i.is_sample_data)
  const hasStaleTrending = trending.some((t: any) => t.is_sample_data)
  const hasStaleData = hasStaleIndices || hasStaleTrending

  return (
    <div className="space-y-8">
      {/* Stale Data Warning */}
      {hasStaleData && (
        <div className="flex items-center gap-3 p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl text-amber-800 dark:text-amber-200">
          <AlertTriangle className="w-5 h-5 flex-shrink-0" />
          <div>
            <span className="font-medium">Market data temporarily unavailable.</span>
            <span className="ml-1 text-amber-700 dark:text-amber-300">
              Showing cached prices which may be outdated. Live data will return automatically.
            </span>
          </div>
        </div>
      )}

      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Markets</h1>
        <p className="mt-1 text-gray-500 dark:text-gray-400">
          Real-time market data and stock search
        </p>
      </div>

      {/* Search */}
      <div className="relative max-w-xl">
        <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
        <input
          type="text"
          placeholder="Search for stocks, ETFs, or indices..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-12 pr-4 py-3 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl text-base focus:outline-none focus:ring-2 focus:ring-blue-500"
        />

        {/* Search Results */}
        {searchQuery && (
          <div className="absolute z-10 w-full mt-2 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl shadow-lg max-h-80 overflow-y-auto">
            {searchLoading ? (
              <div className="flex items-center justify-center py-6">
                <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
              </div>
            ) : isSearchError ? (
              <div className="px-4 py-6 text-center text-red-500">
                Search error: {searchError instanceof Error ? searchError.message : 'Unknown error'}
              </div>
            ) : searchData?.results && searchData.results.length > 0 ? (
              searchData.results.map((result) => (
                <Link
                  key={result.symbol}
                  to={`/tickers/${result.symbol.replace('^', '')}`}
                  className="flex items-center justify-between px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-800 border-b border-gray-100 dark:border-gray-800 last:border-b-0"
                  onClick={() => setSearchQuery('')}
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-gray-900 dark:text-white">
                        {result.symbol}
                      </span>
                      <span className="text-xs px-2 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-gray-600 dark:text-gray-300">
                        {result.type}
                      </span>
                    </div>
                    <span className="text-sm text-gray-500 dark:text-gray-400">
                      {result.name}
                    </span>
                  </div>
                </Link>
              ))
            ) : (
              <div className="px-4 py-6 text-center text-gray-500 dark:text-gray-400">
                No results found for "{searchQuery}"
              </div>
            )}
          </div>
        )}
      </div>

      {/* Market Indices */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Major Indices
        </h2>
        {indicesLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
            {indices.map((index) => (
              <button
                key={index.symbol}
                onClick={() => setSelectedIndex(index.symbol)}
                className={`text-left bg-white dark:bg-gray-900 rounded-xl border p-4 transition-all ${
                  selectedIndex === index.symbol
                    ? 'border-blue-500 ring-2 ring-blue-500/20'
                    : 'border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-700'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-500 dark:text-gray-400">
                    {index.short_name}
                  </span>
                  {index.change >= 0 ? (
                    <TrendingUp className="w-4 h-4 text-green-500" />
                  ) : (
                    <TrendingDown className="w-4 h-4 text-red-500" />
                  )}
                </div>
                <div className="text-xl font-bold text-gray-900 dark:text-white">
                  {formatNumber(index.price)}
                </div>
                <div
                  className={`text-sm font-medium mt-1 ${
                    index.change >= 0 ? 'text-green-600' : 'text-red-600'
                  }`}
                >
                  {index.change >= 0 ? '+' : ''}{index.change_percent.toFixed(2)}%
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Index Chart */}
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              {selectedIndexData?.display_name || selectedIndex}
            </h2>
            {selectedIndexData && (
              <div className="flex items-center gap-3 mt-1">
                <span className="text-2xl font-bold text-gray-900 dark:text-white">
                  {formatNumber(selectedIndexData.price)}
                </span>
                <span
                  className={`text-lg font-medium ${
                    selectedIndexData.change >= 0 ? 'text-green-600' : 'text-red-600'
                  }`}
                >
                  {selectedIndexData.change >= 0 ? '+' : ''}{formatNumber(selectedIndexData.change)} ({selectedIndexData.change_percent.toFixed(2)}%)
                </span>
              </div>
            )}
          </div>
          <div className="flex gap-2">
            {['5d', '1mo', '3mo', '6mo', '1y'].map((period) => (
              <button
                key={period}
                onClick={() => setChartPeriod(period)}
                className={`px-3 py-1.5 text-sm font-medium rounded-lg ${
                  chartPeriod === period
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'
                }`}
              >
                {period.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        {historyLoading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
          </div>
        ) : chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.2} />
              <XAxis dataKey="date" stroke="#9CA3AF" fontSize={12} />
              <YAxis stroke="#9CA3AF" fontSize={12} domain={['auto', 'auto']} />
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
                dataKey="price"
                stroke={selectedIndexData?.change >= 0 ? '#10B981' : '#EF4444'}
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex items-center justify-center h-64 text-gray-500">
            No data available
          </div>
        )}
      </div>

      {/* Trending Stocks */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <Activity className="w-5 h-5" />
          Most Active Stocks
        </h2>
        {trendingLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
          </div>
        ) : isTrendingError ? (
          <div className="text-red-500 py-4">
            Error loading trending: {trendingError instanceof Error ? trendingError.message : 'Unknown error'}
          </div>
        ) : trending.length === 0 ? (
          <div className="text-gray-500 dark:text-gray-400 py-4">
            No trending stocks available
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
            {trending.slice(0, 10).map((stock) => (
              <Link
                key={stock.symbol}
                to={`/tickers/${stock.symbol}`}
                className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 hover:shadow-md transition-shadow"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-semibold text-gray-900 dark:text-white">
                    {stock.symbol}
                  </span>
                  {stock.change >= 0 ? (
                    <span className="text-xs px-2 py-0.5 bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 rounded">
                      +{stock.change_percent.toFixed(2)}%
                    </span>
                  ) : (
                    <span className="text-xs px-2 py-0.5 bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 rounded">
                      {stock.change_percent.toFixed(2)}%
                    </span>
                  )}
                </div>
                <div className="text-lg font-bold text-gray-900 dark:text-white">
                  ${formatNumber(stock.price)}
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Vol: {formatVolume(stock.volume)}
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
