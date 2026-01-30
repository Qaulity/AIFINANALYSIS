import { useState } from 'react'
import { Link } from 'react-router-dom'
import { TrendingUp, TrendingDown, Search, Loader2, ExternalLink, AlertTriangle } from 'lucide-react'
import { useMarketIndices, useMarketSearch } from '../hooks/useApi'

function formatNumber(value: number): string {
  return value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function formatLargeNumber(value: number): string {
  if (value >= 1e12) return `${(value / 1e12).toFixed(2)}T`
  if (value >= 1e9) return `${(value / 1e9).toFixed(2)}B`
  if (value >= 1e6) return `${(value / 1e6).toFixed(2)}M`
  return value.toLocaleString()
}

export default function MarketOverview() {
  const [searchQuery, setSearchQuery] = useState('')
  const [showSearch, setShowSearch] = useState(false)

  const { data: indicesData, isLoading: indicesLoading } = useMarketIndices()
  const { data: searchData, isLoading: searchLoading } = useMarketSearch(searchQuery, 8)

  const indices = indicesData?.indices || []
  const hasStaleData = indices.some((i: any) => i.is_sample_data)

  return (
    <div className="space-y-4">
      {/* Stale Data Warning */}
      {hasStaleData && (
        <div className="flex items-center gap-2 p-2 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg text-amber-800 dark:text-amber-200 text-sm">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          <span>Showing cached data - live prices temporarily unavailable</span>
        </div>
      )}

      {/* Header with Search */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          Market Overview
        </h2>
        <button
          onClick={() => setShowSearch(!showSearch)}
          className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500"
        >
          <Search className="w-5 h-5" />
        </button>
      </div>

      {/* Search Box */}
      {showSearch && (
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search stocks, ETFs, indices..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            autoFocus
          />

          {/* Search Results Dropdown */}
          {searchQuery && (
            <div className="absolute z-10 w-full mt-1 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg max-h-64 overflow-y-auto">
              {searchLoading ? (
                <div className="flex items-center justify-center py-4">
                  <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
                </div>
              ) : searchData?.results && searchData.results.length > 0 ? (
                searchData.results.map((result) => (
                  <Link
                    key={result.symbol}
                    to={`/tickers/${result.symbol.replace('^', '')}`}
                    className="flex items-center justify-between px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-800 border-b border-gray-100 dark:border-gray-800 last:border-b-0"
                    onClick={() => {
                      setSearchQuery('')
                      setShowSearch(false)
                    }}
                  >
                    <div>
                      <span className="font-medium text-gray-900 dark:text-white">
                        {result.symbol}
                      </span>
                      <span className="ml-2 text-sm text-gray-500 dark:text-gray-400">
                        {result.name}
                      </span>
                    </div>
                    <span className="text-xs px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-gray-600 dark:text-gray-300">
                      {result.type}
                    </span>
                  </Link>
                ))
              ) : (
                <div className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                  No results found for "{searchQuery}"
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Market Indices */}
      {indicesLoading ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3">
          {indices.map((index) => (
            <div
              key={index.symbol}
              className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 hover:shadow-md transition-shadow"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-500 dark:text-gray-400">
                  {index.short_name || index.display_name}
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
              <div className="flex items-center gap-2 mt-1">
                <span
                  className={`text-sm font-medium ${
                    index.change >= 0 ? 'text-green-600' : 'text-red-600'
                  }`}
                >
                  {index.change >= 0 ? '+' : ''}{formatNumber(index.change)}
                </span>
                <span
                  className={`text-xs px-1.5 py-0.5 rounded ${
                    index.change >= 0
                      ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                      : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                  }`}
                >
                  {index.change_percent >= 0 ? '+' : ''}{index.change_percent.toFixed(2)}%
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
